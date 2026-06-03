"""美股/港股数据获取 - 基于 yfinance"""

import time

import pandas as pd

from stock_analyzer.data.base import StockQuote
from stock_analyzer.utils.logger import get_logger
from stock_analyzer.utils.retry import retry

logger = get_logger("data.overseas")


@retry(max_attempts=2, base_delay=3.0)
def _download_batch(tickers: list[str], period: str = "5d") -> pd.DataFrame:
    """批量下载多个 ticker 的历史数据，避免逐个请求触发限流。"""
    import yfinance as yf

    tkr_str = " ".join(tickers)
    df = yf.download(tkr_str, period=period, group_by="ticker", progress=False, auto_adjust=True)
    if df is None or df.empty:
        logger.warning(f"批量下载为空: {tickers}")
        return pd.DataFrame()
    return df


def fetch_overseas_quotes(codes: list[str], market: str) -> list[StockQuote]:
    """获取美股/港股行情（批量下载，避免限流）。

    Args:
        codes: ticker 列表，如 ["AAPL", "TSLA"] 或 ["0700.HK", "9988.HK"]
        market: "US" 或 "HK"
    """
    if not codes:
        return []

    logger.info(f"获取{market}行情: {codes}")

    try:
        df = _download_batch(codes, period="5d")
    except Exception as e:
        logger.error(f"批量下载{market}行情失败: {e}")
        return []

    if df.empty:
        return []

    quotes = []
    for code in codes:
        try:
            # 处理单 ticker 和多 ticker 的不同列结构
            if len(codes) == 1:
                ticker_df = df
            else:
                ticker_df = df.xs(code, axis=1, level=0)

            if ticker_df.empty or "Close" not in ticker_df.columns:
                logger.warning(f"{code} 无有效数据")
                continue

            latest = ticker_df.iloc[-1]
            prev = ticker_df.iloc[-2] if len(ticker_df) > 1 else latest

            price = float(latest["Close"])
            prev_close = float(prev["Close"])
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

            quotes.append(StockQuote(
                code=code,
                name=code,
                price=round(price, 2),
                change_pct=round(change_pct, 2),
                volume=float(latest.get("Volume", 0) or 0),
                high=float(latest.get("High", 0) or 0),
                low=float(latest.get("Low", 0) or 0),
                open=float(latest.get("Open", 0) or 0),
                pre_close=prev_close,
                market=market,
            ))
        except Exception as e:
            logger.error(f"解析 {code} 数据失败: {e}")

    logger.info(f"{market}行情: 配置 {len(codes)} 只, 成功 {len(quotes)} 只")
    return quotes


@retry(max_attempts=2, base_delay=3.0)
def _fetch_index_single(code: str) -> dict | None:
    """获取单个海外指数行情。"""
    import yfinance as yf

    t = yf.Ticker(code)
    info = t.info or {}
    df = t.history(period="5d")
    if df.empty:
        return None

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    price = float(latest["Close"])
    prev_close = float(prev["Close"])
    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

    return {
        "code": code,
        "name": info.get("shortName", code),
        "latest": round(price, 2),
        "change_pct": round(change_pct, 2),
        "change_amount": round(price - prev_close, 2),
        "open": round(float(latest.get("Open", 0)), 2),
        "high": round(float(latest.get("High", 0)), 2),
        "low": round(float(latest.get("Low", 0)), 2),
        "pre_close": round(prev_close, 2),
    }


def fetch_overseas_index(codes: list[str]) -> list[dict]:
    """获取海外指数行情（逐个请求，带延迟避免限流）。

    Args:
        codes: yfinance 指数代码列表，如 ["^GSPC", "^IXIC", "^HSI"]

    Returns:
        [{"code": "^GSPC", "name": "标普500", "latest": ..., "change_pct": ...}, ...]
    """
    if not codes:
        return []

    results = []
    for i, code in enumerate(codes):
        # 请求间隔 1 秒，避免触发 yfinance 限流
        if i > 0:
            time.sleep(1.0)
        try:
            result = _fetch_index_single(code)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"获取指数 {code} 失败: {e}")

    logger.info(f"海外指数: 请求 {len(codes)} 个, 成功 {len(results)} 个")
    return results
