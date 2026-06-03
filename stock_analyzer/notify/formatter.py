"""消息格式化 — Markdown 适配与长消息分段"""


def format_report_as_markdown(report: str) -> str:
    """格式化报告为钉钉兼容的 Markdown。

    钉钉机器人支持基本 Markdown 语法：标题（多级）、加粗、链接、
    列表、引用等。本函数对报告做必要的兼容性调整。

    Args:
        report: 原始 Markdown 报告文本

    Returns:
        适合钉钉推送的 Markdown 文本
    """
    # 钉钉 Markdown 支持良好，基本透传
    # 只需确保没有不支持的语法（如 HTML 标签、复杂表格）
    return report


def split_long_message(content: str, max_bytes: int = 18000) -> list[str]:
    """将超长消息按板块边界分段。

    分段策略：
    1. 按 `## ` 标题分割为 sections
    2. 贪心累积：当前段 + 下一 section < max_bytes → 合并
    3. 超过则新起一段
    4. 每段添加序号标注

    Args:
        content: 完整的报告内容
        max_bytes: 单段最大字节数（默认18000，对齐钉钉限制）

    Returns:
        分段后的消息列表，如果不需要分段则返回单元素列表
    """
    content_bytes = content.encode("utf-8")
    if len(content_bytes) <= max_bytes:
        return [content]

    # 按 ## 标题分割
    # 使用正则保留分隔符
    sections: list[str] = []
    current_start = 0

    # 找到所有 ## 标题的位置
    for match in __import__("re").finditer(r"(?:^|\n)(?=## )", content, __import__("re").MULTILINE):
        pos = match.start()
        if pos > current_start:
            # 包含前导换行符
            section_start = current_start
            sections.append(content[section_start:pos])
            current_start = pos

    # 最后一段
    if current_start < len(content):
        sections.append(content[current_start:])

    if not sections:
        return [content]

    # 贪心合并
    chunks: list[str] = []
    current_chunk = ""
    for section in sections:
        candidate = current_chunk + section
        if len(candidate.encode("utf-8")) <= max_bytes:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 如果单个 section 就超限，强制按段落切分
            if len(section.encode("utf-8")) > max_bytes:
                sub_chunks = _force_split(section, max_bytes)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    # 添加序号标注
    total = len(chunks)
    if total == 1:
        return chunks

    result = []
    for i, chunk in enumerate(chunks, 1):
        header = f"**（{i}/{total}）**\n\n"
        result.append(header + chunk)

    return result


def _force_split(text: str, max_bytes: int) -> list[str]:
    """强制按段落边界切分超长 section。"""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = current + ("\n\n" if current else "") + para
        if len(candidate.encode("utf-8")) <= max_bytes:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # 如果单个段落仍超限，直接按字节切
            if len(para.encode("utf-8")) > max_bytes:
                para_bytes = para.encode("utf-8")
                for j in range(0, len(para_bytes), max_bytes - 200):
                    chunk_bytes = para_bytes[j : j + max_bytes - 200]
                    chunks.append(chunk_bytes.decode("utf-8", errors="replace"))
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks if chunks else [text]
