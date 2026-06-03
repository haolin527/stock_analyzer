"""配置模型 - Pydantic 加载 YAML + .env"""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


# ── 环境变量 (.env) ──────────────────────────────────────────

class EnvConfig(BaseSettings):
    """从 .env 加载的密钥配置"""
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
    )
    deepseek_api_key: str = ""
    dingtalk_webhook_url: str = ""


# ── YAML 配置模型 ─────────────────────────────────────────────

class WatchlistCfg(BaseModel):
    a_share: list[str] = []
    hk: list[str] = []
    us: list[str] = []


class IndexItem(BaseModel):
    code: str
    name: str


class IndexesCfg(BaseModel):
    a_share: list[IndexItem] = []
    hk: list[IndexItem] = []
    us: list[IndexItem] = []


class VolumeSurgeCfg(BaseModel):
    enabled: bool = True
    multiplier: float = 1.5


class PriceSurgeCfg(BaseModel):
    enabled: bool = True
    min_change_pct: float = 3.0
    max_change_pct: float = 10.0


class HotTurnoverCfg(BaseModel):
    enabled: bool = True
    top_n: int = 20


class OversoldCfg(BaseModel):
    enabled: bool = True
    rsi_threshold: float = 30.0


class ScreenerCriteria(BaseModel):
    volume_surge: VolumeSurgeCfg = VolumeSurgeCfg()
    price_surge: PriceSurgeCfg = PriceSurgeCfg()
    hot_turnover: HotTurnoverCfg = HotTurnoverCfg()
    oversold: OversoldCfg = OversoldCfg()


class ScreenerCfg(BaseModel):
    enabled: bool = True
    top_n: int = 10
    criteria: ScreenerCriteria = ScreenerCriteria()


class AiAnalysisCfg(BaseModel):
    enabled: bool = True
    model: str = "deepseek-v4-pro"
    max_tokens: int = 4096
    temperature: float = 0.3


class NewsCfg(BaseModel):
    max_items: int = 8
    hours_back: int = 24


class NotificationCfg(BaseModel):
    on_non_trading_day: bool = False
    split_long_message: bool = True
    max_message_bytes: int = 18000


class AppConfig(BaseModel):
    watchlist: WatchlistCfg = WatchlistCfg()
    indexes: IndexesCfg = IndexesCfg()
    screener: ScreenerCfg = ScreenerCfg()
    ai_analysis: AiAnalysisCfg = AiAnalysisCfg()
    news: NewsCfg = NewsCfg()
    notification: NotificationCfg = NotificationCfg()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        if path is None:
            path = Path(__file__).resolve().parent / "config.yaml"
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls(**raw)
