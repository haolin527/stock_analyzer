"""钉钉机器人推送 — Webhook 消息发送"""

import requests

from stock_analyzer.config.settings import NotificationCfg
from stock_analyzer.notify.formatter import split_long_message
from stock_analyzer.utils.logger import get_logger
from stock_analyzer.utils.retry import retry

logger = get_logger("notify.dingtalk")


class DingTalkNotifier:
    """钉钉机器人消息推送器。

    通过 Webhook URL 发送 Markdown 格式消息到钉钉群。
    """

    def __init__(self, webhook_url: str, config: NotificationCfg):
        self.webhook_url = webhook_url
        self.config = config
        logger.info(f"钉钉推送器初始化: max_bytes={config.max_message_bytes}, "
                    f"split={config.split_long_message}")

    def send(self, content: str, title: str = "股市早报") -> bool:
        """发送消息主入口。

        如果启用了分段且内容超限，自动分段发送。

        Args:
            content: Markdown 格式的消息内容
            title: 消息标题

        Returns:
            True 表示发送成功，False 表示失败
        """
        if not self.webhook_url:
            logger.warning("钉钉 Webhook URL 未配置，跳过推送")
            return False

        content_bytes = len(content.encode("utf-8"))
        logger.info(f"准备推送: 标题='{title}', 大小={content_bytes} 字节")

        if self.config.split_long_message and content_bytes > self.config.max_message_bytes:
            logger.info(f"消息超过 {self.config.max_message_bytes} 字节，启动分段")
            return self._send_split(content, title)
        else:
            return self._send_single(content, title)

    @retry(max_attempts=2, base_delay=5.0)
    def _send_single(self, content: str, title: str) -> bool:
        """发送单条钉钉消息。

        Args:
            content: Markdown 消息内容
            title: 消息标题

        Returns:
            True 表示发送成功
        """
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
            },
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()

            errcode = result.get("errcode", -1)
            errmsg = result.get("errmsg", "unknown")

            if errcode == 0:
                logger.info("钉钉推送成功")
                return True
            else:
                logger.error(f"钉钉推送失败: errcode={errcode}, errmsg={errmsg}")
                return False

        except requests.exceptions.Timeout:
            logger.error("钉钉推送超时（15s）")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"钉钉推送网络错误: {e}")
            raise
        except Exception as e:
            logger.error(f"钉钉推送未知错误: {e}")
            return False

    def _send_split(self, content: str, title: str) -> bool:
        """分段发送消息。

        所有段都成功才返回 True。

        Args:
            content: 完整消息内容
            title: 消息标题

        Returns:
            全部分段成功则 True
        """
        segments = split_long_message(content, self.config.max_message_bytes)
        logger.info(f"消息分为 {len(segments)} 段")

        all_ok = True
        for i, seg in enumerate(segments, 1):
            seg_title = f"{title} ({i}/{len(segments)})"
            try:
                ok = self._send_single(seg, seg_title)
                if not ok:
                    all_ok = False
                    logger.error(f"分段 {i}/{len(segments)} 发送失败")
            except Exception:
                all_ok = False
                logger.error(f"分段 {i}/{len(segments)} 发送异常")

        return all_ok
