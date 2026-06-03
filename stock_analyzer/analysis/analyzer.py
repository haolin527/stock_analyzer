"""AI 分析引擎 — DeepSeek API (OpenAI 兼容) 生成股票操作建议"""

import json
import re
from dataclasses import dataclass, field

import pandas as pd
from openai import OpenAI

from stock_analyzer.config.settings import AiAnalysisCfg
from stock_analyzer.data.base import StockQuote, IndexQuote, NewsItem
from stock_analyzer.analysis.prompts import SYSTEM_PROMPT, build_user_prompt
from stock_analyzer.utils.logger import get_logger

logger = get_logger("analysis.analyzer")

# DeepSeek API 地址
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


@dataclass
class StockAnalysis:
    """单只股票的 AI 分析结果"""

    code: str
    name: str
    action: str = "观望"  # 买入 / 持有 / 卖出 / 观望
    confidence: str = "低"  # 高 / 中 / 低
    reasoning: str = ""
    related_news: list[str] = field(default_factory=list)


class AIAnalyzer:
    """AI 股票分析器，通过 DeepSeek API (OpenAI 兼容) 生成操作建议。"""

    def __init__(self, config: AiAnalysisCfg, api_key: str):
        self.config = config
        self.client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        logger.info(
            f"AI分析器初始化: provider=DeepSeek, model={config.model}, "
            f"max_tokens={config.max_tokens}, temperature={config.temperature}"
        )

    def analyze(
        self,
        quotes: list[StockQuote],
        indexes: list[IndexQuote],
        news: list[NewsItem],
        histories: dict[str, pd.DataFrame] | None = None,
    ) -> list[StockAnalysis]:
        """核心分析方法：构建 prompt → 调用 DeepSeek API → 解析响应。

        API 失败时返回空列表，让调用方降级为纯数据报告。
        """
        if not self.config.enabled:
            logger.info("AI分析已禁用")
            return []

        if not quotes:
            logger.warning("无行情数据，跳过AI分析")
            return []

        prompt = build_user_prompt(quotes, indexes, news, histories)
        logger.info(f"开始AI分析: {len(quotes)} 只股票, prompt {len(prompt)} 字符")

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=60,
            )
            text = response.choices[0].message.content or ""
            logger.info(f"DeepSeek API 调用成功, 响应长度 {len(text)} 字符")
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return []

        results = self._parse_response(text)
        logger.info(f"AI分析完成: 成功解析 {len(results)} 条建议")
        return results

    def _parse_response(self, text: str) -> list[StockAnalysis]:
        """解析 DeepSeek 的 JSON 响应。"""
        # 尝试提取 JSON 块
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
            if bracket_match:
                json_str = bracket_match.group(0)
            else:
                json_str = text.strip()

        try:
            raw_list = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            logger.debug(f"原始响应前200字符: {text[:200]}")
            return []

        if not isinstance(raw_list, list):
            logger.error(f"期望 JSON 数组，实际类型: {type(raw_list)}")
            return []

        valid_actions = {"买入", "持有", "卖出", "观望"}
        valid_confidences = {"高", "中", "低"}

        results: list[StockAnalysis] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue

            action = str(item.get("action", "观望"))
            if action not in valid_actions:
                action = "观望"

            confidence = str(item.get("confidence", "低"))
            if confidence not in valid_confidences:
                confidence = "低"

            related = item.get("related_news", [])
            if not isinstance(related, list):
                related = []

            results.append(StockAnalysis(
                code=str(item.get("code", "")),
                name=str(item.get("name", "")),
                action=action,
                confidence=confidence,
                reasoning=str(item.get("reasoning", "")),
                related_news=[str(n) for n in related],
            ))

        return results
