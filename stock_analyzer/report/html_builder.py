"""HTML 报告生成器 — 生成精美的股票分析日报网页"""

from datetime import date
from typing import Optional

from stock_analyzer.data.base import StockQuote, IndexQuote, NewsItem

try:
    from stock_analyzer.analysis.analyzer import StockAnalysis
except ImportError:
    StockAnalysis = None  # type: ignore


class HtmlReportBuilder:
    """生成自包含的 HTML 股票分析日报。"""

    def __init__(self, project_name: str = "stock_analyzer"):
        self.project_name = project_name

    def build(
        self,
        quotes: list[StockQuote],
        indexes: list[IndexQuote],
        news: list[NewsItem],
        analyses: Optional[list] = None,
        errors: list[str] | None = None,
    ) -> str:
        """构建完整 HTML 报告。"""
        today = date.today()
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[today.weekday()]
        title = f"📈 股市早报 | {today} ({weekday})"

        # 构建分析索引
        analysis_map: dict[str, object] = {}
        if analyses and StockAnalysis:
            for a in analyses:
                analysis_map[getattr(a, "code", "")] = a

        html_parts = [
            self._html_head(title),
            self._body_open(),
            self._header(title),
        ]

        # 错误告警
        if errors:
            html_parts.append(self._error_alert(errors))

        # 市场概览卡片
        html_parts.append(self._market_overview(indexes, quotes))

        # 大盘指数
        html_parts.append(self._index_section(indexes))

        # 自选股明细
        html_parts.append(self._watchlist_section(quotes, analysis_map, analyses))

        # 今日要闻
        html_parts.append(self._news_section(news))

        # 智能筛选
        html_parts.append(self._screener_note())

        # 免责声明
        html_parts.append(self._disclaimer())

        html_parts.append(self._body_close())
        return "\n".join(html_parts)

    # ── HTML 模板片段 ──

    def _html_head(self, title: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", "Helvetica Neue", sans-serif;
    background: #f5f7fa; color: #1a1a2e; line-height: 1.6;
}}
.container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
.header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white; padding: 32px 24px; border-radius: 16px; margin-bottom: 20px;
    text-align: center;
}}
.header h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 4px; }}
.header .date {{ font-size: 14px; opacity: 0.8; }}
.card {{
    background: white; border-radius: 12px; padding: 24px; margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}
.card h2 {{ font-size: 18px; margin-bottom: 16px; padding-bottom: 8px;
             border-bottom: 2px solid #e8ecf1; }}
.alert {{
    background: #fff3cd; border: 1px solid #ffc107; border-radius: 10px;
    padding: 14px 20px; margin-bottom: 16px; font-size: 14px; color: #856404;
}}
/* 概览卡片 */
.overview-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }}
.overview-item {{
    background: white; border-radius: 12px; padding: 18px; text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}
.overview-item .label {{ font-size: 12px; color: #8c8c8c; margin-bottom: 6px; }}
.overview-item .value {{ font-size: 24px; font-weight: 700; }}
.up {{ color: #cf1322; }} .down {{ color: #389e0d; }} .neutral {{ color: #8c8c8c; }}
/* 表格 */
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ background: #f8f9fb; padding: 10px 12px; text-align: left; font-weight: 600;
      color: #595959; border-bottom: 2px solid #e8ecf1; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }}
tr:hover {{ background: #f8f9fb; }}
/* 股票分析卡片 */
.stock-card {{
    border: 1px solid #e8ecf1; border-radius: 10px; padding: 16px;
    margin-bottom: 10px; transition: box-shadow 0.2s;
}}
.stock-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.stock-card .stock-header {{
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
}}
.stock-card .stock-name {{ font-size: 16px; font-weight: 600; }}
.stock-card .stock-code {{ font-size: 12px; color: #8c8c8c; margin-left: 8px; }}
.stock-card .stock-meta {{ font-size: 13px; color: #595959; margin-top: 4px; }}
.action-badge {{
    display: inline-block; padding: 3px 12px; border-radius: 20px;
    font-size: 13px; font-weight: 600;
}}
.action-买入 {{ background: #fff1f0; color: #cf1322; }}
.action-持有 {{ background: #e6f7ff; color: #096dd9; }}
.action-卖出 {{ background: #f6ffed; color: #389e0d; }}
.action-观望 {{ background: #fff7e6; color: #d46b08; }}
.conf-高 {{ opacity: 1; }} .conf-中 {{ opacity: 0.85; }} .conf-低 {{ opacity: 0.65; }}
.reasoning {{ font-size: 13px; color: #595959; margin-top: 8px; padding-left: 12px;
               border-left: 3px solid #e8ecf1; }}
.related-news {{ font-size: 12px; margin-top: 6px; padding-left: 12px; }}
.related-news .rn-label {{ color: #8c8c8c; }}
.news-list {{ list-style: none; }}
.news-list li {{ padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
.news-list li:last-child {{ border-bottom: none; }}
.news-list .news-time {{ font-size: 12px; color: #8c8c8c; margin-right: 8px; }}
.news-list .news-source {{ font-size: 12px; color: #bfbfbf; margin-left: 6px; }}
.disclaimer {{
    text-align: center; color: #bfbfbf; font-size: 12px; padding: 20px;
}}
.footer {{ text-align: center; padding: 20px; color: #bfbfbf; font-size: 12px; }}
.market-tag {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600; margin-right: 6px;
}}
.tag-a {{ background: #fff1f0; color: #cf1322; }}
.tag-hk {{ background: #e6f7ff; color: #096dd9; }}
.tag-us {{ background: #f6ffed; color: #389e0d; }}
@media (max-width: 600px) {{
    .container {{ padding: 10px; }}
    .header h1 {{ font-size: 20px; }}
    .overview-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>"""

    def _body_open(self) -> str:
        return '<body><div class="container">'

    def _body_close(self) -> str:
        today = date.today()
        return f"""<div class="footer">
        <p>Generated by stock_analyzer &middot; {today} &middot; Powered by DeepSeek AI</p>
        </div></div></body></html>"""

    def _header(self, title: str) -> str:
        return f"""<div class="header"><h1>{title}</h1>
        <div class="date">盘前智能分析 · 数据驱动决策</div></div>"""

    def _error_alert(self, errors: list[str]) -> str:
        items = "\n".join(f"<li>{e}</li>" for e in errors)
        return f"""<div class="alert"><strong>⚠️ 数据采集警告</strong><ul style="margin:8px 0 0 20px;">{items}</ul></div>"""

    def _market_overview(self, indexes: list[IndexQuote], quotes: list[StockQuote]) -> str:
        up_count = sum(1 for q in quotes if q.change_pct > 0)
        down_count = sum(1 for q in quotes if q.change_pct < 0)
        total = len(quotes)
        a_indexes = [i for i in indexes if i.market == "A"]
        up_text = "偏多" if up_count > down_count else "偏空" if down_count > up_count else "中性"

        return f"""<div class="overview-grid">
        <div class="overview-item"><div class="label">跟踪股票</div>
        <div class="value neutral">{total} 只</div></div>
        <div class="overview-item"><div class="label">上涨 / 下跌</div>
        <div class="value"><span class="up">{up_count}</span> / <span class="down">{down_count}</span></div></div>
        <div class="overview-item"><div class="label">市场情绪</div>
        <div class="value neutral">{up_text}</div></div>
        </div>"""

    def _index_section(self, indexes: list[IndexQuote]) -> str:
        rows = ""
        for market, label, tag in [("A", "A股市场", "tag-a"), ("HK", "港股市场", "tag-hk"), ("US", "美股市场", "tag-us")]:
            market_idx = [i for i in indexes if i.market == market]
            if not market_idx:
                continue
            for idx in market_idx:
                cls = "up" if idx.change_pct > 0 else "down" if idx.change_pct < 0 else "neutral"
                rows += (
                    f"<tr><td><span class='market-tag {tag}'>{label[:2]}</span>"
                    f"{idx.name}</td><td>{idx.latest:,.2f}</td>"
                    f"<td class='{cls}'>{idx.change_pct:+.2f}%</td>"
                    f"<td class='{cls}'>{idx.change_amount:+.2f}</td></tr>\n"
                )

        if not rows:
            return ""

        return f"""<div class="card"><h2>📊 大盘指数</h2>
        <table><thead><tr><th>指数</th><th>最新价</th><th>涨跌幅</th><th>涨跌额</th></tr></thead>
        <tbody>{rows}</tbody></table></div>"""

    def _watchlist_section(self, quotes: list[StockQuote],
                           analysis_map: dict[str, object],
                           analyses: Optional[list]) -> str:
        cards = ""
        for market, label in [("A", "A股"), ("HK", "港股"), ("US", "美股")]:
            market_quotes = [q for q in quotes if q.market == market]
            if not market_quotes:
                continue

            cards += f'<h3 style="margin:16px 0 8px;font-size:16px;">{label}</h3>'
            for q in market_quotes:
                # 颜色
                if market == "A":
                    color = "up" if q.change_pct > 0 else "down" if q.change_pct < 0 else "neutral"
                else:
                    color = "up" if q.change_pct > 0 else "down" if q.change_pct < 0 else "neutral"

                # AI 分析
                ai_html = ""
                if analyses is not None and StockAnalysis is not None:
                    matched = analysis_map.get(q.code)
                    if matched is None:
                        # 模糊匹配
                        for k, v in analysis_map.items():
                            if q.code.startswith(k) or k.startswith(q.code):
                                matched = v
                                break
                    if matched:
                        a = matched
                        ai_html = (
                            f'<div class="reasoning"><strong>🎯 {a.action}</strong> '
                            f'<span class="action-badge action-{a.action} conf-{a.confidence}">{a.confidence}置信度</span>'
                            f'<br>{a.reasoning}</div>'
                        )
                        if a.related_news:
                            rn_list = "".join(f"<li>{n}</li>" for n in a.related_news)
                            ai_html += f'<div class="related-news"><span class="rn-label">📰 相关新闻：</span><ul style="margin:4px 0 0 16px;">{rn_list}</ul></div>'
                    else:
                        ai_html = '<div class="reasoning" style="color:#bfbfbf;">无分析结果</div>'
                elif analyses is None:
                    ai_html = '<div class="reasoning" style="color:#faad14;">⚠️ AI分析暂时不可用（需配置 API Key）</div>'

                cards += f"""<div class="stock-card">
                <div class="stock-header">
                    <span><span class="stock-name">{q.name}</span><span class="stock-code">{q.code}</span></span>
                    <span style="font-size:18px;font-weight:700;" class="{color}">{q.price:.2f}</span>
                </div>
                <div class="stock-meta">
                    涨跌 <span class="{color}">{q.change_pct:+.2f}%</span>
                    &nbsp;|&nbsp; 成交额 {q.turnover:,.0f}
                    &nbsp;|&nbsp; 最高 {q.high:.2f} &nbsp;最低 {q.low:.2f}
                </div>
                {ai_html}
                </div>"""

        return f"""<div class="card"><h2>💼 自选股明细</h2>{cards}</div>"""

    def _news_section(self, news: list[NewsItem]) -> str:
        if not news:
            return ""
        items = ""
        for n in news:
            time_str = f'<span class="news-time">{n.time}</span>' if n.time else ""
            source_str = f'<span class="news-source">— {n.source}</span>' if n.source else ""
            items += f"<li>{time_str}{n.title}{source_str}</li>\n"

        return f"""<div class="card"><h2>📰 今日要闻</h2>
        <ul class="news-list">{items}</ul></div>"""

    def _screener_note(self) -> str:
        return """<div class="card"><h2>🔍 智能筛选</h2>
        <p style="color:#8c8c8c;font-size:14px;">全市场扫描功能暂不可用（数据源连接不稳定），当前仅分析自选股池。</p></div>"""

    def _disclaimer(self) -> str:
        return """<div class="disclaimer">
        ⚠️ <strong>免责声明</strong>：以上分析由 AI 生成，仅供参考，不构成投资建议。<br>
        投资有风险，入市需谨慎。请结合自身情况做出独立判断。
        </div>"""
