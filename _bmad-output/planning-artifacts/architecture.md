# 🏗️ 技术架构设计文档：stock_analyzer

> **架构师**：Winston（BMad 系统架构师）
> **日期**：2026-06-02
> **版本**：v1.0
> **原则**：偏好无聊的技术，开发者生产力是架构的一部分，每个决策锚定业务价值

---

## 一、架构概览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     调度层 (Scheduler)                       │
│  Windows Task Scheduler / APScheduler → 每日 08:00 触发      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   编排层 (Orchestrator)                       │
│  main.py: 串联数据→分析→报告→推送 四阶段流水线               │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│   数据层 (Data)  │ │ 分析层 (AI) │ │  推送层 (Notify) │
│  ✅ 已建成       │ │ 🔴 待建      │ │ 🔴 待建          │
│                 │ │              │ │                  │
│ a_share.py     │ │ analyzer.py │ │ dingtalk.py     │
│ overseas.py    │ │ prompts.py  │ │ formatter.py    │
│ news.py        │ │              │ │                  │
│ market_index   │ │              │ │                  │
└─────────────────┘ └─────────────┘ └─────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   报告层 (Report)                             │
│  report_builder.py: 组装数据+分析结果 → Markdown 报告         │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 增建文件清单

```
stock_analyzer/
├── analysis/
│   ├── analyzer.py      # [新] AI分析主逻辑
│   └── prompts.py       # [新] Prompt模板管理
├── notify/
│   ├── dingtalk.py      # [新] 钉钉Webhook发送
│   └── formatter.py     # [新] 消息格式化+分段
├── report/
│   └── report_builder.py # [新] 报告组装引擎
├── main.py               # [新] 入口+编排+调度
├── requirements.txt      # [改] 补全依赖
└── .env                  # [用户创建] API Key等密钥
```

---

## 二、技术选型决策

### 决策 1：调度器

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| **APScheduler** | Python原生，跨平台，灵活 | 需要进程常驻，额外内存 | ✅ **推荐** |
| cron (Linux) | 简单可靠 | Windows不可用 | ❌ 不跨平台 |
| Windows Task Scheduler | 系统级，零内存 | 仅Windows，配置繁琐 | ✅ **备选** |
| 自带 while+sleep | 零依赖 | 不精确，易挂 | ❌ 太脆弱 |

**决策**: **APScheduler** 作为主方案，**Windows Task Scheduler** 作为备选。APScheduler 使用 `CronTrigger(hour=8, minute=0)`，配合 `BackgroundScheduler` 在后台进程常驻。

> **权衡**：APScheduler 需要进程常驻（约30MB内存），但换来的是精确的调度、Python生态集成、跨平台能力。对于个人使用的分析工具，30MB内存完全可接受。

### 决策 2：CLI 框架

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| **argparse** | 标准库，零依赖 | API冗长 | ✅ **推荐** |
| click | 装饰器风格，优雅 | 额外依赖 | 可用但不必要 |
| typer | 类型提示驱动，现代 | 额外依赖 | 过度设计 |

**决策**: **argparse**。项目只有几个简单命令（`run`、`test`、`status`），argparse 足够，零额外依赖。

### 决策 3：报告模板

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| f-string 拼接 | 简单直接 | 复杂嵌套时难维护 | ❌ 不适合结构化报告 |
| Jinja2 | 功能强大，模板继承 | 额外依赖 | ❌ 对Markdown报告过度 |
| **Python 字符串模板** | 标准库，无依赖 | 功能有限 | ✅ **推荐** |
| Markdown 逐段构建 | 灵活，易于调试 | 需自己组织结构 | ✅ **推荐** |

**决策**: **逐段构建 Markdown**（通过 `list[str]` 累积段落，最后 `join`）。报告是固定结构（摘要→大盘→自选股→新闻→建议），不需要模板引擎的复杂度。每个段由对应函数生成，测试方便。

### 决策 4：数据库

**决策**: **不需要数据库**。理由：
1. 数据是实时获取的，不需要持久化历史行情
2. 配置已存在于 YAML 文件中
3. 日志通过文件记录
4. 如果未来需要历史回溯（P2-2），可以追加 SQLite

> **当前方案**：纯文件系统。配置（YAML）→ 数据（API实时获取）→ 缓存（JSON TTL）→ 报告（Markdown）→ 日志（文本文件）。

### 决策 5：HTTP 服务

**决策**: **不需要 HTTP 服务**。这是一个纯 CLI 脚本，由调度器触发执行后退出。不需要 Web 界面，不需要 API 端点。

---

## 三、模块设计

### 3.1 `analysis/analyzer.py` — AI 分析引擎

**职责**：调用 Claude API，输入行情+新闻+K线，输出结构化分析结果

