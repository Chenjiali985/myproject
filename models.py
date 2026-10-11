from datetime import datetime

import markdown
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

MARKDOWN_EXTENSIONS = ['fenced_code', 'tables', 'codehilite', 'toc']
MARKDOWN_CONFIGS = {'codehilite': {'guess_lang': False}}


def get_or_create(model, **kwargs):
    obj = model.query.filter_by(**kwargs).first()
    if obj is None:
        obj = model(**kwargs)
        db.session.add(obj)
        db.session.flush()
    return obj


post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', backref='category', lazy='dynamic')


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', secondary=post_tags,
                            backref=db.backref('tags', lazy='joined'),
                            lazy='dynamic')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now,
                           onupdate=datetime.now, nullable=False)
    views = db.Column(db.Integer, default=0, nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    comments = db.relationship('Comment', backref='post',
                               cascade='all, delete-orphan', lazy='dynamic')

    @property
    def html(self):
        return markdown.markdown(
            self.content or '',
            extensions=MARKDOWN_EXTENSIONS,
            extension_configs=MARKDOWN_CONFIGS,
        )


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
