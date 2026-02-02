"""
GitHub Trending AI 项目推送入口

每日自动获取 GitHub Trending 中的 AI 项目并推送
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
    logger.info(f"GitHub AI Trending 启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    try:
        # 1. 获取 Trending 项目
        logger.info("步骤 1/3: 获取 GitHub Trending...")
        from src.github_fetcher import fetch_ai_trending
        # max_results=10: 最多推送10个
        # min_results=5: 少于5个时尝试更大范围 (weekly/monthly)
        projects = fetch_ai_trending(max_results=10, min_results=5)
        
        if not projects:
            logger.warning("没有获取到 AI 相关项目 (即使尝试了 monthly)")
            from src.notifier import format_github_empty_digest, send_github_digest
            send_github_digest([])
            return
        
        logger.info(f"获取到 {len(projects)} 个 AI 项目")
        
        # 2. LLM 摘要
        logger.info("步骤 2/3: LLM 分析项目...")
        from src.github_summarizer import summarize_projects
        summaries = summarize_projects(projects)
        
        logger.info(f"生成 {len(summaries)} 个项目摘要")
        
        # 3. 推送
        logger.info("步骤 3/3: 发送推送...")
        from src.notifier import send_github_digest
        success = send_github_digest(summaries)
        
        if success:
            logger.info("✅ GitHub AI Trending 推送完成！")
        else:
            logger.error("❌ 推送失败")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"运行出错: {e}")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("GitHub AI Trending 运行结束")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
