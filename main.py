"""
AI-Scholar-Daily 主入口

每日自动获取 AI 论文、LLM 摘要并推送到 Telegram
"""

import logging
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info(f"AI-Scholar-Daily 启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    try:
        # 1. 获取论文
        logger.info("步骤 1/3: 获取论文...")
        from src.fetcher import fetch_papers
        papers = fetch_papers(days=2)  # 获取最近2天的论文，确保不遗漏
        
        if not papers:
            logger.warning("没有获取到任何相关论文")
            # 仍然发送空摘要通知
            from src.notifier import send_daily_digest
            send_daily_digest([])
            return
        
        logger.info(f"获取到 {len(papers)} 篇候选论文")
        
        # 2. LLM 摘要
        logger.info("步骤 2/3: LLM 分析摘要...")
        from src.summarizer import summarize_papers
        summaries = summarize_papers(papers)
        
        logger.info(f"生成 {len(summaries)} 篇论文摘要")
        
        # 3. Telegram 推送
        logger.info("步骤 3/3: 发送 Telegram 通知...")
        from src.notifier import send_daily_digest
        success = send_daily_digest(summaries)
        
        if success:
            logger.info("✅ 每日推送完成！")
        else:
            logger.error("❌ 推送失败，请检查 Telegram 配置")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"运行出错: {e}")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("AI-Scholar-Daily 运行结束")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
