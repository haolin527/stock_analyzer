"""大盘指数数据获取"""

from stock_analyzer.data.base import IndexQuote
from stock_analyzer.data.a_share import fetch_a_share_index
from stock_analyzer.data.overseas import fetch_overseas_index
from stock_analyzer.utils.logger import get_logger

logger = get_logger("data.market_index")


def fetch_all_indexes(a_share_list: list, hk_list: list, us_list: list) -> list[IndexQuote]:
    """获取所有配置的指数数据

    Returns:
        统一的 IndexQuote 列表
    """
    all_indexes: list[IndexQuote] = []

    # A 股指数 (新浪 API)
    for item in a_share_list:
        try:
            code = item.code if hasattr(item, 'code') else item.get("code", "")
            name = item.name if hasattr(item, 'name') else item.get("name", code)
            result = fetch_a_share_index(code, name)
            if result:
                all_indexes.append(IndexQuote(
                    code=result["code"],
                    name=result["name"],
                    latest=result["latest"],
                    change_pct=result["change_pct"],
                    change_amount=result["change_amount"],
                    market="A",
                ))
        except Exception as e:
            logger.error(f"A 股指数 {name} 获取失败: {e}")

    logger.info(f"A 股指数: {len(all_indexes)} 个")

    # 海外指数 (yfinance)
    hk_codes = [item.code if hasattr(item, 'code') else item.get("code", "")
                for item in hk_list]
    hk_names = {}
    for item in hk_list:
        c = item.code if hasattr(item, 'code') else item.get("code", "")
        n = item.name if hasattr(item, 'name') else item.get("name", c)
        hk_names[c] = n

    us_codes = [item.code if hasattr(item, 'code') else item.get("code", "")
                for item in us_list]
    us_names = {}
    for item in us_list:
        c = item.code if hasattr(item, 'code') else item.get("code", "")
        n = item.name if hasattr(item, 'name') else item.get("name", c)
        us_names[c] = n

    all_overseas = hk_codes + us_codes
    if all_overseas:
        try:
            overseas = fetch_overseas_index(all_overseas)
            for item in overseas:
                market = "HK" if item["code"] in hk_codes else "US"
                name = hk_names.get(item["code"]) or us_names.get(item["code"]) or item["name"]
                all_indexes.append(IndexQuote(
                    code=item["code"],
                    name=name,
                    latest=item["latest"],
                    change_pct=item["change_pct"],
                    change_amount=item["change_amount"],
                    open=item.get("open", 0),
                    high=item.get("high", 0),
                    low=item.get("low", 0),
                    pre_close=item.get("pre_close", 0),
                    market=market,
                ))
        except Exception as e:
            logger.error(f"海外指数获取失败: {e}")

    logger.info(f"全部指数: 共 {len(all_indexes)} 个")
    return all_indexes
