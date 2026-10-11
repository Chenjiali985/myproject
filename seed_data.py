import os
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from models import Admin, Category, Comment, Post, Tag, db, get_or_create


def _post(title, slug, category, tags, summary, content, days_ago, views=0):
    category_obj = get_or_create(Category, name=category)
    tag_objs = [get_or_create(Tag, name=t) for t in tags]
    post = Post(
        title=title, slug=slug, summary=summary, content=content,
        created_at=datetime.now() - timedelta(days=days_ago),
        views=views, published=True, category_id=category_obj.id)
    post.tags = tag_objs
    db.session.add(post)
    return post


POSTS = [
    dict(
        title='Flask 入门：从零搭建一个博客应用',
        slug='flask-build-blog-from-scratch',
        category='Web 开发',
        tags=['Flask', 'Python'],
        summary='用最少的代码理解 Flask 的核心概念：路由、模板、ORM 与项目组织方式，一步步搭出属于自己的博客。',
        days_ago=2, views=358,
        content='''## 为什么要自己搭博客

市面上的博客平台很多，但自己动手搭一个，能顺带学会 Web 开发的完整链路：
路由、模板渲染、数据库建模、表单处理和部署。

## 技术选型

| 组件 | 选择 | 理由 |
| --- | --- | --- |
| Web 框架 | Flask | 轻量、灵活、学习曲线平缓 |
| 数据库 | SQLite | 零配置，单文件，够用 |
| ORM | Flask-SQLAlchemy | 声明式模型，省去手写 SQL |
| 渲染 | Jinja2 + Markdown | 写作体验好 |

## 项目结构

```text
blog/
├── app.py          # 应用入口与路由
├── models.py       # 数据模型
├── config.py       # 配置
├── templates/      # Jinja2 模板
├── static/         # CSS / JS
└── blog.db         # SQLite 数据库
```

## 最小可运行示例

```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', title='我的博客')
```

## 数据模型

一篇文章通常有：标题、正文（Markdown）、分类、标签、发布时间。

```python
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
```

## 小结

1. 先跑通最小原型，再逐步加功能；
2. 把 Markdown 渲染放在展示层，数据库只存原文；
3. 用 `paginate` 做分页，避免一次性加载全部数据。

下一篇会讲如何在博客里实现分类与标签系统。'''),
    dict(
        title='Python 装饰器完全指南',
        slug='python-decorator-guide',
        category='Python',
        tags=['Python', '进阶'],
        summary='从函数是一等公民讲起，用 5 个渐进式例子彻底搞懂装饰器，包括带参数装饰器与 functools.wrap。',
        days_ago=6, views=512,
        content='''## 函数是对象

在 Python 里，函数可以像普通对象一样被赋值、传参、返回：

```python
def greet():
    return 'hello'

f = greet      # 赋值给变量
print(f())     # hello
```

## 手写第一个装饰器

装饰器本质是"接收函数并返回新函数"的函数：

```python
import time
from functools import wraps

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f'{func.__name__} 耗时 {time.perf_counter() - start:.4f}s')
        return result
    return wrapper

@timer
def work():
    return sum(range(1_000_000))
```

## 带参数的装饰器

再包一层即可接收参数：

```python
def retry(times=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if i == times - 1:
                        raise
        return wrapper
    return decorator

@retry(times=5)
def fetch():
    ...
```

## 三个常见坑

1. 忘记 `@wraps(func)`，丢失原函数的 `__name__` 与文档字符串；
2. 装饰器在**导入时**执行一次，而不是每次调用时；
3. 同一函数可以被多个装饰器叠加，执行顺序是自下而上。

## 适用场景

计时统计、缓存（`lru_cache`）、权限校验、路由注册（Flask 的 `@app.route`）——
本质上都是"在不改动原函数的前提下叠加行为"。'''),
    dict(
        title='SQLite 在小型项目中的实践',
        slug='sqlite-in-small-projects',
        category='数据库',
        tags=['SQLite', '数据库设计'],
        summary='单文件、零配置的 SQLite 是个人项目和原型的最佳选择，这篇文章总结它的适用边界与实用技巧。',
        days_ago=11, views=187,
        content='''## 为什么选 SQLite

- 零配置：不需要安装数据库服务，一个 `.db` 文件就是全部；
- 标准库自带 `sqlite3` 模块，开箱即用；
- 读写性能对中小流量完全够用（本站就在用它）。

## 何时应该换掉它

| 场景 | 建议 |
| --- | --- |
| 多个进程高频并发写入 | 换 PostgreSQL / MySQL |
| 需要复杂权限与网络访问 | 换服务端数据库 |
| 纯读或低频写（博客、配置、缓存） | SQLite 足矣 |

## 常用技巧

开启外键约束（默认是关闭的）：

```python
import sqlite3

conn = sqlite3.connect('blog.db')
conn.execute('PRAGMA foreign_keys = ON')
```

备份数据库只需复制文件，也可以用命令行：

```bash
sqlite3 blog.db ".backup backup.db"
```

查看查询计划，确认索引是否生效：

```sql
EXPLAIN QUERY PLAN SELECT * FROM post WHERE slug = 'python-decorator-guide';
```

## 实践建议

1. 给所有 `WHERE` 高频字段建索引（如 `slug`、`created_at`）；
2. 用 WAL 模式提升并发读性能：`PRAGMA journal_mode = WAL;`
3. 定期 `VACUUM` 回收空间。'''),
    dict(
        title='用 Markdown 高效写作',
        slug='write-efficiently-with-markdown',
        category='工具与效率',
        tags=['Markdown', '写作'],
        summary='Markdown 让你专注内容本身。本文整理最常用的语法与写作工作流，并附上速查表。',
        days_ago=16, views=264,
        content='''## 为什么是 Markdown

纯文本、易版本管理、可渲染成 HTML——Markdown 是技术写作的事实标准。

## 核心语法速查

```markdown
# 一级标题          **加粗**        *斜体*
- 无序列表          1. 有序列表
> 引用              `行内代码`
[链接](https://example.com)   ![图片](img.png)
```

代码块用三个反引号包裹，并标注语言以获得高亮：

```python
print('hello markdown')
```

## 表格

| 语法 | 效果 |
| --- | --- |
| `**粗体**` | **粗体** |
| `` `代码` `` | `代码` |

## 我的写作工作流

1. 先用列表写大纲，确认逻辑再展开；
2. 正文里少用加粗和标题层级，重点靠内容而不是样式；
3. 代码示例务必可运行，贴出关键片段即可；
4. 发布前通读一遍，删掉所有"其实没必要的话"。'''),
    dict(
        title='生成器与协程：Python 迭代的进阶之路',
        slug='python-generator-and-coroutine',
        category='Python',
        tags=['Python', '异步编程'],
        summary='从 yield 到 async/await，理清生成器、迭代器与协程之间的关系，写出更省内存的代码。',
        days_ago=22, views=301,
        content='''## 生成器：惰性求值

处理大文件或大集合时，生成器逐条产出数据，内存占用恒定：

```python
def read_large(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            yield line.strip()

total = sum(len(line) for line in read_large('access.log'))
```

## 生成器表达式

```python
squares = (x * x for x in range(10))  # 注意是圆括号
```

## 从 yield 到协程

`yield` 还能接收数据，形成双向通道——这正是早期协程的实现方式：

```python
def averager():
    total, count = 0.0, 0
    avg = None
    while True:
        value = yield avg
        total += value
        count += 1
        avg = total / count
```

## 现代写法：async / await

如今并发场景直接用原生协程：

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f'{name} done'

async def main():
    results = await asyncio.gather(
        fetch('a', 1), fetch('b', 2))
    print(results)

asyncio.run(main())
```

## 一句话总结

- 迭代器：描述"如何取值"；
- 生成器：最简洁的迭代器实现；
- 协程：可以暂停与恢复的函数，用于并发。'''),
    dict(
        title='CSS Grid 布局快速上手',
        slug='css-grid-quick-start',
        category='Web 开发',
        tags=['CSS', '前端'],
        summary='用 10 分钟学会 CSS Grid 的核心概念：容器、轨道、区域与响应式布局，告别 Float 时代。',
        days_ago=28, views=221,
        content='''## 两行代码实现响应式卡片

```css
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
}
```

`auto-fill` + `minmax` 的组合能自动决定每行放几列，是卡片布局的最佳实践。

## 核心概念

- **容器**：设置 `display: grid` 的元素；
- **轨道**：`grid-template-columns` / `grid-template-rows` 定义的行列；
- **区域**：用命名网格规划整体版式。

## 命名区域排版

```css
.page {
    display: grid;
    grid-template-areas:
        'header header'
        'main   aside'
        'footer footer';
    grid-template-columns: 1fr 300px;
}
.header  { grid-area: header; }
.aside   { grid-area: aside; }
```

## 常用技巧

1. `gap` 同时控制行列间距，不需要负 margin；
2. `fr` 单位按比例分配剩余空间；
3. 配合 `@media` 在窄屏时把 `aside` 移到下方，几行即可完成响应式改造。'''),
    dict(
        title='Git 常用命令备忘录',
        slug='git-cheat-sheet',
        category='工具与效率',
        tags=['Git', '效率工具'],
        summary='把最常用、最容易忘的 Git 命令整理成一页备忘录：撤销、回退、分支、暂存与排查问题。',
        days_ago=35, views=431,
        content='''## 日常提交

```bash
git status                 # 查看状态
git add -p                 # 交互式暂存，按块选择
git commit -m 'feat: xxx'  # 提交
```

## 撤销与回退

```bash
git restore file.txt        # 丢弃工作区改动
git restore --staged a.py   # 取消暂存
git reset --soft HEAD~1     # 撤销上次提交，保留改动
git revert <commit>         # 生成反向提交，适合公共分支
```

> 千万不要对已推送的公共分支使用 `reset --hard` + 强推。

## 分支操作

```bash
git switch -c feature/login   # 创建并切换
git merge --no-ff dev         # 保留合并记录
git rebase main               # 变基，保持线性历史
git branch -d feature/login   # 删除已合并分支
```

## 排查问题

```bash
git log --oneline --graph -20   # 图形化历史
git blame -L 10,20 file.py      # 查每行最后修改者
git bisect start                # 二分定位引入 bug 的提交
```

## 实用别名

```bash
git config --global alias.st 'status -sb'
git config --global alias.lg "log --oneline --graph --all"
```'''),
    dict(
        title='我的 2026 开发环境清单',
        slug='my-2026-dev-setup',
        category='随笔',
        tags=['工具', '随笔'],
        summary='记录目前每天在用的开发工具与配置习惯，原则只有一条：少即是多。',
        days_ago=42, views=156,
        content='''## 原则

工具不在多，在于顺手。每年做一次大扫除，删掉一个月没打开的软件。

## 硬件与系统

- 27 寸 4K 显示器 + 笔记本支架，久坐党的腰比什么都重要；
- Windows Terminal + WSL2，兼顾日常与 Linux 环境。

## 编辑器

VS Code 依然是主力，离不开的几个扩展：

1. Python / Pylance
2. GitLens —— 追溯每行代码的来历
3. Error Lens —— 把报错直接写在行内

## 终端里的三件套

```bash
# 代替 cd 的 zoxide
z blog

# 代替 ls 的 eza
eza --icons

# 替代 ctrl+r 搜历史
fzf
```

## 最后

环境是为工作服务的。与其折腾配置，不如把时间花在写出更好的代码上。'''),
]

COMMENTS = [
    ('flask-build-blog-from-scratch', '小白', '跟着写了一遍，终于把博客跑起来了，感谢分享！'),
    ('flask-build-blog-from-scratch', 'Ray', '建议补一讲部署到云服务器的部分。'),
    ('python-decorator-guide', 'Momo', '装饰器执行顺序那个坑我踩过，自下而上记住了。'),
]


def seed_if_empty():
    if Admin.query.first() is not None or Post.query.first() is not None:
        return

    db.session.add(Admin(
        username=os.environ.get('ADMIN_USERNAME', 'admin'),
        password_hash=generate_password_hash(
            os.environ.get('ADMIN_PASSWORD', 'admin123'))))

    for item in POSTS:
        _post(**item)

    for slug, name, content in COMMENTS:
        post = Post.query.filter_by(slug=slug).first()
        if post:
            db.session.add(Comment(post_id=post.id, name=name, content=content))

    db.session.commit()
