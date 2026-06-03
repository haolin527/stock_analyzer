"""A 股数据获取 - 基于新浪财经 JS API"""

import re
import time
from typing import Optional

import requests

from stock_analyzer.data.base import StockQuote
from stock_analyzer.utils.logger import get_logger
from stock_analyzer.utils.retry import retry

logger = get_logger("data.a_share")

# 新浪行情 API 每次最多约 800 个代码
MAX_CODES_PER_REQUEST = 400

_SESSION: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://finance.sina.com.cn/",
        })
    return _SESSION


def _normalize_code(code: str) -> str:
    """将各种格式的代码转换为 6 位纯数字"""
    code = code.replace(".SZ", "").replace(".SH", "").replace(".sz", "").replace(".sh", "").strip()
    return code


def _to_sina_code(code: str) -> str:
    """转换为新浪代码格式: sh600519 或 sz000858"""
    code = _normalize_code(code)
    if code.startswith(("6", "5", "9")):
        return f"sh{code}"
    else:
        return f"sz{code}"


def _parse_sina_quote(line: str) -> Optional[StockQuote]:
    """解析新浪股票行情数据行"""
    # 格式: var hq_str_sh600519="name,open,prev_close,price,high,low,..."
    m = re.search(r'hq_str_(\w+)="(.+)"', line)
    if not m:
        return None

    sina_code = m.group(1)
    fields = m.group(2).split(",")
    if len(fields) < 9:
        return None

    code = sina_code[2:]  # 去掉 sh/sz 前缀
    market_prefix = sina_code[:2]

    # 判断市场后缀
    if market_prefix == "sh":
        full_code = f"{code}.SH"
    else:
        full_code = f"{code}.SZ"

    try:
        name = fields[0]
        open_price = float(fields[1]) if fields[1] else 0.0
        pre_close = float(fields[2]) if fields[2] else 0.0
        price = float(fields[3]) if fields[3] else 0.0
        high = float(fields[4]) if fields[4] else 0.0
        low = float(fields[5]) if fields[5] else 0.0
        volume = float(fields[8]) if len(fields) > 8 and fields[8] else 0.0
        turnover = float(fields[9]) if len(fields) > 9 and fields[9] else 0.0

        change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0.0
    except (ValueError, IndexError) as e:
        logger.debug(f"解析 {full_code} 数据失败: {e}")
        return None

    return StockQuote(
        code=full_code,
        name=name,
        price=round(price, 2),
        change_pct=round(change_pct, 2),
        change_amount=round(price - pre_close, 2),
        volume=volume,
        turnover=turnover,
        high=round(high, 2),
        low=round(low, 2),
        open=round(open_price, 2),
        pre_close=round(pre_close, 2),
        market="A",
    )


@retry(max_attempts=3, base_delay=3.0)
def _fetch_sina_batch(codes: list[str]) -> list[StockQuote]:
    """从新浪批量获取股票行情"""
    if not codes:
        return []

    url = "http://hq.sinajs.cn/list=" + ",".join(codes)
    session = _get_session()

    resp = session.get(url, timeout=30)
    resp.encoding = "gbk"

    quotes = []
    for line in resp.text.strip().split(";"):
        line = line.strip()
        if not line:
            continue
        q = _parse_sina_quote(line)
        if q:
            quotes.append(q)

    return quotes


def fetch_watchlist_quotes(codes: list[str]) -> list[StockQuote]:
    """获取自选股行情"""
    if not codes:
        return []

    sina_codes = [_to_sina_code(c) for c in codes]
    all_quotes: list[StockQuote] = []

    # 分批请求
    for i in range(0, len(sina_codes), MAX_CODES_PER_REQUEST):
        batch = sina_codes[i:i + MAX_CODES_PER_REQUEST]
        try:
            quotes = _fetch_sina_batch(batch)
            all_quotes.extend(quotes)
        except Exception as e:
            logger.error(f"获取 A 股行情批次 {i // MAX_CODES_PER_REQUEST + 1} 失败: {e}")

    logger.info(f"自选股 A 股: 配置 {len(codes)} 只, 获取 {len(all_quotes)} 只")
    return all_quotes


@retry(max_attempts=3, base_delay=3.0)
def fetch_a_share_index(index_code: str, index_name: str = "") -> Optional[dict]:
    """获取 A 股指数行情

    Args:
        index_code: 新浪格式 s_sh000001 或 sh000001
        index_name: 指数名称

    Returns:
        {"code": "...", "name": "...", "latest": ..., "change_pct": ..., ...}
    """
    if not index_code.startswith("s_"):
        sina_code = f"s_{index_code}"
    else:
        sina_code = index_code

    url = f"http://hq.sinajs.cn/list={sina_code}"
    session = _get_session()

    resp = session.get(url, timeout=15)
    resp.encoding = "gbk"

    m = re.search(r'hq_str_\w+="(.+)"', resp.text)
    if not m:
        logger.warning(f"指数 {index_code} 响应解析失败")
        return None

    fields = m.group(1).split(",")
    if len(fields) < 3:
        return None

    try:
        name = index_name or fields[0]
        latest = float(fields[1]) if fields[1] else 0.0
        change_amount = float(fields[2]) if fields[2] else 0.0
        change_pct = float(fields[3]) if len(fields) > 3 and fields[3] else 0.0
    except (ValueError, IndexError):
        return None

    return {
        "code": index_code,
        "name": name,
        "latest": round(latest, 2),
        "change_pct": round(change_pct, 2),
        "change_amount": round(change_amount, 2),
    }