**接口设计**：
```python
@dataclass
class StockAnalysis:
    code: str
    name: str
    action: str           # "买入" | "持有" | "卖出" | "观望"
    confidence: str       # "高" | "中" | "低"
    reasoning: str        # AI给出的理由
    related_news: list[str]  # 关联新闻标题

class AIAnalyzer:
    def __init__(self, config: AiAnalysisCfg, api_key: str):
        ...

    def analyze(
        self,
        quotes: list[StockQuote],
        indexes: list[IndexQuote],
        news: list[NewsItem],
        histories: dict[str, pd.DataFrame]  # code -> K线DataFrame
    ) -> list[StockAnalysis]:
        """核心分析方法"""
        ...

    def _build_prompt(self, ...) -> str:
        """构建发送给Claude的prompt"""
        ...

    def _parse_response(self, text: str) -> list[StockAnalysis]:
        """解析Claude的结构化回复"""
        ...
```

**Prompt 设计原则**：
- System prompt: 角色设定（专业股票分析师），输出格式约束（JSON），免责声明要求
- User prompt: 行情数据（表格）+ 新闻摘要（列表）+ 大盘指数 + 历史K线概要
- 要求 Claude 输出结构化 JSON，便于解析

**错误处理**：
- API 超时：30秒超时，重试1次
- 返回非JSON：降级为纯文本解析
- 完全失败：返回空列表，触发报告层的降级逻辑（纯数据报告）

### 3.2 `notify/dingtalk.py` — 钉钉推送

**职责**：将 Markdown 报告通过钉钉 Webhook 发送

**接口设计**：
```python
class DingTalkNotifier:
    def __init__(self, webhook_url: str, config: NotificationCfg):
        ...

    def send(self, content: str, title: str = "股市早报") -> bool:
        """发送消息，超过限制自动分段"""
        ...

    def _send_single(self, content: str, title: str) -> bool:
        """发送单条消息"""
        ...

    def _split_content(self, content: str) -> list[str]:
        """按板块边界分段（优先在##标题处分割）"""
        ...
```

**分段策略**（`split_long_message` 启用时）：
1. 按 `## ` 标题分割为 sections
2. 贪心累积：当前段 + 下一 section < 18000字节 → 合并
3. 超过则新起一段
4. 每段添加 `(1/3)` `(2/3)` 序号

### 3.3 `report/report_builder.py` — 报告生成

**职责**：将数据层和分析层的结果组装为 Markdown 报告

**接口设计**：
```python
class ReportBuilder:
    def build(
        self,
        quotes: list[StockQuote],
        indexes: list[IndexQuote],
        news: list[NewsItem],
        analyses: list[StockAnalysis] | None,  # None = AI不可用
    ) -> str:
        """构建完整报告"""
        sections = [
            self._build_header(),
            self._build_summary(quotes, indexes),
            self._build_index_section(indexes),
            self._build_watchlist_section(quotes, analyses),
            self._build_news_section(news),
            self._build_disclaimer(),
        ]
        return "\n\n".join(sections)
```

**报告结构**：
```markdown
# 📈 股市早报 | 2026-06-03 (周二)

## 📊 大盘风向
[12个指数表格]

## 💼 自选股明细
### A股
[8只股票，含AI建议]
### 港股
[3只股票]
### 美股
[4只股票]

## 📰 今日要闻
[8条新闻，关联股票标注]

---
⚠️ 免责声明：以上分析由AI生成，仅供参考，不构成投资建议。
```

### 3.4 `main.py` — 入口与编排

**职责**：串联全流程，设置调度器

```python
# main.py 结构
def run_daily_report():
    """每日报告主流程"""
    # Phase 1: 数据采集
    quotes = collect_all_quotes(config)
    indexes = collect_all_indexes(config)
    news = collect_news(config)

    # Phase 2: AI 分析
    try:
        analyses = analyzer.analyze(quotes, indexes, news, histories)
    except Exception:
        analyses = None  # 降级

    # Phase 3: 报告生成
    report = report_builder.build(quotes, indexes, news, analyses)

    # Phase 4: 推送
    notifier.send(report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "test", "status"])
    # run: 立即执行一次
    # test: 执行但不推送（dry-run）
    # status: 显示配置摘要和上次执行状态
    ...

if __name__ == "__main__":
    main()
```

---

## 四、数据流

### 完整时序（08:00 触发后的逐秒推演）

```
08:00:00  调度器触发 main.py run
08:00:01  ├─ 检查交易日 → 是交易日，继续
08:00:01  ├─ 并行启动数据采集：
08:00:01  │  ├─ fetch_watchlist_quotes(A股8只) → 新浪API
08:00:01  │  ├─ fetch_overseas_quotes(港股3只)  → yfinance
08:00:01  │  ├─ fetch_overseas_quotes(美股4只)  → yfinance
08:00:01  │  ├─ fetch_all_indexes(12个)         → 新浪+yfinance
08:00:01  │  └─ fetch_financial_news(8条)       → akshare
08:00:15  ├─ 数据采集完成（~15秒）
08:00:16  ├─ 构建 Prompt（嵌入行情数据+新闻+指数）
08:00:17  ├─ 调用 Claude API
08:00:45  ├─ AI分析完成（~30秒）
08:00:46  ├─ 组装报告（Markdown拼接）
08:00:47  ├─ 发送钉钉消息
08:00:48  └─ 日志记录 → 退出 ✅
```

