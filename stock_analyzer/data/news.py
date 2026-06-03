"""财经新闻聚合"""

from datetime import datetime, timedelta

from stock_analyzer.data.base import NewsItem
from stock_analyzer.utils.logger import get_logger
from stock_analyzer.utils.retry import retry

logger = get_logger("data.news")


@retry(max_attempts=2, base_delay=2.0)
def fetch_financial_news(max_items: int = 8) -> list[NewsItem]:
    """获取最新的财经新闻

    尝试多个数据源，优先返回可用源的新闻。
    """
    news_items: list[NewsItem] = []

    # 源1: akshare 的 stock_info_global_em (全球财经快讯)
    try:
        items = _fetch_akshare_global_news(max_items)
        if items:
            news_items.extend(items)
            logger.info(f"akshare 全球快讯: {len(items)} 条")
    except Exception as e:
        logger.warning(f"akshare 新闻源失败: {e}")

    # 源2: akshare 的 stock_news_em (东财新闻)
    if len(news_items) < max_items:
        try:
            items = _fetch_eastmoney_news(max_items)
            if items:
                news_items.extend(items)
                logger.info(f"东财新闻: {len(items)} 条")
        except Exception as e:
            logger.warning(f"东财新闻源失败: {e}")

    # 去重（按标题）
    seen = set()
    unique: list[NewsItem] = []
    for item in news_items:
        key = item.title[:40]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    logger.info(f"新闻聚合: 共 {len(unique)} 条（去重后）")
    return unique[:max_items]


def _fetch_akshare_global_news(max_items: int) -> list[NewsItem]:
    """从 akshare 获取全球财经快讯"""
    import akshare as ak

    df = ak.stock_info_global_em()
    if df.empty:
        return []

    items = []
    for _, row in df.head(max_items * 2).iterrows():
        title = str(row.iloc[0]) if len(row) > 0 else ""
        if not title or len(title) < 5:
            continue
        items.append(NewsItem(
            title=title,
            source="全球快讯",
            time=str(row.iloc[1]) if len(row) > 1 else "",
        ))
    return items[:max_items]


def _fetch_eastmoney_news(max_items: int) -> list[NewsItem]:
    """从东方财富获取财经新闻"""
    import akshare as ak

    df = ak.stock_news_em()
    if df.empty:
        return []

    items = []
    for _, row in df.head(max_items * 2).iterrows():
        title = str(row.get("标题", row.iloc[0] if len(row) > 0 else ""))
        if not title or len(title) < 5:
            continue
        items.append(NewsItem(
            title=title,
            source="东方财富",
            time=str(row.get("发布时间", "")),
            url=str(row.get("新闻链接", "")),
        ))
    return items[:max_items]