@retry(max_attempts=2, base_delay=3.0)
def fetch_full_market_for_screening() -> list[dict]:
    """获取全市场股票列表用于智能筛选。

    使用新浪 A 股列表 API 分页获取所有股票代码，然后批量查询行情。
    由于全量查询很重，此函数应配合缓存使用。

    Returns:
        [{"code": "...", "name": "...", "price": ..., "change_pct": ..., "volume": ..., "turnover": ..., "volume_ratio": ...}]
    """
    logger.info("正在获取 A 股全市场数据用于筛选...")
    start = time.time()

    session = _get_session()

    # 第一步：获取所有 A 股代码
    all_codes: list[str] = []
    page = 1
    while True:
        api_url = (
            "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            "Market_Center.getHQNodeData"
            f"?page={page}&num=500&sort=symbol&asc=1&node=hs_a&symbol=&_s_r_a=auto"
        )
        try:
            resp = session.get(api_url, timeout=30)
            resp.encoding = "gbk"
            data = resp.json()
            if not data:
                break
            for item in data:
                all_codes.append(item["symbol"])
            if len(data) < 500:
                break
            page += 1
        except Exception as e:
            logger.warning(f"获取 A 股代码列表第 {page} 页失败: {e}")
            break

    if not all_codes:
        logger.error("未能获取 A 股代码列表")
        return []

    logger.info(f"获取到 {len(all_codes)} 个 A 股代码，开始批量查询行情...")

    # 第二步：批量查询行情（每批 MAX_CODES_PER_REQUEST 个）
    all_quotes: list[dict] = []
    for i in range(0, len(all_codes), MAX_CODES_PER_REQUEST):
        batch = all_codes[i:i + MAX_CODES_PER_REQUEST]
        sina_batch = [f"{c[:2].lower()}{c[2:]}" if c.startswith(("SH", "SZ")) else c
                      for c in batch]
        try:
            url = "http://hq.sinajs.cn/list=" + ",".join(sina_batch)
            resp = session.get(url, timeout=60)
            resp.encoding = "gbk"

            for line in resp.text.strip().split(";"):
                line = line.strip()
                if not line or "=" not in line:
                    continue
                q = _parse_sina_quote(line)
                if q and q.price > 0:
                    all_quotes.append({
                        "code": q.code,
                        "name": q.name,
                        "price": q.price,
                        "change_pct": q.change_pct,
                        "volume": q.volume,
                        "turnover": q.turnover,
                        "volume_ratio": q.volume_ratio,
                        "turnover_rate": q.turnover_rate,
                        "high": q.high,
                        "low": q.low,
                        "open": q.open,
                        "pre_close": q.pre_close,
                        "amplitude": q.amplitude,
                    })
        except Exception as e:
            logger.warning(f"批量查询行情失败 (offset={i}): {e}")

    elapsed = time.time() - start
    logger.info(f"全市场数据获取完成: {len(all_quotes)} 只有效股票, 耗时 {elapsed:.1f}s")
    return all_quotes


@retry(max_attempts=2, base_delay=3.0)
def fetch_stock_history(code: str, days: int = 60):
    """获取个股历史日 K 线数据

    使用腾讯财经 API（比新浪更可靠的历史数据）
    """
    import pandas as pd

    normalized = _normalize_code(code)
    if normalized.startswith(("6", "5", "9")):
        tencent_code = f"sh{normalized}"
    else:
        tencent_code = f"sz{normalized}"

    session = _get_session()
    url = (
        f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={tencent_code},day,,,{days + 10},qfq"
    )

    resp = session.get(url, timeout=15)
    data = resp.json()

    klines = None
    try:
        klines = data["data"][tencent_code]["qfqday"] or data["data"][tencent_code]["day"]
    except (KeyError, TypeError):
        logger.warning(f"{code} 历史数据解析失败")
        return pd.DataFrame()

    if not klines:
        return pd.DataFrame()

    rows = []
    for item in klines:
        rows.append({
            "date": item[0],
            "open": float(item[1]),
            "close": float(item[2]),
            "high": float(item[3]),
            "low": float(item[4]),
            "volume": float(item[5]),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").tail(days)
    return df
