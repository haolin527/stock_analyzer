"""报告生成引擎 — 组装 Markdown 日报"""

from datetime import date

from stock_analyzer.data.base import StockQuote, IndexQuote, NewsItem

# 尝试导入 StockAnalysis，如果 analysis 模块尚未就绪则使用 fallback
try:
    from stock_analyzer.analysis.analyzer import StockAnalysis
except ImportError:
    StockAnalysis = None  # type: ignore


class ReportBuilder:
    """Markdown 报告组装器。

    将行情数据、指数、新闻和 AI 分析结果组装为结构化的日报。
    """

    def __init__(self, project_name: str = "stock_analyzer"):
        self.project_name = project_name

    def build(
        self,
        quotes: list[StockQuote],
        indexes: list[IndexQuote],
        news: list[NewsItem],
        analyses: list | None = None,  # list[StockAnalysis] | None
        errors: list[str] | None = None,
    ) -> str:
        """构建完整的 Markdown 日报。

        Args:
            quotes: 自选股行情列表
            indexes: 大盘指数列表
            news: 财经新闻列表
            analyses: AI 分析结果列表，None 表示 AI 不可用
            errors: 数据采集中的错误信息列表

        Returns:
            格式化的 Markdown 报告字符串
        """
        today = date.today()
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[today.weekday()]

        sections: list[str] = []

        # ── 标题 ──
        sections.append(f"# 📈 股市早报 | {today} ({weekday})")
        sections.append("")

        # ── 错误告警 ──
        if errors:
            sections.append("> ⚠️ **数据采集警告**")
            for err in errors:
                sections.append(f"> - {err}")
            sections.append("")

        # ── 大盘风向 ──
        sections.append("## 📊 大盘风向")
        sections.append("")

        for market, label in [("A", "A股市场"), ("HK", "港股市场"), ("US", "美股市场")]:
            market_indexes = [i for i in indexes if i.market == market]
            if not market_indexes:
                continue
            sections.append(f"### {label}")
            sections.append("")
            sections.append("| 指数 | 最新价 | 涨跌幅 | 涨跌额 |")
            sections.append("|------|--------|--------|--------|")
            for idx in market_indexes:
                sections.append(
                    f"| {idx.name} | {idx.latest:.2f} | "
                    f"{idx.change_pct:+.2f}% | {idx.change_amount:+.2f} |"
                )
            sections.append("")

        # ── 自选股明细 ──
        sections.append("## 💼 自选股明细")
        sections.append("")

        for market, label in [("A", "A股"), ("HK", "港股"), ("US", "美股")]:
            market_quotes = [q for q in quotes if q.market == market]
            if not market_quotes:
                continue

            sections.append(f"### {label}")
            sections.append("")

            for q in market_quotes:
                # 颜色 emoji：A股红涨绿跌，海外绿涨红跌
                if market == "A":
                    emoji = "🔴" if q.change_pct > 0 else "🟢" if q.change_pct < 0 else "⚪"
                else:
                    emoji = "🟢" if q.change_pct > 0 else "🔴" if q.change_pct < 0 else "⚪"

                # 基本信息行
                sections.append(
                    f"**{q.name}**（`{q.code}`） | "
                    f"现价 {q.price:.2f} | "
                    f"{emoji} {q.change_pct:+.2f}% | "
                    f"成交额 {q.turnover:,.0f}"
                )

                # AI 分析（如果有）
                if analyses is not None and StockAnalysis is not None:
                    matched = _find_analysis(q.code, analyses)
                    if matched:
                        sections.append(f"> 🎯 **操作建议：{matched.action}**（置信度：{matched.confidence}）")
                        if matched.reasoning:
                            # 缩进显示理由
                            for line in matched.reasoning.split("\n"):
                                line = line.strip()
                                if line:
                                    sections.append(f"> {line}")
                        if matched.related_news:
                            sections.append(f"> 📰 相关新闻：")
                            for rn in matched.related_news:
                                sections.append(f">   - {rn}")
                    else:
                        sections.append(f"> 🎯 无分析结果")
                elif analyses is None:
                    sections.append(f"> ⚠️ AI分析暂时不可用")

                sections.append("")

        # ── 今日要闻 ──
        if news:
            sections.append("## 📰 今日要闻")
            sections.append("")
            for i, n in enumerate(news, 1):
                time_prefix = f"`{n.time}` " if n.time else ""
                source_suffix = f" — {n.source}" if n.source else ""
                sections.append(f"{i}. {time_prefix}{n.title}{source_suffix}")
            sections.append("")

        # ── 智能筛选 ──
        # （全市场扫描暂不可用，标注为待修复）
        sections.append("## 🔍 智能筛选")
        sections.append("")
        sections.append("> ⚠️ 全市场扫描功能暂不可用（数据源连接不稳定），")
        sections.append("> 当前仅分析自选股池。修复后将恢复放量/涨跌幅/换手率/超卖筛选。")
        sections.append("")

        # ── 免责声明 ──
        sections.append("---")
        sections.append("")
        sections.append(
            "⚠️ **免责声明**：以上分析由AI生成，仅供参考，不构成投资建议。"
            "投资有风险，入市需谨慎。请结合自身情况做出独立判断。"
        )

        return "\n".join(sections)


def _find_analysis(code: str, analyses: list) -> object | None:
    """根据股票代码查找对应的 AI 分析结果。

    Args:
        code: 股票代码
        analyses: StockAnalysis 列表

    Returns:
        匹配的 StockAnalysis 或 None
    """
    for a in analyses:
        a_code = getattr(a, "code", "")
        # 兼容不同代码格式（如 000858 vs 000858.SZ）
        if a_code == code or a_code.startswith(code) or code.startswith(a_code):
            return a
    return None
