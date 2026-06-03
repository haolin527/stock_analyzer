"""磁盘缓存 - JSON + TTL"""

import json
import time
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


class DiskCache:
    """基于文件的简单 TTL 缓存"""

    def __init__(self, default_ttl: int = 300):
        self._default_ttl = default_ttl

    def _key_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return CACHE_DIR / f"{safe}.json"

    def get(self, key: str) -> Optional[dict]:
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("_ts", 0) > data.get("_ttl", self._default_ttl):
                path.unlink(missing_ok=True)
                return None
            return data.get("value")
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        path = self._key_path(key)
        data = {
            "_ts": time.time(),
            "_ttl": ttl if ttl is not None else self._default_ttl,
            "value": value,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)

    def clear(self) -> None:
        for f in CACHE_DIR.glob("*.json"):
            f.unlink(missing_ok=True)
