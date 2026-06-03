"""数据模型基类"""

from dataclasses import dataclass, field


@dataclass
class StockQuote:
    """统一股票行情数据结构"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float = 0.0           # 成交量（手/股）
    turnover: float = 0.0         # 成交额（元）
    volume_ratio: float = 0.0     # 量比
    turnover_rate: float = 0.0    # 换手率
    amplitude: float = 0.0        # 振幅
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    pre_close: float = 0.0
    market: str = "A"             # A / HK / US
    change_amount: float = 0.0    # 涨跌额


@dataclass
class IndexQuote:
    """统一指数行情数据结构"""
    code: str
    name: str
    latest: float
    change_pct: float
    change_amount: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: float = 0.0
    market: str = "A"


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    source: str = ""
    time: str = ""
    url: str = ""
    summary: str = ""
