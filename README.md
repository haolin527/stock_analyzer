# 📈 stock_analyzer — AI 驱动的每日股票分析推送

每天早上 8:00，一份由 **DeepSeek AI** 生成的股票分析报告自动出现在你面前 — 覆盖 A 股、港股、美股，结合技术面 + 消息面，给出每只持仓股的操作建议。

## ✨ 功能

- 🌍 **三市场覆盖** — A 股（新浪 API）+ 港股 + 美股（yfinance）
- 🤖 **AI 深度分析** — DeepSeek V4 Pro 对每只股票给出买入/持有/卖出/观望建议 + 置信度 + 理由
- 📊 **大盘风向** — 12 个核心指数（上证、沪深300、恒生、标普500、纳斯达克等）
- 📰 **新闻聚合** — 全球快讯 + 东财新闻，AI 自动关联到相关持仓股
- 🎨 **精美 HTML 报告** — 响应式设计，手机/电脑都能看
- ⏰ **定时调度** — 每个交易日 8:00 自动运行
- 📱 **钉钉推送**（可选）— 消息直达手机

## 📸 报告预览

HTML 报告包含以下板块：

```
┌─────────────────────────────────────┐
│        📈 股市早报 | 2026-06-03      │
│         盘前智能分析 · 数据驱动决策    │
├─────────────────────────────────────┤
│  [跟踪 15 只] [上涨 10 / 下跌 5]     │  ← 市场概览卡片
├─────────────────────────────────────┤
│  📊 大盘指数                         │
│  ┌──────────┬────────┬────────┐     │
│  │ 上证指数  │ 4075.10│ +0.43% │     │
│  │ 沪深300   │ 4914.56│ +1.45% │     │
│  │ 恒生指数  │   ...  │  ...   │     │
│  └──────────┴────────┴────────┘     │
├─────────────────────────────────────┤
│  💼 自选股明细                       │
│  ┌─────────────────────────────┐    │
│  │ 宁德时代  433.89  🔴 +3.28% │    │
│  │ 🎯 持有 (高置信度)           │    │
│  │ 技术面放量突破，消息面利好...  │    │
│  │ 📰 新能源板块政策利好         │    │
│  ├─────────────────────────────┤    │
│  │ 五粮液     82.71  🟢 -0.84% │    │
│  │ ...                        │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  📰 今日要闻（8 条）                 │
├─────────────────────────────────────┤
│  ⚠️ 免责声明：AI 生成，仅供参考      │
└─────────────────────────────────────┘
```

## 🏗️ 架构

```
stock_analyzer/
├── analysis/              # AI 分析引擎
│   ├── prompts.py         #   Prompt 模板
│   └── analyzer.py        #   DeepSeek API 调用
├── data/                  # 数据采集层
│   ├── a_share.py         #   A 股行情（新浪 API）
│   ├── overseas.py        #   港股/美股（yfinance）
│   ├── market_index.py    #   大盘指数聚合
│   └── news.py            #   财经新闻聚合
├── report/                # 报告生成
│   ├── html_builder.py    #   HTML 报告（精美样式）
│   └── report_builder.py  #   Markdown 报告
├── notify/                # 消息推送（可选）
│   ├── dingtalk.py        #   钉钉 Webhook
│   └── formatter.py       #   消息分段
├── config/                # 配置管理（Pydantic + YAML）
├── utils/                 # 工具库（重试/缓存/日志/交易日历）
└── main.py                # 入口 + 调度编排
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/haolin527/stock_analyzer.git
cd stock_analyzer
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
```

```
DEEPSEEK_API_KEY=sk-你的Key
```

> 获取 Key: [DeepSeek API 控制台](https://platform.deepseek.com/api_keys)

### 4. （可选）自定义自选股

编辑 `stock_analyzer/config/config.yaml`：

```yaml
watchlist:
  a_share:
    - "000858"    # 五粮液
    - "600519"    # 贵州茅台
    # ... 添加你的自选股
```

### 5. 🎉 生成第一份报告

```bash
python main.py html
```

HTML 报告自动保存到 `_bmad-output/report.html` 并在浏览器打开。

## 📋 命令说明

```bash
python main.py html        # 生成 HTML 报告 + 浏览器打开（推荐）
python main.py test        # 终端文本预览
python main.py status      # 查看当前配置
python main.py schedule    # 启动定时调度（每日 8:00 自动运行）
```

## ⚙️ 技术栈

| 层级 | 技术 |
|------|------|
| AI 引擎 | DeepSeek V4 Pro（OpenAI 兼容 API） |
| 数据源 | 新浪 JS API · yfinance · akshare · 腾讯财经 |
| 配置管理 | Pydantic v2 + YAML + .env |
| 调度 | APScheduler（BackgroundScheduler） |
| 报告 | 自包含 HTML（响应式 CSS，零外部依赖） |
| 消息推送 | 钉钉机器人 Webhook（可选） |

## 📝 开发流程

本项目使用 [BMad Method](https://docs.bmad-method.org/) 工作流驱动开发：

- 📊 **[需求分析](_bmad-output/planning-artifacts/requirements-analysis.md)** — 利益相关者、竞品对标、风险清单
- 📋 **[产品需求 PRD](_bmad-output/planning-artifacts/prd.md)** — JTBD、用户故事、验收标准
- 🏗️ **[技术架构](_bmad-output/planning-artifacts/architecture.md)** — 分层设计、技术选型、数据流

## ⚠️ 免责声明

本工具仅供学习参考，AI 生成的所有分析均不构成投资建议。投资有风险，入市需谨慎。

## 📄 License

MIT
