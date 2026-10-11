import os
import warnings

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 仅开发环境默认值；生产部署必须通过环境变量 SECRET_KEY 覆盖
    SECRET_KEY = os.environ.get('SECRET_KEY', 'boke-dev-secret-key-change-me')
    if 'SECRET_KEY' not in os.environ:
        warnings.warn('SECRET_KEY 未配置，正在使用开发默认值，生产部署前请设置环境变量',
                      stacklevel=2)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'blog.db'))
    POSTS_PER_PAGE = 6
