"""
AI-Scholar-Daily Telegram 推送模块

负责将摘要结果以 Markdown 格式发送到 Telegram
"""

import logging
from datetime import datetime
from typing import List, Optional

import requests

from .config import get_settings
from .summarizer import PaperSummary

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 通知器"""
    
    TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
    MAX_MESSAGE_LENGTH = 4096  # Telegram 单条消息最大长度
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = self.TELEGRAM_API_URL.format(token=bot_token)
    
    def send_message(
        self, 
        text: str, 
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True,
    ) -> bool:
        """
        发送单条消息
        
        Args:
            text: 消息文本
            parse_mode: 解析模式 (Markdown/HTML)
            disable_web_page_preview: 是否禁用链接预览
            
        Returns:
            是否发送成功
        """
        try:
            response = requests.post(
                self.api_url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                },
                timeout=30,
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.info("消息发送成功")
                return True
            else:
                logger.error(f"消息发送失败: {result.get('description')}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("消息发送超时")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"消息发送异常: {e}")
            return False
    
    def send_long_message(self, text: str) -> bool:
        """
        发送长消息（自动分段）
        
        Args:
            text: 消息文本
            
        Returns:
            是否全部发送成功
        """
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return self.send_message(text)
        
        # 按段落分割
        chunks = self._split_message(text)
        success = True
        
        for i, chunk in enumerate(chunks):
            logger.info(f"发送消息片段 {i + 1}/{len(chunks)}")
            if not self.send_message(chunk):
                success = False
        
        return success
    
    def _split_message(self, text: str) -> List[str]:
        """
        智能分割长消息
        
        Args:
            text: 消息文本
            
        Returns:
            分割后的消息列表
        """
        chunks = []
        current_chunk = ""
        
        # 按 "---" 分隔符分割
        sections = text.split("\n---\n")
        
        for section in sections:
            # 如果当前片段加上新段落不超过限制，则合并
            if len(current_chunk) + len(section) + 5 < self.MAX_MESSAGE_LENGTH:
                current_chunk += section + "\n---\n"
            else:
                # 保存当前片段，开始新片段
                if current_chunk:
                    chunks.append(current_chunk.rstrip("\n---\n"))
                current_chunk = section + "\n---\n"
        
        # 添加最后一个片段
        if current_chunk:
            chunks.append(current_chunk.rstrip("\n---\n"))
        
        return chunks


def format_daily_digest(summaries: List[PaperSummary]) -> str:
    """
    格式化每日摘要消息
    
    Args:
        summaries: 论文摘要列表
        
    Returns:
        格式化后的 Markdown 消息
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    lines = [
        f"📚 *AI-Scholar-Daily* | {today}",
        "",
        f"今日为您精选 {len(summaries)} 篇高相关论文：",
        "",
        "---",
        "",
    ]
    
    for i, summary in enumerate(summaries, 1):
        # 转义 Markdown 特殊字符
        title = _escape_markdown(summary.title)
        authors = _escape_markdown(", ".join(summary.authors[:3]))
        core = _escape_markdown(summary.core_contribution)
        insight = _escape_markdown(summary.edge_insight)
        
        paper_block = [
            f"*{i}. [{title}]({summary.url})*",
            f"👤 作者: {authors}",
            f"⭐ 相关度: {summary.relevance_score}/10",
            f"💡 核心贡献: {core}",
            f"🔗 边缘智能启发: {insight}",
            "",
            "---",
            "",
        ]
        lines.extend(paper_block)
    
    lines.append("📖 祝你阅读愉快！")
    
    return "\n".join(lines)


def format_empty_digest() -> str:
    """
    格式化空摘要消息（无相关论文时）
    
    Returns:
        格式化后的消息
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    return f"""📚 *AI-Scholar-Daily* | {today}

今日暂无高相关度的新论文。

明天再见！ 🌟
"""


def _escape_markdown(text: str) -> str:
    """
    转义 Markdown 特殊字符
    
    Args:
        text: 原始文本
        
    Returns:
        转义后的文本
    """
    # Telegram Markdown 需要转义的字符
    special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    
    return text


def send_daily_digest(summaries: List[PaperSummary]) -> bool:
    """
    发送每日摘要的主函数
    
    Args:
        summaries: 论文摘要列表
        
    Returns:
        是否发送成功
    """
    settings = get_settings()
    
    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    
    if summaries:
        message = format_daily_digest(summaries)
    else:
        message = format_empty_digest()
    
    return notifier.send_long_message(message)
