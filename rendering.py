"""Markdown 渲染：表现层逻辑独立于数据模型，便于替换与测试。"""
import markdown

MARKDOWN_EXTENSIONS = ['fenced_code', 'tables', 'codehilite', 'toc']
MARKDOWN_CONFIGS = {'codehilite': {'guess_lang': False}}


def render_markdown(text):
    """Markdown 文本 → HTML（含代码高亮、表格、目录）"""
    return markdown.markdown(
        text or '',
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_CONFIGS,
    )
