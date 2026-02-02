"""
AI-Scholar-Daily 配置管理模块

使用 pydantic-settings 管理环境变量配置
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # LLM API 配置
    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1", 
        alias="LLM_BASE_URL"
    )
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    
    # 推送渠道配置 (telegram/whatsapp/both)
    notify_channel: str = Field(default="telegram", alias="NOTIFY_CHANNEL")
    
    # Telegram 配置 (可选，当 notify_channel 包含 telegram 时必填)
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")
    
    # WhatsApp 配置 (可选，当 notify_channel 包含 whatsapp 时必填)
    whatsapp_api_token: Optional[str] = Field(default=None, alias="WHATSAPP_API_TOKEN")
    whatsapp_phone_number_id: Optional[str] = Field(default=None, alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_recipient: Optional[str] = Field(default=None, alias="WHATSAPP_RECIPIENT")
    
    # OpenClaw 配置 (可选，当 notify_channel=openclaw 时使用)
    openclaw_channel: str = Field(default="whatsapp", alias="OPENCLAW_CHANNEL")  # whatsapp/telegram
    openclaw_recipient: Optional[str] = Field(default=None, alias="OPENCLAW_RECIPIENT")  # 手机号或chat_id
    
    # Server酱 配置 (可选，当 notify_channel=serverchan 时使用)
    # 获取 SendKey: https://sct.ftqq.com/
    serverchan_sendkey: Optional[str] = Field(default=None, alias="SERVERCHAN_SENDKEY")
    
    # 论文获取配置
    max_papers: int = Field(default=10, alias="MAX_PAPERS")
    arxiv_categories: str = Field(
        default="cs.AI,cs.LG,cs.NI", 
        alias="ARXIV_CATEGORIES"
    )
    
    # 关键词配置
    core_keywords: str = Field(
        default="LLM,GPT,Claude,Gemini,大语言模型,多模态,AI Agent,Transformer",
        alias="CORE_KEYWORDS"
    )
    related_keywords: str = Field(
        default="RAG,LangChain,开源模型,Llama,Mistral,量化,微调,RLHF,Diffusion,Stable Diffusion",
        alias="RELATED_KEYWORDS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def arxiv_categories_list(self) -> List[str]:
        """获取 arXiv 分类列表"""
        return [cat.strip() for cat in self.arxiv_categories.split(",")]
    
    @property
    def core_keywords_list(self) -> List[str]:
        """获取核心关键词列表"""
        return [kw.strip() for kw in self.core_keywords.split(",")]
    
    @property
    def related_keywords_list(self) -> List[str]:
        """获取相关关键词列表"""
        return [kw.strip() for kw in self.related_keywords.split(",")]


# 全局配置实例
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()


# 研究方向描述（用于 LLM Prompt）
RESEARCH_CONTEXT = """
你是一个专业的 AI 前沿动态分析助手，关注以下领域：

1. **大语言模型 (LLM)**: GPT、Claude、Gemini、开源模型动态
2. **多模态 AI**: 视觉-语言模型、文生图/视频、音频处理
3. **AI Agent**: 自主智能体、工具调用、多Agent协作
4. **开源生态**: Hugging Face、LangChain、LlamaIndex 等
5. **模型优化**: 量化、蒸馏、剪枝、高效推理
6. **应用场景**: 代码生成、RAG、知识图谱、具身智能

请根据以上领域评估内容的重要性和创新性，关注：
- 突破性的新模型或架构
- 重要的开源发布
- 业界巨头的重大更新
- 有影响力的论文和研究
"""

