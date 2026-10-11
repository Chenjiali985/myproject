import functools
import re
from datetime import datetime

from flask import (Flask, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)
from sqlalchemy import and_, func
from werkzeug.security import check_password_hash

from config import Config
from models import (Admin, Category, Comment, Post, Tag, db, get_or_create,
                    post_tag_table)
from seed_data import seed_if_empty


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin_id'):
            flash('请先登录后台', 'error')
            return redirect(url_for('admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def sanitize_slug(raw):
    return re.sub(r'[^\w-]+', '-', (raw or '').strip()).strip('-').lower()


def init_db(app):
    """建表 + 空库时灌入种子数据（仅在应用启动时执行一次）"""
    with app.app_context():
        db.create_all()
        seed_if_empty()


# ---------------- 可复用的查询/工具函数（模块级，可独立测试） ----------------

def paginate_query(query, page, per_page):
    """纯分页逻辑：与 Flask 请求上下文解耦"""
    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_paginated_posts(extra_filter=None):
    """已发布文章的分页查询（读取当前请求页码与站点配置）"""
    query = Post.query.filter_by(published=True)
    if extra_filter is not None:
        query = query.filter(extra_filter)
    query = query.order_by(Post.created_at.desc())
    return paginate_query(query,
                          page=request.args.get('page', 1, type=int),
                          per_page=current_app.config['POSTS_PER_PAGE'])


def build_search_query(keyword):
    """按关键词在标题/摘要/正文中做大小写不敏感模糊查询"""
    like = f'%{keyword}%'
    return Post.query.filter(
        Post.published.is_(True),
        db.or_(Post.title.ilike(like), Post.summary.ilike(like),
               Post.content.ilike(like)))


def generate_unique_slug(base, exclude_id=None):
    """保证 slug 唯一，冲突时自动追加 -2、-3…"""
    slug, i = base, 2
    while True:
        query = Post.query.filter_by(slug=slug)
        if exclude_id:
            query = query.filter(Post.id != exclude_id)
        if query.first() is None:
            return slug
        slug = f'{base}-{i}'
        i += 1


def populate_post_from_form(post):
    """把后台表单数据写入 Post 对象（新建/编辑共用）"""
    post.title = request.form['title'].strip()
    post.content = (request.form.get('content', '')
                    .replace('\r\n', '\n').replace('\r', '\n'))
    post.summary = request.form.get('summary', '').strip() or None
    post.published = request.form.get('published') == 'on'
    form_slug = sanitize_slug(request.form.get('slug'))
    if form_slug:
        post.slug = form_slug
    new_category_name = request.form.get('new_category', '').strip()
    if new_category_name:
        category = get_or_create(Category, name=new_category_name)
    else:
        form_category_id = request.form.get('category_id', type=int)
        category = (db.session.get(Category, form_category_id)
                    if form_category_id else None)
    raw_tags = request.form.get('tags', '')
    tag_names = [name for name in
                 (s.strip() for s in re.split(r'[,，]', raw_tags)) if name]
    post.category_id = category.id if category else None
    post.tags = [get_or_create(Tag, name=name) for name in tag_names]


# ---------------- 侧栏数据查询（单一职责，聚合查询避免 N+1） ----------------

def query_nav_categories():
    """分类及其已发布文章数（有文章的分类才返回）"""
    rows = (db.session.query(Category, func.count(Post.id))
            .outerjoin(Post, and_(Post.category_id == Category.id,
                                  Post.published.is_(True)))
            .group_by(Category.id)
            .order_by(Category.name).all())
    return [(category, count) for category, count in rows if count]


def query_tag_cloud(limit=15):
    """标签及其已发布文章数，按数量降序取前 limit 个"""
    rows = (db.session.query(Tag, func.count(Post.id))
            .outerjoin(post_tag_table, Tag.id == post_tag_table.c.tag_id)
            .outerjoin(Post, and_(Post.id == post_tag_table.c.post_id,
                                  Post.published.is_(True)))
            .group_by(Tag.id).all())
    rows.sort(key=lambda item: (-item[1], item[0].name))
    return rows[:limit]


def query_recent_posts(limit=5):
    return (Post.query.filter_by(published=True)
            .order_by(Post.created_at.desc()).limit(limit).all())


def query_top_posts(limit=5):
    return (Post.query.filter_by(published=True)
            .order_by(Post.views.desc()).limit(limit).all())


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    init_db(app)

    # ---------------- 公开页面 ----------------

    @app.route('/')
    def index():
        p = get_paginated_posts()
        return render_template('list.html', posts=p.items, pagination=p,
                               endpoint='index', title='最新文章',
                               subtitle=None, kwargs={})

    @app.route('/post/<slug>')
    def post_detail(slug):
        post = Post.query.filter_by(slug=slug).first_or_404()
        if not post.published and not session.get('admin_id'):
            abort(404)
        post.views += 1
        db.session.commit()
        comments = post.comments.order_by(Comment.created_at.asc()).all()
        return render_template('post.html', post=post, comments=comments)

    @app.route('/category/<name>')
    def category(name):
        cat = Category.query.filter_by(name=name).first_or_404()
        p = get_paginated_posts(Post.category_id == cat.id)
        return render_template('list.html', posts=p.items, pagination=p,
                               endpoint='category', title=f'分类：{name}',
                               subtitle=None, kwargs={'name': name})

    @app.route('/tag/<name>')
    def tag(name):
        t = Tag.query.filter_by(name=name).first_or_404()
        p = get_paginated_posts(Post.tags.contains(t))
        return render_template('list.html', posts=p.items, pagination=p,
                               endpoint='tag', title=f'标签：{name}',
                               subtitle=None, kwargs={'name': name})

    @app.route('/archive')
    def archive():
        posts = (Post.query.filter_by(published=True)
                 .order_by(Post.created_at.desc()).all())
        groups = {}
        for post in posts:
            key = (post.created_at.year, post.created_at.month)
            groups.setdefault(key, []).append(post)
        data = sorted(groups.items(), key=lambda kv: kv[0], reverse=True)
        return render_template('archive.html', archive_data=data,
                               title='归档', total=len(posts))

    @app.route('/search')
    def search():
        q = request.args.get('q', '').strip()
        if q:
            query = build_search_query(q).order_by(Post.created_at.desc())
            p = paginate_query(
                query, page=request.args.get('page', 1, type=int),
                per_page=app.config['POSTS_PER_PAGE'])
        else:
            p = get_paginated_posts()
        return render_template(
            'list.html', posts=p.items, pagination=p, endpoint='search',
            title=f'搜索：{q}' if q else '搜索',
            subtitle=f'共 {p.total} 条结果' if q else '输入关键词查找文章',
            kwargs={'q': q})

    @app.route('/about')
    def about():
        return render_template('about.html', title='关于我')

    @app.route('/comment/<int:post_id>', methods=['POST'])
    def add_comment(post_id):
        post = db.session.get(Post, post_id)
        if post is None:
            abort(404)
        name = request.form.get('name', '').strip()
        content = request.form.get('content', '').strip()
        if not name or not content:
            flash('昵称和评论内容不能为空', 'error')
        else:
            db.session.add(Comment(post_id=post.id, name=name, content=content))
            db.session.commit()
            flash('评论发表成功', 'success')
        return redirect(url_for('post_detail', slug=post.slug) + '#comments')

    # ---------------- 后台管理 ----------------

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            admin = Admin.query.filter_by(username=username).first()
            if admin and check_password_hash(admin.password_hash, password):
                session['admin_id'] = admin.id
                flash('登录成功', 'success')
                next_url = request.args.get('next') or url_for('admin_dashboard')
                if not next_url.startswith('/'):
                    next_url = url_for('admin_dashboard')
                return redirect(next_url)
            flash('用户名或密码错误', 'error')
        return render_template('login.html', title='登录')

    @app.route('/admin/logout')
    def admin_logout():
        session.pop('admin_id', None)
        flash('已退出登录', 'success')
        return redirect(url_for('index'))

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        posts = Post.query.order_by(Post.created_at.desc()).all()
        return render_template('admin/dashboard.html', posts=posts,
                               title='文章管理')

    @app.route('/admin/post/new', methods=['GET', 'POST'])
    @login_required
    def post_new():
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            if not title or not content:
                flash('标题和内容不能为空', 'error')
            else:
                post = Post()
                populate_post_from_form(post)
                db.session.add(post)
                base = (sanitize_slug(request.form.get('slug'))
                        or sanitize_slug(title)
                        or datetime.now().strftime('%Y%m%d%H%M%S'))
                post.slug = generate_unique_slug(base)
                db.session.commit()
                flash('文章已创建', 'success')
                return redirect(url_for('admin_dashboard'))
        return render_template('admin/post_form.html', post=None,
                               categories=Category.query.order_by(Category.name).all(),
                               title='写新文章')

    @app.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
    @login_required
    def post_edit(post_id):
        post = db.session.get(Post, post_id)
        if post is None:
            abort(404)
        if request.method == 'POST':
            populate_post_from_form(post)
            base = sanitize_slug(request.form.get('slug')) or sanitize_slug(post.title)
            if not base:
                base = f'post-{post.id}'
            post.slug = generate_unique_slug(base, exclude_id=post.id)
            db.session.commit()
            flash('文章已更新', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/post_form.html', post=post,
                               categories=Category.query.order_by(Category.name).all(),
                               title='编辑文章')

    @app.route('/admin/post/<int:post_id>/toggle', methods=['POST'])
    @login_required
    def toggle_post_publish(post_id):
        post = db.session.get(Post, post_id)
        if post is None:
            abort(404)
        post.published = not post.published
        db.session.commit()
        flash('文章已' + ('发布' if post.published else '下线'), 'success')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
    @login_required
    def post_delete(post_id):
        post = db.session.get(Post, post_id)
        if post is None:
            abort(404)
        db.session.delete(post)
        db.session.commit()
        flash('文章已删除', 'success')
        return redirect(url_for('admin_dashboard'))

    # ---------------- 全局数据与错误页 ----------------

    @app.context_processor
    def inject_common():
        """每个模板都能用：侧栏分类计数、标签云、热门/最近文章"""
        return dict(nav_categories=query_nav_categories(),
                    tag_cloud=query_tag_cloud(),
                    recent_posts=query_recent_posts(),
                    top_posts=query_top_posts())

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html', title='404 页面不存在'), 404

    return app


# 模块级 app 实例：flask CLI（flask run）通过它发现应用；脚本启动走 __main__
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
