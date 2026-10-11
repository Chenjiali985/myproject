"""sanitize_slug 函数的单元测试。

被测函数（app.py）：
    def sanitize_slug(raw):
        return re.sub(r'[^\\w-]+', '-', (raw or '').strip()).strip('-').lower()
（即：把非“单词字符/连字符”的片段替换为横线，再去首尾横线并转小写）

测试矩阵：正常输入 / 大小写 / 空白 / 标点 / 保留字符 / 空值与异常输入 /
          Unicode（中文等）/ 真实博客标题 / 返回类型 / 幂等性
"""
import pytest

from app import sanitize_slug


# ---------- 1. 正常英文标题 ----------
@pytest.mark.parametrize('raw, expected', [
    ('Hello World', 'hello-world'),
    ('My First Blog Post', 'my-first-blog-post'),
], ids=['两词标题', '多词标题'])
def test_normal_english_titles(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 2. 大写统一转小写 ----------
@pytest.mark.parametrize('raw, expected', [
    ('Mixed CASE Title', 'mixed-case-title'),
    ('ALL CAPS', 'all-caps'),
    ('python', 'python'),
], ids=['大小写混杂', '全大写', '已全小写'])
def test_lowercase_conversion(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 3. 空白处理 ----------
@pytest.mark.parametrize('raw, expected', [
    ('  Hello World  ', 'hello-world'),   # 首尾空格被 strip，不产生横线
    ('Hello   World', 'hello-world'),     # 连续空格被 + 量词合并为一个 "-"
    ('hello\tworld\n', 'hello-world'),    # 制表符替换、尾部换行 strip
], ids=['首尾空格', '连续空格合并', '制表符与换行'])
def test_whitespace_handling(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 4. 标点符号处理 ----------
@pytest.mark.parametrize('raw, expected', [
    ('Hello, World!', 'hello-world'),       # ", " 合并为一个 "-"，尾部 ! 替换后 strip
    ('###Test###', 'test'),                 # 首尾 # 替换后再 strip('-')
    ('a/b\\c', 'a-b-c'),                    # 斜杠/反斜杠分别替换
    ('C++', 'c'),                           # 两个 + 合并为 "-"，尾部 strip
    ('Python: Great? Yes!', 'python-great-yes'),
], ids=['逗号感叹号', '首尾井号', '正反斜杠', '加号', '冒号问号'])
def test_punctuation_replaced_and_trimmed(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 5. 合法 URL 字符原样保留（下划线与已有连字符） ----------
@pytest.mark.parametrize('raw, expected', [
    ('Python_Foo-Bar', 'python_foo-bar'),
    ('hello--world', 'hello--world'),      # 已有连字符不属于 [^\w-]，不压缩
    ('hello___world', 'hello___world'),    # 下划线是 \w，原样保留
    ('-lead-trail-', 'lead-trail'),        # 仅“首尾横线”会被 strip，内部保留
], ids=['下划线与连字符', '连续横线不压缩', '连续下划线', '首尾横线清理'])
def test_reserved_url_chars(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 6. 空值、None 与“无有效字符”的输入 ----------
@pytest.mark.parametrize('raw', ['', None, '   ', '!!!', '###', '/ \\ ?'],
                         ids=['空字符串', 'None', '纯空白', '纯标点',
                              '纯井号', '纯分隔符号'])
def test_empty_like_inputs_return_empty_string(raw):
    assert sanitize_slug(raw) == ''


# ---------- 7. Unicode / 中文：\w 在 Python 正则中默认开启 Unicode 模式 ----------
@pytest.mark.parametrize('raw, expected', [
    ('Flask 入门教程', 'flask-入门教程'),
    ('你好', '你好'),
    ('Ñoño Café', 'ñoño-café'),             # 带重音的拉丁字母同样属于 \w
], ids=['中英混合', '纯中文', '重音拉丁字母'])
def test_unicode_letters_are_words(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 8. 真实博客标题（含全角标点） ----------
@pytest.mark.parametrize('raw, expected', [
    # 全角冒号“：”、全角感叹号“！”都不是 \w → 替换为 "-"，尾部再 strip
    ('Flask 入门：从零搭建一个博客应用！', 'flask-入门-从零搭建一个博客应用'),
    # 半角点号会被替换；版本号仍能形成可读 slug
    ('Python 3.12 新特性', 'python-3-12-新特性'),
], ids=['全角标点标题', '含版本号标题'])
def test_real_world_chinese_titles(raw, expected):
    assert sanitize_slug(raw) == expected


# ---------- 9. 对任意输入，返回值类型始终是 str，且满足 slug 不变量 ----------
@pytest.mark.parametrize('raw', [
    'Hello World', '', None, '   ', '!!!', 'Flask 入门教程', 'C++',
])
def test_output_invariants(raw):
    result = sanitize_slug(raw)
    assert isinstance(result, str)          # None 也安全返回字符串，不抛异常
    assert result == result.lower()         # 不含大写字母
    assert ' ' not in result                # 不含空格
    assert not result.startswith('-')       # 不以横线开头
    assert not result.endswith('-')         # 不以横线结尾


# ---------- 10. 幂等性：对生成结果再处理一次，结果不变 ----------
@pytest.mark.parametrize('raw', [
    'Hello World', '  Flask 入门：教程！ ', '###C++', 'Python_Foo-Bar',
])
def test_idempotent(raw):
    once = sanitize_slug(raw)
    twice = sanitize_slug(once)
    assert once == twice
