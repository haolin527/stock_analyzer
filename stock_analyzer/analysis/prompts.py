"""AI 分析 Prompt 模板"""

import pandas as pd

from stock_analyzer.data.base import StockQuote, IndexQuote, NewsItem

SYSTEM_PROMPT = """你是一位专业的股票分析师，拥有丰富的技术分析和基本面分析经验。

你的任务是根据提供的行情数据、大盘指数、财经新闻和历史K线数据，对每只自选股进行分析并给出操作建议。

## 输出要求

以 JSON 数组格式输出，每个元素包含以下字段：

- `code`: 股票代码
- `name`: 股票名称
- `action`: 操作建议，必须为以下之一："买入"、"持有"、"卖出"、"观望"
- `confidence`: 置信度，必须为以下之一："高"、"中"、"低"
- `reasoning`: 分析理由，需包含技术面和消息面两个维度，每条理由 30-80 字
- `related_news`: 与该股票相关的新闻标题列表（从提供的新闻中匹配，无关联则为空数组）

## 分析原则

1. 技术面：基于涨跌幅、成交量、历史K线趋势综合判断
2. 消息面：关联相关新闻，评估利好/利空影响
3. 跨市场：考虑A股/港股/美股的联动效应
4. 保守倾向：不确定时优先给出"持有"或"观望"，避免激进建议
5. 每只股票都必须分析，不可跳过

请用 ```json 和 ``` 包裹 JSON 输出。"""


def build_user_prompt(
    quotes: list[StockQuote],
    indexes: list[IndexQuote],
    news: list[NewsItem],
    histories: dict[str, pd.DataFrame] | None = None,
) -> str:
    """构建发送给 Claude 的用户 prompt。

    Args:
        quotes: 自选股行情列表
        indexes: 大盘指数列表
        news: 新闻列表
        histories: 股票代码到历史K线DataFrame的映射，可选

    Returns:
        格式化的 prompt 字符串
    """
    sections: list[str] = []

    # 标题
    sections.append("请对以下自选股进行分析，给出操作建议。")
    sections.append("")

    # ── 大盘指数 ──
    sections.append("## 大盘指数")
    sections.append("")

    for market, label in [("A", "A股"), ("HK", "港股"), ("US", "美股")]:
        market_indexes = [i for i in indexes if i.market == market]
        if market_indexes:
            sections.append(f"### {label}")
            for idx in market_indexes:
                direction = "📈" if idx.change_pct > 0 else "📉" if idx.change_pct < 0 else "➡️"
                sections.append(
                    f"- {direction} {idx.name}（{idx.code}）："
                    f"{idx.latest:.2f}，涨跌幅 {idx.change_pct:+.2f}%"
                )
            sections.append("")

    # ── 自选股行情 ──
    sections.append("## 自选股行情")
    sections.append("")

    for market, label in [("A", "A股"), ("HK", "港股"), ("US", "美股")]:
        market_quotes = [q for q in quotes if q.market == market]
        if not market_quotes:
            continue

        # 表头
        sections.append(f"### {label}")
        sections.append("| 代码 | 名称 | 现价 | 涨跌幅 | 成交量(手) | 成交额 |")
        sections.append("|------|------|------|--------|------------|--------|")

        for q in market_quotes:
            sections.append(
                f"| {q.code} | {q.name} | {q.price:.2f} | "
                f"{q.change_pct:+.2f}% | {q.volume:,.0f} | "
                f"{q.turnover:,.0f} |"
            )
        sections.append("")

    # ── 历史K线概要 ──
    if histories:
        sections.append("## 近期走势（最近5个交易日）")
        sections.append("")
        for code, df in histories.items():
            if df.empty or len(df) < 2:
                continue
            recent = df.tail(5)
            name = _find_name(code, quotes)
            changes = []
            for _, row in recent.iterrows():
                date_str = row["date"].strftime("%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])[-5:]
                changes.append(f"{date_str}: {row['close']:.2f}")
            sections.append(f"- **{name}**（{code}）：{' → '.join(changes)}")
        sections.append("")

    # ── 财经新闻 ──
    if news:
        sections.append("## 今日财经新闻")
        sections.append("")
        for i, n in enumerate(news, 1):
            time_str = f"[{n.time}] " if n.time else ""
            source_str = f"（来源：{n.source}）" if n.source else ""
            sections.append(f"{i}. {time_str}{n.title}{source_str}")
        sections.append("")

    # ── 分析指令 ──
    sections.append("## 分析指令")
    sections.append("")
    sections.append("请对以上每只自选股进行分析，输出 JSON 数组。")
    sections.append("每只股票的分析需包含：")
    sections.append("1. 技术面判断（基于涨跌幅、成交量、近期走势）")
    sections.append("2. 消息面判断（关联上方新闻中与该股相关的条目）")
    sections.append("3. 综合操作建议（买入/持有/卖出/观望）")
    sections.append("")
    sections.append("请用 ```json 和 ``` 包裹 JSON 输出。")

    return "\n".join(sections)


def _find_name(code: str, quotes: list[StockQuote]) -> str:
    """根据代码查找股票名称"""
    for q in quotes:
        if q.code == code:
            return q.name
    return code
