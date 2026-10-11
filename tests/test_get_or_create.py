"""get_or_create 函数的单元测试（数据库层）。

被测函数（models.py L12-18）：
    def get_or_create(model, **kwargs):
        obj = model.query.filter_by(**kwargs).first()
        if obj is None:
            obj = model(**kwargs)
            db.session.add(obj)
            db.session.flush()
        return obj

它是后台保存文章时“分类/标签不存在就自动创建”的核心，两条分支：
- 已存在 -> 返回原记录，不产生重复；
- 不存在 -> 新建并 flush（立即拿到主键），但不 commit，事务由调用方提交。

测试矩阵：创建分支 / 复用分支 / 幂等 / 多模型隔离 /
          flush 与 commit 的事务边界 / 约束即时校验 / 大小写敏感性
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app
from models import Admin, Category, Tag, db, get_or_create


@pytest.fixture()
def app_ctx():
    """提供干净的应用上下文与内存数据库。

    create_app() 启动时会自动灌入种子数据（8 篇示例文章），
    这里 drop_all 后再 create_all，确保 count() 类断言从 0 开始、互不干扰。
    """
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.rollback()
        db.session.remove()
        db.drop_all()


# ---------- 1. 不存在 -> 新建（两种模型参数化） ----------
@pytest.mark.parametrize('model', [Category, Tag], ids=['Category', 'Tag'])
def test_creates_new_row_when_absent(app_ctx, model):
    assert model.query.count() == 0
    obj = get_or_create(model, name='Python')
    assert obj.id is not None          # flush 已为新记录分配主键
    assert obj.name == 'Python'
    assert model.query.count() == 1


# ---------- 2. flush 后在同一 session/事务中立即可见 ----------
def test_flush_makes_row_visible_in_same_session(app_ctx):
    obj = get_or_create(Category, name='Python')
    # 注意：此时尚未 commit，但 flush 已发出 INSERT，查询应能命中
    fetched = Category.query.filter_by(name='Python').first()
    assert fetched is not None
    assert fetched is obj              # identity map 保证返回同一 Python 对象


# ---------- 3. 已存在 -> 返回原记录，不产生重复 ----------
def test_returns_existing_instead_of_duplicate(app_ctx):
    first = get_or_create(Category, name='Python')
    db.session.commit()

    second = get_or_create(Category, name='Python')

    assert second.id == first.id
    assert Category.query.count() == 1


# ---------- 4. 连续多次调用同名：幂等，只产生一行 ----------
def test_repeated_calls_keep_single_row(app_ctx):
    objs = [get_or_create(Tag, name='Flask') for _ in range(3)]
    db.session.commit()

    assert Tag.query.count() == 1
    assert all(o.id == objs[0].id for o in objs)


# ---------- 5. 不同名称 -> 各自独立的新行 ----------
def test_different_names_create_different_rows(app_ctx):
    py = get_or_create(Category, name='Python')
    web = get_or_create(Category, name='Web')
    assert py.id != web.id
    assert Category.query.count() == 2
    assert {c.name for c in Category.query.all()} == {'Python', 'Web'}


# ---------- 6. 不同模型互不相干：同名也是两张表的两条记录 ----------
def test_distinct_models_are_independent(app_ctx):
    cat = get_or_create(Category, name='Python')
    tag = get_or_create(Tag, name='Python')

    assert isinstance(cat, Category)
    assert isinstance(tag, Tag)
    assert Category.query.count() == 1
    assert Tag.query.count() == 1


# ---------- 7. 事务边界：只 flush 未 commit，rollback 可撤销 ----------
def test_creation_can_be_rolled_back(app_ctx):
    get_or_create(Category, name='临时分类')
    # 不 commit，直接回滚 -> 新建应被撤销
    db.session.rollback()

    assert Category.query.filter_by(name='临时分类').first() is None
    assert Category.query.count() == 0


# ---------- 8. 事务边界：调用方 commit 后真正持久化 ----------
def test_caller_commit_persists_row(app_ctx):
    obj = get_or_create(Category, name='Python')
    db.session.commit()

    fetched = Category.query.filter_by(name='Python').first()
    assert fetched is not None
    assert fetched.id == obj.id
    assert Category.query.count() == 1


# ---------- 9. flush 会即时触发 NOT NULL 约束，而不是拖到 commit ----------
def test_flush_validates_constraints_immediately(app_ctx):
    # Admin.password_hash 为 NOT NULL，缺省传入 None，flush 时即报错
    with pytest.raises(IntegrityError):
        get_or_create(Admin, username='ghost')
    db.session.rollback()   # 出错后清理会话，避免污染 fixture 的 teardown

    assert Admin.query.filter_by(username='ghost').first() is None


# ---------- 10. 查询是精确匹配：大小写不同视为不同名称 ----------
def test_lookup_is_case_sensitive(app_ctx):
    get_or_create(Category, name='Python')
    db.session.commit()

    other = get_or_create(Category, name='python')   # SQLite '=' 默认大小写敏感
    existing = Category.query.filter_by(name='Python').first()

    assert other.id != existing.id
    assert Category.query.count() == 2
