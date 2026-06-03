#!/usr/bin/env python
"""
stock_analyzer — 每日股票分析推送系统

用法:
    python main.py html          # 生成 HTML 报告并在浏览器中打开
    python main.py test          # 终端预览报告（不生成文件）
    python main.py status        # 显示配置摘要
    python main.py schedule      # 启动调度器（每个交易日 8:00 自动生成报告）
"""

import argparse
import sys
import time
import webbrowser
from datetime import date
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from stock_analyzer.config.settings import AppConfig, EnvConfig
from stock_analyzer.data.a_share import fetch_watchlist_quotes, fetch_stock_history
from stock_analyzer.data.overseas import fetch_overseas_quotes
from stock_analyzer.data.market_index import fetch_all_indexes
from stock_analyzer.data.news import fetch_financial_news
from stock_analyzer.analysis.analyzer import AIAnalyzer
from stock_analyzer.report.html_builder import HtmlReportBuilder
from stock_analyzer.utils.logger import setup_logging, get_logger
from stock_analyzer.utils.market_calendar import is_trading_day

logger = get_logger("main")

OUTPUT_DIR = PROJECT_ROOT / "_bmad-output"


def run_daily_report(config: AppConfig, env: EnvConfig, output_html: bool = True) -> str | None:
    """每日报告主流程：数据采集 → AI 分析 → HTML 报告生成。

    Args:
        config: 应用配置
        env: 环境变量（API Key 等）
        output_html: True 生成 HTML 文件，False 仅打印终端预览

    Returns:
        报告文本/HTML，如果被跳过则返回 None
    """
    errors: list[str] = []
    all_quotes: list = []
    all_indexes: list = []

    logger.info("=" * 50)
    logger.info("每日报告流程启动")
    logger.info("=" * 50)

    # ── Phase 1: 数据采集 ──
    logger.info("Phase 1/4: 数据采集")

    # A股自选股
    try:
        a_quotes = fetch_watchlist_quotes(config.watchlist.a_share)
        all_quotes.extend(a_quotes)
        logger.info(f"A股自选股: {len(a_quotes)}/{len(config.watchlist.a_share)} 只")
    except Exception as e:
        msg = f"A股自选股获取失败: {e}"
        logger.error(msg)
        errors.append(msg)

    # 港股
    if config.watchlist.hk:
        try:
            hk_quotes = fetch_overseas_quotes(config.watchlist.hk, "HK")
            all_quotes.extend(hk_quotes)
            logger.info(f"港股自选股: {len(hk_quotes)}/{len(config.watchlist.hk)} 只")
        except Exception as e:
            msg = f"港股自选股获取失败: {e}"
            logger.error(msg)
            errors.append(msg)

    # 美股
    if config.watchlist.us:
        try:
            us_quotes = fetch_overseas_quotes(config.watchlist.us, "US")
            all_quotes.extend(us_quotes)
            logger.info(f"美股自选股: {len(us_quotes)}/{len(config.watchlist.us)} 只")
        except Exception as e:
            msg = f"美股自选股获取失败: {e}"
            logger.error(msg)
            errors.append(msg)

    # 大盘指数
    try:
        all_indexes = fetch_all_indexes(
            config.indexes.a_share,
            config.indexes.hk,
            config.indexes.us,
        )
        logger.info(f"大盘指数: {len(all_indexes)} 个")
    except Exception as e:
        msg = f"大盘指数获取失败: {e}"
        logger.error(msg)
        errors.append(msg)

    # 新闻
    news: list = []
    try:
        news = fetch_financial_news(config.news.max_items)
        logger.info(f"财经新闻: {len(news)} 条")
    except Exception as e:
        msg = f"新闻获取失败: {e}"
        logger.error(msg)
        errors.append(msg)

    if not all_quotes and not all_indexes:
        logger.error("所有数据源均获取失败，终止本次运行")
        return None

    # ── Phase 2: AI 分析 ──
    logger.info("Phase 2/4: AI 分析")
    analyses = None

    if config.ai_analysis.enabled and env.deepseek_api_key:
        try:
            # 获取A股历史K线（供 AI 参考）
            histories = {}
            for q in all_quotes:
                if q.market == "A":
                    try:
                        df = fetch_stock_history(q.code, days=60)
                        if not df.empty:
                            histories[q.code] = df
                    except Exception:
                        pass

            analyzer = AIAnalyzer(config.ai_analysis, env.deepseek_api_key)
            analyses = analyzer.analyze(all_quotes, all_indexes, news, histories)
            logger.info(f"AI分析: {len(analyses)} 条建议")
        except Exception as e:
            logger.error(f"AI分析失败，降级为纯数据报告: {e}")
    else:
        if not env.deepseek_api_key:
            logger.warning("DEEPSEEK_API_KEY 未配置，跳过 AI 分析")
        else:
            logger.info("AI分析已禁用")

    # ── Phase 3: 报告生成 ──
    logger.info("Phase 3/4: 报告生成")
    builder = HtmlReportBuilder(project_name="stock_analyzer")
    html = builder.build(all_quotes, all_indexes, news, analyses, errors)
    logger.info(f"HTML报告生成完成: {len(html)} 字符")

    # ── Phase 4: 输出 ──
    logger.info("Phase 4/4: 输出")
    if output_html:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        html_path = OUTPUT_DIR / "report.html"
        html_path.write_text(html, encoding="utf-8")
        logger.info(f"HTML 报告已保存: {html_path}")
        print(f"[OK] HTML 报告已保存: {html_path}")
        print(f"     文件大小: {len(html)} 字符")
        return str(html_path)
    else:
        # 终端预览
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        # 提取纯文本预览
        from stock_analyzer.report.report_builder import ReportBuilder
        text_builder = ReportBuilder()
        text_report = text_builder.build(all_quotes, all_indexes, news, analyses, errors)
        print()
        print("=" * 60)
        print("  [PREVIEW] 报告预览")
        print("=" * 60)
        print()
        print(text_report)
        print()
        print("=" * 60)
        print("  使用 `python main.py html` 生成 HTML 报告并在浏览器打开。")
        print("=" * 60)
        return text_report

    logger.info("每日报告流程结束")


