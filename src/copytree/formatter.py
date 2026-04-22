"""输出格式化：纯文本和 Markdown。"""


def format_text(tree_text: str) -> str:
    """返回原始树状文本。"""
    return tree_text


def format_markdown(tree_text: str) -> str:
    """将树状文本包裹在 Markdown 代码块中。"""
    return f"```\n{tree_text}\n```"


def format_output(tree_text: str, fmt: str) -> str:
    """根据格式类型分发格式化。"""
    if fmt == "markdown":
        return format_markdown(tree_text)
    return format_text(tree_text)
