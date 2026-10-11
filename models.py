from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from rendering import render_markdown

db = SQLAlchemy()


def local_now():
    """站点统一使用服务器本地时间（个人单时区博客，不涉及时区换算）"""
    return datetime.now()


def get_or_create(model, **kwargs):
    obj = model.query.filter_by(**kwargs).first()
    if obj is None:
        obj = model(**kwargs)
        db.session.add(obj)
        db.session.flush()
    return obj


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', backref=db.backref('category'),
                            lazy='dynamic')


# 文章 ↔ 标签 多对多关联表（数据库表名保持 post_tags 不变，兼容已有 blog.db）
post_tag_table = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', secondary=post_tag_table,
                            backref=db.backref('tags', lazy='joined'),
                            lazy='dynamic')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now,
                           onupdate=local_now, nullable=False)
    views = db.Column(db.Integer, default=0, nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    comments = db.relationship('Comment', backref=db.backref('post'),
                               cascade='all, delete-orphan', lazy='dynamic')

    @property
    def html(self):
        return render_markdown(self.content)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
