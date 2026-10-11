import functools
import re
from datetime import datetime

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from config import Config
from models import Admin, Category, Comment, Post, Tag, db, get_or_create
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


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_if_empty()

    def paginated_posts(extra_filter=None):
        query = Post.query.filter_by(published=True)
        if extra_filter is not None:
            query = query.filter(extra_filter)
        return query.order_by(Post.created_at.desc()).paginate(
            page=request.args.get('page', 1, type=int),
            per_page=app.config['POSTS_PER_PAGE'],
            error_out=False)

    def unique_slug(base, exclude_id=None):
        slug, i = base, 2
        while True:
            query = Post.query.filter_by(slug=slug)
            if exclude_id:
                query = query.filter(Post.id != exclude_id)
            if query.first() is None:
                return slug
            slug = f'{base}-{i}'
            i += 1

    def fill_post_from_form(post):
        post.title = request.form['title'].strip()
        post.content = request.form.get('content', '').replace('\r\n', '\n')
        post.summary = request.form.get('summary', '').strip() or None
        post.published = request.form.get('published') == 'on'
        slug = sanitize_slug(request.form.get('slug'))
        if slug:
            post.slug = slug
        new_cat = request.form.get('new_category', '').strip()
        if new_cat:
            category = get_or_create(Category, name=new_cat)
        else:
            cid = request.form.get('category_id', type=int)
            category = db.session.get(Category, cid) if cid else None
        raw_tags = request.form.get('tags', '')
        names = [n for n in (s.strip() for s in re.split(r'[,，]', raw_tags)) if n]
        tags = [get_or_create(Tag, name=n) for n in names]
        post.category_id = category.id if category else None
        post.tags = tags

    # ---------------- 公开页面 ----------------

    @app.route('/')
    def index():
        p = paginated_posts()
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
        p = paginated_posts(Post.category_id == cat.id)
        return render_template('list.html', posts=p.items, pagination=p,
                               endpoint='category', title=f'分类：{name}',
                               subtitle=None, kwargs={'name': name})

    @app.route('/tag/<name>')
    def tag(name):
        t = Tag.query.filter_by(name=name).first_or_404()
        p = paginated_posts(Post.tags.contains(t))
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
            like = f'%{q}%'
            query = Post.query.filter(
                Post.published.is_(True),
                db.or_(Post.title.ilike(like), Post.summary.ilike(like),
                       Post.content.ilike(like)))
            p = query.order_by(Post.created_at.desc()).paginate(
                page=request.args.get('page', 1, type=int),
                per_page=app.config['POSTS_PER_PAGE'], error_out=False)
        else:
            p = paginated_posts()
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
                post = Post(title=title)
                fill_post_from_form(post)
                db.session.add(post)
                base = (sanitize_slug(request.form.get('slug'))
                        or sanitize_slug(title)
                        or datetime.now().strftime('%Y%m%d%H%M%S'))
                post.slug = unique_slug(base)
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
            fill_post_from_form(post)
            base = sanitize_slug(request.form.get('slug')) or sanitize_slug(post.title)
            if not base:
                base = f'post-{post.id}'
            post.slug = unique_slug(base, exclude_id=post.id)
            db.session.commit()
            flash('文章已更新', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/post_form.html', post=post,
                               categories=Category.query.order_by(Category.name).all(),
                               title='编辑文章')

    @app.route('/admin/post/<int:post_id>/toggle', methods=['POST'])
    @login_required
    def post_toggle(post_id):
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
        cat_counts = []
        for c in Category.query.order_by(Category.name).all():
            n = c.posts.filter_by(published=True).count()
            if n:
                cat_counts.append((c, n))
        tag_counts = sorted(
            ((t, t.posts.filter_by(published=True).count())
             for t in Tag.query.order_by(Tag.name).all()),
            key=lambda item: (-item[1], item[0].name))
        recent = (Post.query.filter_by(published=True)
                  .order_by(Post.created_at.desc()).limit(5).all())
        top = (Post.query.filter_by(published=True)
               .order_by(Post.views.desc()).limit(5).all())
        return dict(nav_categories=cat_counts, tag_cloud=tag_counts[:15],
                    recent_posts=recent, top_posts=top)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html', title='404 页面不存在'), 404

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
