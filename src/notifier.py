"""
AI-Scholar-Daily 多渠道推送模块

支持多种推送渠道:
- Telegram: 直接调用 Telegram Bot API
- WhatsApp: 调用 WhatsApp Business Cloud API (需要 Meta 开发者账号)
- OpenClaw: 通过 OpenClaw CLI 推送 (推荐，无需额外 API 配置)

架构说明:
    BaseNotifier (抽象基类)
        ├── TelegramNotifier  - Telegram 推送实现
        ├── WhatsAppNotifier  - WhatsApp API 推送实现
        └── OpenClawNotifier  - OpenClaw CLI 推送实现
"""

import logging
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import requests

from .config import get_settings
from .summarizer import PaperSummary

# 日志记录器，用于输出调试和错误信息
logger = logging.getLogger(__name__)


# ============================================================================
# 抽象基类
# ============================================================================

class BaseNotifier(ABC):
    """
    通知器抽象基类
    
    所有具体的通知器都必须继承此类并实现 send_message() 方法。
    提供了长消息自动分段发送的通用功能。
    
    Attributes:
        MAX_MESSAGE_LENGTH (int): 单条消息的最大字符数，超过此长度将自动分段
    """
    
    # 单条消息最大长度 (Telegram/WhatsApp 通用限制)
    MAX_MESSAGE_LENGTH = 4096
    
    @abstractmethod
    def send_message(self, text: str) -> bool:
        """
        发送单条消息 (抽象方法，子类必须实现)
        
        Args:
            text: 要发送的消息文本
            
        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        pass
    
    def send_long_message(self, text: str) -> bool:
        """
        发送长消息，自动分段处理
        
        如果消息长度超过 MAX_MESSAGE_LENGTH，会按分隔符 "---" 智能分割，
        确保每个片段不超过限制。
        
        Args:
            text: 要发送的消息文本（可能很长）
            
        Returns:
            bool: 所有片段都发送成功返回 True，任一失败返回 False
        """
        # 如果消息长度在限制内，直接发送
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return self.send_message(text)
        
        # 分割长消息
        chunks = self._split_message(text)
        success = True  # 跟踪整体发送状态
        
        # 逐个发送每个片段
        for i, chunk in enumerate(chunks):
            logger.info(f"发送消息片段 {i + 1}/{len(chunks)}")
            if not self.send_message(chunk):
                success = False  # 记录失败但继续发送其他片段
        
        return success
    
    def _split_message(self, text: str) -> List[str]:
        """
        智能分割长消息
        
        按 "---" 分隔符分割消息，确保每个片段不超过 MAX_MESSAGE_LENGTH。
        这样可以保持论文摘要的完整性，不会在中间截断。
        
        Args:
            text: 原始长消息文本
            
        Returns:
            List[str]: 分割后的消息片段列表
        """
        chunks = []           # 存储最终的消息片段
        current_chunk = ""    # 当前正在构建的片段
        
        # 按 "---" 分隔符分割（每篇论文之间有 "---"）
        sections = text.split("\n---\n")
        
        for section in sections:
            # 检查加入当前片段后是否超过限制 (+5 是为 "\n---\n" 预留空间)
            if len(current_chunk) + len(section) + 5 < self.MAX_MESSAGE_LENGTH:
                # 不超过限制，合并到当前片段
                current_chunk += section + "\n---\n"
            else:
                # 超过限制，保存当前片段，开始新片段
                if current_chunk:
                    chunks.append(current_chunk.rstrip("\n---\n"))
                current_chunk = section + "\n---\n"
        
        # 别忘了添加最后一个片段
        if current_chunk:
            chunks.append(current_chunk.rstrip("\n---\n"))
        
        return chunks


# ============================================================================
# Telegram 通知器
# ============================================================================

class TelegramNotifier(BaseNotifier):
    """
    Telegram Bot API 通知器
    
    通过 Telegram Bot API 直接发送消息。需要在 .env 中配置:
    - TELEGRAM_BOT_TOKEN: 机器人 Token (通过 @BotFather 获取)
    - TELEGRAM_CHAT_ID: 目标聊天 ID (通过 @userinfobot 获取)
    
    Attributes:
        TELEGRAM_API_URL (str): Telegram API 端点模板
        bot_token (str): Telegram Bot Token
        chat_id (str): 目标聊天 ID
        api_url (str): 完整的 API 请求 URL
    """
    
    # Telegram sendMessage API 端点
    TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
    MAX_MESSAGE_LENGTH = 4096  # Telegram 单条消息限制
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        初始化 Telegram 通知器
        
        Args:
            bot_token: Telegram Bot Token (格式: 123456:ABC-DEF...)
            chat_id: 目标聊天 ID (可以是用户ID或群组ID)
        """
        self.bot_token = bot_token      # 机器人令牌
        self.chat_id = chat_id          # 目标聊天ID
        # 构建完整的API URL
        self.api_url = self.TELEGRAM_API_URL.format(token=bot_token)
    
    def send_message(
        self, 
        text: str, 
        parse_mode: str = "Markdown",           # 消息格式：Markdown 或 HTML
        disable_web_page_preview: bool = True,  # 禁用链接预览，避免消息过长
    ) -> bool:
        """
        发送单条 Telegram 消息
        
        Args:
            text: 消息文本
            parse_mode: 解析模式 ("Markdown" 或 "HTML")
            disable_web_page_preview: 是否禁用网页预览
            
        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 发送 POST 请求到 Telegram API
            response = requests.post(
                self.api_url,
                json={
                    "chat_id": self.chat_id,                          # 目标聊天
                    "text": text,                                      # 消息内容
                    "parse_mode": parse_mode,                          # 格式化模式
                    "disable_web_page_preview": disable_web_page_preview,  # 禁用预览
                },
                timeout=30,  # 30秒超时
            )
            response.raise_for_status()  # 如果HTTP状态码不是2xx，抛出异常
            
            # 解析响应
            result = response.json()
            if result.get("ok"):
                logger.info("Telegram 消息发送成功")
                return True
            else:
                # API返回了错误
                logger.error(f"Telegram 发送失败: {result.get('description')}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Telegram 发送超时")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram 发送异常: {e}")
            return False


# ============================================================================
# WhatsApp 通知器
# ============================================================================

class WhatsAppNotifier(BaseNotifier):
    """
    WhatsApp Business Cloud API 通知器
    
    通过 Meta 的 WhatsApp Business Cloud API 发送消息。
    需要 Meta 开发者账号和已验证的业务号码。
    
    配置项 (.env):
    - WHATSAPP_API_TOKEN: Meta 开发者平台获取的 API Token
    - WHATSAPP_PHONE_NUMBER_ID: 发送消息的号码 ID
    - WHATSAPP_RECIPIENT: 接收消息的手机号 (国际格式，如 8613800138000)
    
    注意: 个人用户申请有限制，推荐使用 OpenClaw 方式替代。
    """
    
    # WhatsApp Cloud API 端点
    WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    MAX_MESSAGE_LENGTH = 4096  # WhatsApp 单条消息限制
    
    def __init__(self, api_token: str, phone_number_id: str, recipient: str):
        """
        初始化 WhatsApp 通知器
        
        Args:
            api_token: WhatsApp Business API Token
            phone_number_id: 发送号码的 ID (不是手机号本身)
            recipient: 接收者手机号 (国际格式，不带+号)
        """
        self.api_token = api_token              # API 访问令牌
        self.phone_number_id = phone_number_id  # 发送号码 ID
        self.recipient = recipient              # 接收者号码
        # 构建 API URL
        self.api_url = self.WHATSAPP_API_URL.format(phone_number_id=phone_number_id)
    
    def send_message(self, text: str) -> bool:
        """
        发送单条 WhatsApp 消息
        
        Args:
            text: 消息文本
            
        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 设置请求头，包含认证信息
            headers = {
                "Authorization": f"Bearer {self.api_token}",  # Bearer Token 认证
                "Content-Type": "application/json",
            }
            
            # 构建请求体
            payload = {
                "messaging_product": "whatsapp",      # 固定值
                "to": self.recipient,                 # 接收者号码
                "type": "text",                       # 消息类型：文本
                "text": {"body": text}                # 消息内容
            }
            
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            
            # 检查响应
            result = response.json()
            if result.get("messages"):
                # 成功时会返回 messages 数组
                logger.info("WhatsApp 消息发送成功")
                return True
            else:
                logger.error(f"WhatsApp 发送失败: {result}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("WhatsApp 发送超时")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"WhatsApp 发送异常: {e}")
            return False


# ============================================================================
# OpenClaw 通知器 (推荐)
# ============================================================================

class OpenClawNotifier(BaseNotifier):
    """
    OpenClaw CLI 通知器 (推荐使用)
    
    通过调用本地安装的 OpenClaw CLI 发送消息。
    无需单独配置 WhatsApp Business API，OpenClaw 会处理所有连接细节。
    
    工作原理:
        1. 调用 subprocess 执行 `openclaw message send` 命令
        2. OpenClaw CLI 将消息发送到本地运行的 Gateway
        3. Gateway 通过已配置的渠道 (WhatsApp/Telegram) 发送消息
    
    前提条件:
        - 已安装 OpenClaw: npm install -g openclaw
        - OpenClaw Gateway 正在运行: openclaw gateway --verbose
        - 已配置并连接目标渠道 (首次需要 openclaw onboard)
    
    配置项 (.env):
    - OPENCLAW_CHANNEL: 目标渠道 ("whatsapp" 或 "telegram")
    - OPENCLAW_RECIPIENT: 接收者 (可选，手机号或chat_id)
    """
    
    MAX_MESSAGE_LENGTH = 4096
    
    def __init__(self, channel: str = "whatsapp", recipient: Optional[str] = None):
        """
        初始化 OpenClaw 通知器
        
        Args:
            channel: 目标渠道，可选 "whatsapp" 或 "telegram"
            recipient: 接收者标识 (WhatsApp 手机号或 Telegram chat_id)
                       如果不指定，将发送到默认会话
        """
        self.channel = channel      # 目标渠道
        self.recipient = recipient  # 接收者标识 (可选)
    
    def send_message(self, text: str) -> bool:
        """
        通过 OpenClaw CLI 发送消息
        
        调用 `openclaw message send` 命令，该命令会:
        1. 连接到本地 Gateway (ws://127.0.0.1:18789)
        2. 通过指定渠道发送消息
        
        Args:
            text: 消息文本
            
        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 构建命令参数
            cmd = [
                "openclaw", "message", "send",   # OpenClaw 发送消息命令
                "--channel", self.channel,        # 目标渠道
                "--message", text,                # 消息内容
            ]
            
            # 如果指定了接收者，添加 --to 参数
            if self.recipient:
                cmd.extend(["--to", self.recipient])
            
            logger.info(f"调用 OpenClaw 发送到 {self.channel}...")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,  # 捕获 stdout 和 stderr
                text=True,            # 输出为文本而非字节
                timeout=60,           # 60秒超时
                shell=True,           # Windows 需要 shell=True
            )
            
            # 检查返回码
            if result.returncode == 0:
                logger.info(f"OpenClaw ({self.channel}) 消息发送成功")
                return True
            else:
                # 命令执行失败，输出错误信息
                logger.error(f"OpenClaw 发送失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("OpenClaw 发送超时")
            return False
        except FileNotFoundError:
            # openclaw 命令未找到 (未安装或未在 PATH 中)
            logger.error("OpenClaw CLI 未找到，请确保已安装 openclaw")
            return False
        except Exception as e:
            logger.error(f"OpenClaw 发送异常: {e}")
            return False


# ============================================================================
# Server酱 通知器 (微信推送)
# ============================================================================

class ServerChanNotifier(BaseNotifier):
    """
    Server酱 (ServerChan) 通知器 - 微信推送
    
    通过 Server酱 将消息推送到微信。非常简单，只需一个 SendKey。
    
    获取方式:
        1. 访问 https://sct.ftqq.com/
        2. 使用微信扫码登录
        3. 获取 SendKey
    
    配置项 (.env):
    - SERVERCHAN_SENDKEY: Server酱的 SendKey
    
    限制:
        - 免费版每天 5 条消息
        - 付费版无限制
    
    消息格式:
        - title: 消息标题 (必填，最多 256 字符)
        - desp: 消息内容 (选填，支持 Markdown，最多 64KB)
    """
    
    # Server酱 API 端点
    SERVERCHAN_API_URL = "https://sctapi.ftqq.com/{sendkey}.send"
    MAX_MESSAGE_LENGTH = 64000  # 64KB 限制
    
    def __init__(self, sendkey: str):
        """
        初始化 Server酱 通知器
        
        Args:
            sendkey: Server酱的 SendKey (在 sct.ftqq.com 获取)
        """
        self.sendkey = sendkey  # Server酱 SendKey
        self.api_url = self.SERVERCHAN_API_URL.format(sendkey=sendkey)
    
    def send_message(self, text: str, title: str = "AI-Scholar-Daily 论文推送") -> bool:
        """
        发送 Server酱 消息到微信
        
        Args:
            text: 消息内容 (支持 Markdown)
            title: 消息标题
            
        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 构建请求数据
            data = {
                "title": title,    # 消息标题
                "desp": text,      # 消息内容 (Markdown)
            }
            
            logger.info("发送 Server酱 消息到微信...")
            
            # 发送 POST 请求
            response = requests.post(
                self.api_url,
                data=data,
                timeout=30,
            )
            response.raise_for_status()
            
            # 检查响应
            result = response.json()
            if result.get("code") == 0:
                logger.info("Server酱 消息发送成功")
                return True
            else:
                # 常见错误码:
                # 10001: 发送失败
                # 10002: 配额不足
                logger.error(f"Server酱 发送失败: {result.get('message')}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Server酱 发送超时")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Server酱 发送异常: {e}")
            return False


# ============================================================================
# 消息格式化函数
# ============================================================================

def format_daily_digest(
    summaries: List[PaperSummary], 
    for_whatsapp: bool = False,
    overview: str = None,
) -> str:
    """
    格式化每日论文摘要消息
    
    将论文摘要列表转换为格式化的消息文本。
    Telegram 使用 Markdown 格式（支持粗体、链接等），
    WhatsApp/OpenClaw 使用纯文本格式（更好的兼容性）。
    
    Args:
        summaries: 论文摘要列表 (PaperSummary 对象)
        for_whatsapp: 是否为 WhatsApp 格式 (True=纯文本, False=Markdown)
        overview: 可选的每日总结文本
        
    Returns:
        str: 格式化后的消息文本
    """
    # 获取当前日期
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 构建消息头部
    lines = [
        # Telegram 用 *加粗*，WhatsApp 用纯文本
        f"📚 *AI 前沿日报* | {today}" if not for_whatsapp else f"📚 AI 前沿日报 | {today}",
        "",  # 空行
    ]
    
    # 添加每日总结 (如果有)
    if overview:
        lines.extend([
            "🧠 【今日总结】" if for_whatsapp else "🧠 *【今日总结】*",
            overview,
            "",
            "---",
            "",
        ])
    
    lines.extend([
        f"📄 今日精选 {len(summaries)} 篇论文：",
        "",
        "---",  # 分隔线
        "",
    ])
    
    # 遍历每篇论文
    for i, summary in enumerate(summaries, 1):  # 从1开始编号
        if for_whatsapp:
            # WhatsApp/OpenClaw 使用纯文本格式 (不支持 Markdown)
            paper_block = [
                f"{i}. {summary.title}",                           # 序号和标题
                f"🔗 {summary.url}",                               # 论文链接
                f"👤 作者: {', '.join(summary.authors[:3])}",      # 前3位作者
                f"⭐ 相关度: {summary.relevance_score}/10",        # 相关度评分
                f"💡 核心贡献: {summary.core_contribution}",       # LLM生成的核心贡献
                f"🔗 边缘智能启发: {summary.edge_insight}",        # LLM生成的研究启发
                "",
                "---",  # 论文之间的分隔线
                "",
            ]
        else:
            # Telegram 使用 Markdown 格式 (需要转义特殊字符)
            title = _escape_markdown(summary.title)
            authors = _escape_markdown(", ".join(summary.authors[:3]))
            core = _escape_markdown(summary.core_contribution)
            insight = _escape_markdown(summary.edge_insight)
            
            paper_block = [
                f"*{i}. [{title}]({summary.url})*",    # Markdown 链接 + 加粗
                f"👤 作者: {authors}",
                f"⭐ 相关度: {summary.relevance_score}/10",
                f"💡 核心贡献: {core}",
                f"🔗 边缘智能启发: {insight}",
                "",
                "---",
                "",
            ]
        lines.extend(paper_block)
    
    # 添加结尾
    lines.append("📖 祝你阅读愉快！")
    
    # 合并为单个字符串
    return "\n".join(lines)


def format_empty_digest(for_whatsapp: bool = False) -> str:
    """
    格式化空摘要消息 (当天没有相关论文时使用)
    
    Args:
        for_whatsapp: 是否为 WhatsApp 格式
        
    Returns:
        str: 格式化后的消息文本
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    if for_whatsapp:
        # WhatsApp 纯文本格式
        return f"""📚 AI-Scholar-Daily | {today}

今日暂无高相关度的新论文。

明天再见！ 🌟
"""
    else:
        # Telegram Markdown 格式
        return f"""📚 *AI-Scholar-Daily* | {today}

今日暂无高相关度的新论文。

明天再见！ 🌟
"""


def _escape_markdown(text: str) -> str:
    """
    转义 Telegram Markdown 特殊字符
    
    Telegram 的 Markdown 解析器需要转义某些特殊字符，
    否则会导致格式错误或消息发送失败。
    
    Args:
        text: 原始文本
        
    Returns:
        str: 转义后的文本
    """
    # Telegram Markdown V2 需要转义的字符
    special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    
    # 在每个特殊字符前添加反斜杠
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    
    return text


# ============================================================================
# GitHub 项目推送格式
# ============================================================================

def format_github_digest(
    summaries: list, 
    for_whatsapp: bool = False,
    overview: str = None,
) -> str:
    """
    格式化 GitHub 项目推送消息
    
    Args:
        summaries: ProjectSummary 列表
        for_whatsapp: 是否为纯文本格式
        overview: 可选的每日总结
        
    Returns:
        格式化的消息
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    lines = [
        f"🔥 *GitHub AI Trending* | {today}" if not for_whatsapp else f"🔥 GitHub AI Trending | {today}",
        "",
    ]
    
    # 添加每日总结 (如果有)
    if overview:
        lines.extend([
            "🧠 【今日总结】" if for_whatsapp else "🧠 *【今日总结】*",
            overview,
            "",
            "---",
            "",
        ])
    
    lines.extend([
        f"🔧 今日精选 {len(summaries)} 个热门 AI 项目：",
        "",
        "---",
        "",
    ])
    
    for i, s in enumerate(summaries, 1):
        if for_whatsapp:
            block = [
                f"{i}. {s.name}",
                f"🔗 {s.url}",
                f"⭐ {s.stars} (+{s.stars_today} today) | 推荐度: {s.score}/10",
                f"📝 {s.summary}",
                f"💡 亮点: {s.highlights}",
                f"🎯 场景: {s.use_cases}",
                "",
                "---",
                "",
            ]
        else:
            name = _escape_markdown(s.name)
            summary = _escape_markdown(s.summary)
            highlights = _escape_markdown(s.highlights)
            use_cases = _escape_markdown(s.use_cases)
            
            block = [
                f"*{i}. [{name}]({s.url})*",
                f"⭐ {s.stars} (+{s.stars_today} today) | 推荐度: {s.score}/10",
                f"📝 {summary}",
                f"💡 亮点: {highlights}",
                f"🎯 场景: {use_cases}",
                "",
                "---",
                "",
            ]
        lines.extend(block)
    
    lines.append("🚀 Happy Coding!")
    return "\n".join(lines)


def format_github_empty_digest(for_whatsapp: bool = False) -> str:
    """格式化空推送 (无 AI 项目时)"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if for_whatsapp:
        return f"""🔥 GitHub AI Trending | {today}

今日暂无特别突出的 AI 项目。

明天再见！ 🚀
"""
    else:
        return f"""🔥 *GitHub AI Trending* | {today}

今日暂无特别突出的 AI 项目。

明天再见！ 🚀
"""


def send_github_digest(summaries: list) -> bool:
    """
    发送 GitHub 项目推送
    
    Args:
        summaries: ProjectSummary 列表
        
    Returns:
        是否成功
    """
    settings = get_settings()
    channel = settings.notify_channel.lower()
    
    # 生成每日总结
    overview = None
    if summaries:
        try:
            from .summarizer import generate_daily_overview
            logger.info("生成 GitHub 项目总结...")
            overview = generate_daily_overview(project_summaries=summaries)
        except Exception as e:
            logger.warning(f"总结生成失败，跳过: {e}")

    # 格式化消息
    for_whatsapp = channel in ("serverchan", "whatsapp", "openclaw")
    if summaries:
        message = format_github_digest(summaries, for_whatsapp=for_whatsapp, overview=overview)
    else:
        message = format_github_empty_digest(for_whatsapp=for_whatsapp)
    
    # 使用与论文推送相同的渠道逻辑
    if channel == "serverchan":
        if not settings.serverchan_sendkey:
            logger.error("Server酱配置缺失")
            return False
        notifier = ServerChanNotifier(sendkey=settings.serverchan_sendkey)
        return notifier.send_long_message(message)
    
    elif channel == "telegram":
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            logger.error("Telegram 配置缺失")
            return False
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )
        return notifier.send_long_message(message)
    
    elif channel == "openclaw":
        openclaw_channel = getattr(settings, 'openclaw_channel', 'whatsapp')
        openclaw_recipient = getattr(settings, 'openclaw_recipient', None)
        notifier = OpenClawNotifier(channel=openclaw_channel, recipient=openclaw_recipient)
        return notifier.send_long_message(message)
    
    else:
        logger.error(f"不支持的推送渠道: {channel}")
        return False


# ============================================================================
# 主发送函数 (入口点)
# ============================================================================

def send_daily_digest(summaries: List[PaperSummary]) -> bool:
    """
    发送每日摘要的主函数 (推送模块的入口点)
    
    根据环境变量 NOTIFY_CHANNEL 的配置选择推送渠道:
    - "telegram": 直接调用 Telegram Bot API
    - "whatsapp": 调用 WhatsApp Business Cloud API (需要 Meta 开发者账号)
    - "openclaw": 通过 OpenClaw CLI 推送 (推荐，无需额外 API 配置)
    - "both": 同时推送到 Telegram 和 WhatsApp
    
    Args:
        summaries: 论文摘要列表 (从 summarizer 模块获取)
        
    Returns:
        bool: 推送成功返回 True，失败返回 False
    """
    # 从配置中获取推送渠道设置
    settings = get_settings()
    channel = settings.notify_channel.lower()  # 转小写，忽略大小写
    
    success = True  # 跟踪整体推送状态
    
    # 生成每日总结
    overview = None
    if summaries:
        try:
            from .summarizer import generate_daily_overview
            logger.info("生成每日总结...")
            overview = generate_daily_overview(paper_summaries=summaries)
        except Exception as e:
            logger.warning(f"每日总结生成失败，跳过: {e}")
    
    # ========== OpenClaw 推送 (推荐方式) ==========
    if channel == "openclaw":
        # 获取 OpenClaw 特定配置
        openclaw_channel = getattr(settings, 'openclaw_channel', 'whatsapp')  # 默认 whatsapp
        openclaw_recipient = getattr(settings, 'openclaw_recipient', None)     # 可选的接收者
        
        # 创建 OpenClaw 通知器
        notifier = OpenClawNotifier(
            channel=openclaw_channel,
            recipient=openclaw_recipient,
        )
        
        # 格式化消息 (使用纯文本格式)
        message = format_daily_digest(summaries, for_whatsapp=True, overview=overview) if summaries else format_empty_digest(for_whatsapp=True)
        
        # 发送消息
        if not notifier.send_long_message(message):
            logger.error("OpenClaw 推送失败")
            return False
        else:
            logger.info("✅ OpenClaw 推送成功")
            return True
    
    # ========== Server酱 推送 (微信) ==========
    if channel == "serverchan":
        # 检查必需的配置
        if not settings.serverchan_sendkey:
            logger.error("Server酱 配置缺失 (SERVERCHAN_SENDKEY)")
            return False
        
        # 创建 Server酱 通知器
        notifier = ServerChanNotifier(sendkey=settings.serverchan_sendkey)
        
        # 格式化消息 (Server酱 支持 Markdown)
        message = format_daily_digest(summaries, overview=overview) if summaries else format_empty_digest()
        
        # 发送消息
        if not notifier.send_long_message(message):
            logger.error("Server酱 推送失败")
            return False
        else:
            logger.info("✅ Server酱 推送成功 (微信)")
            return True
    
    # ========== Telegram 推送 ==========
    if channel in ("telegram", "both"):
        # 检查必需的配置是否存在
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            logger.error("Telegram 配置缺失，跳过 Telegram 推送")
            if channel == "telegram":
                return False  # 如果只配置了 Telegram 但缺少配置，返回失败
        else:
            # 创建 Telegram 通知器
            notifier = TelegramNotifier(
                bot_token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
            )
            
            # 格式化消息 (使用 Markdown 格式)
            message = format_daily_digest(summaries, overview=overview) if summaries else format_empty_digest()
            
            # 发送消息
            if not notifier.send_long_message(message):
                logger.error("Telegram 推送失败")
                success = False
            else:
                logger.info("✅ Telegram 推送成功")
    
    # ========== WhatsApp 推送 ==========
    if channel in ("whatsapp", "both"):
        # 检查必需的配置是否存在
        if not settings.whatsapp_api_token or not settings.whatsapp_phone_number_id or not settings.whatsapp_recipient:
            logger.error("WhatsApp 配置缺失，跳过 WhatsApp 推送")
            if channel == "whatsapp":
                return False  # 如果只配置了 WhatsApp 但缺少配置，返回失败
        else:
            # 创建 WhatsApp 通知器
            notifier = WhatsAppNotifier(
                api_token=settings.whatsapp_api_token,
                phone_number_id=settings.whatsapp_phone_number_id,
                recipient=settings.whatsapp_recipient,
            )
            
            # 格式化消息 (使用纯文本格式)
            message = format_daily_digest(summaries, for_whatsapp=True, overview=overview) if summaries else format_empty_digest(for_whatsapp=True)
            
            # 发送消息
            if not notifier.send_long_message(message):
                logger.error("WhatsApp 推送失败")
                success = False
            else:
                logger.info("✅ WhatsApp 推送成功")
    
    return success