def show_status(config: AppConfig, env: EnvConfig) -> None:
    """显示配置摘要。"""
    print("=" * 50)
    print("  stock_analyzer 配置摘要")
    print("=" * 50)
    print()
    print(f"  自选股 A股: {len(config.watchlist.a_share)} 只 — {', '.join(config.watchlist.a_share)}")
    print(f"  自选股 港股: {len(config.watchlist.hk)} 只 — {', '.join(config.watchlist.hk)}")
    print(f"  自选股 美股: {len(config.watchlist.us)} 只 — {', '.join(config.watchlist.us)}")
    print(f"  大盘指数: {len(config.indexes.a_share) + len(config.indexes.hk) + len(config.indexes.us)} 个")
    print(f"  AI 模型: {config.ai_analysis.model} (DeepSeek)")
    print(f"  DeepSeek API Key: {'[已配置]' if env.deepseek_api_key else '[未配置]'}")
    print(f"  新闻: 最多 {config.news.max_items} 条")
    print()
    today = date.today()
    trading = is_trading_day(today)
    print(f"  今日 ({today}): {'[交易日]' if trading else '[非交易日]'}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="stock_analyzer — 每日股票分析推送系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py html         生成 HTML 报告并在浏览器中打开
  python main.py test         终端预览报告
  python main.py status       查看当前配置
  python main.py schedule     启动后台调度器（每个交易日 8:00 自动生成）
        """,
    )
    parser.add_argument(
        "command",
        choices=["html", "test", "status", "schedule"],
        help="html=生成HTML报告 | test=终端预览 | status=配置摘要 | schedule=定时调度",
    )
    args = parser.parse_args()

    # 初始化
    setup_logging()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    config = AppConfig.load()
    env = EnvConfig()

    if args.command == "status":
        show_status(config, env)
        return

    if args.command in ("html", "test"):
        output_html = args.command == "html"
        result = run_daily_report(config, env, output_html=output_html)

        if output_html and result:
            # 自动在浏览器中打开
            print(f"      正在打开浏览器...")
            webbrowser.open(f"file:///{result}")
        return

    if args.command == "schedule":
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        print("启动定时调度器...")
        print("   触发时间: 每个交易日 08:00")
        print("   输出格式: HTML 报告")
        print("   按 Ctrl+C 停止")
        print()

        scheduler = BackgroundScheduler()

        def scheduled_job():
            today = date.today()
            if not is_trading_day(today):
                logger.info(f"{today} 非交易日，跳过")
                print(f"[非交易日] {today}，跳过")
                return
            print(f"[交易日] {today}，开始生成报告...")
            try:
                result = run_daily_report(config, env, output_html=True)
                if result:
                    print(f"  报告已保存: {result}")
            except Exception as e:
                logger.error(f"定时任务执行异常: {e}")
                print(f"  执行失败: {e}")

        scheduler.add_job(
            scheduled_job,
            trigger=CronTrigger(hour=8, minute=0),
            id="daily_report",
            name="每日股市早报",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("调度器已启动")

        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n调度器已停止")
            scheduler.shutdown()
            logger.info("调度器已停止")


if __name__ == "__main__":
    main()
