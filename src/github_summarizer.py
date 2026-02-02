"""
GitHub 项目 LLM 摘要模块

使用 LLM 分析和摘要 GitHub 项目
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

from .config import get_settings, RESEARCH_CONTEXT
from .github_fetcher import GithubProject

logger = logging.getLogger(__name__)


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class ProjectSummary:
    """项目摘要"""
    name: str           # 项目名称
    url: str            # 项目 URL
    stars: int          # Star 数量
    stars_today: int    # 今日新增
    description: str    # 原始描述
    summary: str        # LLM 生成的中文摘要
    highlights: str     # 亮点分析
    use_cases: str      # 应用场景
    score: int          # 推荐度 (1-10)


# ============================================================================
# LLM 客户端
# ============================================================================

def get_llm_client() -> OpenAI:
    """获取 LLM 客户端"""
    settings = get_settings()
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


# ============================================================================
# 摘要函数
# ============================================================================

import json
import re

# ... (Previous code)

SUMMARY_PROMPT = """你是一个 AI 技术专家。请分析以下 GitHub 项目，并以 **纯 JSON 格式** 返回摘要。

项目信息:
- 名称: {name}
- 描述: {description}
- Stars: {stars} (+{stars_today} today)
- 语言: {language}

请返回如下 JSON (不要添加 Markdown 代码块标记，不要有其他文字):
{{
    "summary": "一句话中文摘要(30字以内)",
    "highlights": "技术亮点(1-2点)",
    "use_cases": "适用场景",
    "score": 8
}}

评分标准(score): 1-10分，10分表示强烈推荐给 AI 开发者。
"""

def _extract_json(content: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON"""
    try:
        # 1. 尝试直接解析
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 2. 尝试提取代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except:
            pass
            
    # 3. 尝试寻找最外层 {}
    try:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            return json.loads(content[start:end+1])
    except:
        pass
        
    return None


def summarize_project(project: GithubProject) -> Optional[ProjectSummary]:
    """
    使用 LLM 摘要单个项目 (JSON 模式)
    """
    try:
        client = get_llm_client()
        settings = get_settings()
        
        prompt = SUMMARY_PROMPT.format(
            name=project.name,
            description=project.description,
            stars=project.stars,
            stars_today=project.stars_today,
            language=project.language,
        )
        
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": RESEARCH_CONTEXT},
                {"role": "user", "content": prompt},
            ],
            # Kimi 等模型不支持 temperature 参数
            max_tokens=600,
        )
        
        content = response.choices[0].message.content
        logger.info(f"LLM 响应 [{project.name}]: {content[:50]}...")
        
        data = _extract_json(content)
        
        if not data:
            logger.warning(f"JSON 解析失败 [{project.name}]")
            # 降级策略: 如果解析失败，使用原始描述
            return ProjectSummary(
                name=project.name,
                url=project.url,
                stars=project.stars,
                stars_today=project.stars_today,
                description=project.description,
                summary=project.description[:50] + " (自动摘要失败)",
                highlights="无法解析",
                use_cases="无法解析",
                score=5,
            )
            
        return ProjectSummary(
            name=project.name,
            url=project.url,
            stars=project.stars,
            stars_today=project.stars_today,
            description=project.description,
            summary=data.get("summary", "无摘要"),
            highlights=data.get("highlights", "无亮点"),
            use_cases=data.get("use_cases", "无场景"),
            score=int(data.get("score", 5)),
        )
        
    except Exception as e:
        logger.error(f"项目摘要生成失败 [{project.name}]: {e}")
        return None


def summarize_projects(
    projects: List[GithubProject],
    max_count: int = 10,
) -> List[ProjectSummary]:
    """
    批量摘要项目
    
    Args:
        projects: 项目列表
        max_count: 最大处理数量
        
    Returns:
        摘要列表
    """
    summaries = []
    
    for project in projects[:max_count]:
        logger.info(f"摘要项目: {project.name}")
        summary = summarize_project(project)
        if summary:
            summaries.append(summary)
    
    # 按推荐度排序
    summaries.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"生成 {len(summaries)} 个项目摘要")
    return summaries
