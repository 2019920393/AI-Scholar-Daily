"""
AI-Scholar-Daily 配置管理模块

使用 pydantic-settings 管理环境变量配置
"""

import os
from typing import List
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
    
    # Telegram 配置
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(..., alias="TELEGRAM_CHAT_ID")
    
    # 论文获取配置
    max_papers: int = Field(default=10, alias="MAX_PAPERS")
    arxiv_categories: str = Field(
        default="cs.AI,cs.LG,cs.NI", 
        alias="ARXIV_CATEGORIES"
    )
    
    # 关键词配置
    core_keywords: str = Field(
        default="Edge Intelligence,Transformer,Network Optimization,边缘智能",
        alias="CORE_KEYWORDS"
    )
    related_keywords: str = Field(
        default="Federated Learning,IoT,Mobile Computing,Attention Mechanism,Neural Network Pruning,Model Compression",
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
你是一个专业的 AI 论文分析助手，专注于以下研究方向：
1. 计算网络与边缘智能 (Edge Intelligence)
2. Transformer 架构及其优化
3. 网络优化与分布式计算

用户是中国科学技术大学的研究生，研究方向是"计算网络与边缘智能"，正在学习 Transformer。
请根据这个背景评估论文的相关性和价值。
"""