**设计要点**：
- 数据采集阶段：5个数据源**可并行**调用（ThreadPoolExecutor），互不依赖
- AI分析阶段：串行（依赖数据采集结果），是耗时最长环节
- 错误隔离：单个数据源失败不阻塞其他源

---

## 五、错误处理策略

### 分级处理体系

| 级别 | 场景 | 处理 | 用户体验 |
|------|------|------|---------|
| **L0** | 某个数据源部分失败（如新浪2只超时，6只成功） | 继续，报告中标注缺失 | 正常推送，缺失股票标注"N/A" |
| **L1** | 某个数据源完全失败（如yfinance全部超时） | 跳过该市场，报告标注 | 推送不完整报告，缺失市场标注"数据获取失败" |
| **L2** | Claude API 超时/失败 | 降级为纯数据报告 | 推送无AI建议的报告，标注"AI分析暂时不可用" |
| **L3** | 钉钉推送失败 | 重试1次，日志告警 | 用户感知不到（重试成功）/ 该日无推送（重试失败） |
| **L4** | 所有数据源失败 | 终止，日志记录 | 今日无推送 |

### 关键降级路径

```
正常路径:  数据 → AI分析 → 报告 → 推送
降级路径:  数据 → ──✗── → 纯数据报告 → 推送  (AI不可用)
最低路径:  ──✗── → 不推送，仅日志              (数据不可用)
```

---

## 六、部署方案

### 方案：Windows Task Scheduler + Python

Windows 环境下最务实的部署方式：

**步骤**：
1. 创建 `.env` 文件（CLAUDE_API_KEY + DINGTALK_WEBHOOK_URL）
2. `pip install -r requirements.txt`
3. 手动运行一次验证：`python main.py test`
4. 配置 Windows 定时任务：
   ```
   触发器: 每日 08:00
   操作: 启动程序 → pythonw.exe
   参数: C:\Users\Administrator\Documents\bmad-test\main.py run
   起始于: C:\Users\Administrator\Documents\bmad-test
   条件: 唤醒计算机运行此任务 ✅
   ```

**备选**：如果后续需要更灵活的调度，可迁移到 APScheduler 后台进程 + NSSM 注册为 Windows 服务。

### 部署清单

- [ ] Python 3.10+ 环境
- [ ] `.env` 文件配置（CLAUDE_API_KEY, DINGTALK_WEBHOOK_URL）
- [ ] `pip install -r requirements.txt`
- [ ] 手动执行 `python main.py test` 验证
- [ ] Windows Task Scheduler 配置
- [ ] 第一个交易日人工确认推送

---

## 七、现有代码改进建议

### 直接复用（无需修改）

| 文件 | 理由 |
|------|------|
| `config/settings.py` | 设计完善，开箱即用 |
| `config/config.yaml` | 配置完整 |
| `data/base.py` | 数据模型结构良好 |
| `utils/retry.py` | 通用重试装饰器 |
| `utils/cache.py` | 磁盘TTL缓存 |
| `utils/logger.py` | 日志系统 |
| `utils/market_calendar.py` | 交易日判断 |
| `data/a_share.py` | 自选股部分（fetch_watchlist_quotes, fetch_stock_history） |
| `data/overseas.py` | 海外行情（需改进名称映射） |
| `data/market_index.py` | 指数聚合 |
| `data/news.py` | 新闻聚合 |

### 需要修改

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `data/a_share.py` | 全市场扫描 `fetch_full_market_for_screening()` 改为可选，失败时降级 | P0 |
| `data/overseas.py` | 增加中文名称映射，`name` 字段不应直接填 code | P1 |
| `requirements.txt` | 补全：pydantic, pydantic-settings, pyyaml, requests, pandas, anthropic, schedule | P0 |

### 已识别的 BUG

| 位置 | 问题 | 修复 |
|------|------|------|
| `a_share.py` 全市场扫描 | 3次重试全部"Remote end closed connection without response" | 降级处理，失败时不阻塞主流程 |
| `market_index.py` | `hasattr()` 和 `.get()` 混合使用，pydantic model 和 dict 不一致 | 统一转换为 dict 访问 |

---

## 八、依赖清单（完整 requirements.txt）

```
# 数据获取
akshare>=1.14.0
yfinance>=0.2.40
requests>=2.31.0

# 配置
pydantic>=2.0.0
pydantic-settings>=2.0.0
pyyaml>=6.0

# AI 分析
anthropic>=0.39.0

# 调度
apscheduler>=3.10.0

# 数据处理
pandas>=2.0.0

# 钉钉推送（requests 已包含，无需额外依赖）
```

---

> **架构师结语**：
> 这个架构刻意保持简单。三个新增模块（analyzer/notify/report）每个约100-200行代码，main.py约100行。数据层完全复用。总新增代码量约600-800行。技术栈选择遵循「无聊的技术」原则——argparse而非typer，逐段构建Markdown而非Jinja2，文件系统而非数据库，APScheduler而非Kubernetes CronJob。权衡的核心始终是：**这个决策对个人项目的长期维护成本影响多大？**——答案通常是：保持简单。
