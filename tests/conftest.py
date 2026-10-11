"""pytest 全局配置：在导入 app 之前完成路径与测试环境隔离。"""
import os
import sys

# 让 tests/ 下的用例可以导入项目根目录中的 app 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 必须在 import app 之前设置：测试使用独立的内存数据库，绝不污染开发用的 blog.db
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
