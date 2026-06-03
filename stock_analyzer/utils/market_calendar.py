"""交易日判断 - 基于 akshare 交易日历"""

from datetime import date, datetime

from stock_analyzer.utils.logger import get_logger

logger = get_logger("utils.market_calendar")

_trade_dates_cache: set[str] | None = None
_cache_date: date | None = None


def _load_trade_calendar() -> set[str]:
    """从 akshare 加载 A 股交易日历"""
    global _trade_dates_cache, _cache_date
    today = date.today()

    if _trade_dates_cache is not None and _cache_date == today:
        return _trade_dates_cache

    try:
        import akshare as ak
        df = ak.tool_trade_date_hist_sina()
        _trade_dates_cache = set(df["trade_date"].astype(str).values)
        _cache_date = today
        logger.info(f"加载交易日历: {len(_trade_dates_cache)} 个交易日")
        return _trade_dates_cache
    except Exception as e:
        logger.warning(f"加载交易日历失败: {e}，假定今天是交易日")
        return set()


def is_trading_day(check_date: date | None = None) -> bool:
    """判断指定日期是否为 A 股交易日。默认判断今天。"""
    if check_date is None:
        check_date = date.today()

    date_str = check_date.strftime("%Y-%m-%d")

    # 周末直接返回 False
    if check_date.weekday() >= 5:
        return False

    trade_dates = _load_trade_calendar()
    if not trade_dates:
        # 如果加载失败，按周末判断
        return True

    return date_str in trade_dates
