import os
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from models import Admin, Category, Comment, Post, Tag, db, get_or_create


def _build_post(title, slug, category_name, tag_names, summary, content,
                days_ago, views=0):
    category_instance = get_or_create(Category, name=category_name)
    tag_instances = [get_or_create(Tag, name=tag_name) for tag_name in tag_names]
    post = Post(
        title=title, slug=slug, summary=summary, content=content,
        created_at=datetime.now() - timedelta(days=days_ago),
        views=views, published=True, category_id=category_instance.id)
    post.tags = tag_instances
    db.session.add(post)
    return post

from seed_content import SEED_COMMENTS, SEED_POSTS


def seed_if_empty():
    if Admin.query.first() is not None or Post.query.first() is not None:
        return

    db.session.add(Admin(
        username=os.environ.get('ADMIN_USERNAME', 'admin'),
        password_hash=generate_password_hash(
            os.environ.get('ADMIN_PASSWORD', 'admin123'))))

    for item in SEED_POSTS:
        _build_post(**item)

    for slug, name, content in SEED_COMMENTS:
        post = Post.query.filter_by(slug=slug).first()
        if post:
            db.session.add(Comment(post_id=post.id, name=name, content=content))

    db.session.commit()
