"""
AI-Scholar-Daily LLM 摘要模块

调用 OpenAI 兼容 API 对论文进行智能摘要和评分
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from openai import OpenAI

from .config import get_settings, RESEARCH_CONTEXT
from .fetcher import Paper

logger = logging.getLogger(__name__)


@dataclass
class PaperSummary:
    """论文摘要结果"""
    title: str
    authors: List[str]
    url: str
    relevance_score: int  # 1-10 分
    core_contribution: str  # 一句话核心贡献
    edge_insight: str  # 对边缘智能的启发
    should_include: bool  # 是否应该推送
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "authors": self.authors,
            "url": self.url,
            "relevance_score": self.relevance_score,
            "core_contribution": self.core_contribution,
            "edge_insight": self.edge_insight,
            "should_include": self.should_include,
        }


# LLM 分析 Prompt
ANALYSIS_PROMPT = """请分析以下论文，并以 JSON 格式返回结果。

论文标题: {title}
作者: {authors}
摘要: {abstract}

请严格按照以下 JSON 格式返回（不要包含其他文字）:
{{
    "relevance_score": <1-10的整数，10表示与边缘智能/Transformer研究高度相关>,
    "core_contribution": "<一句话概括论文的核心贡献，不超过50字>",
    "edge_insight": "<这篇论文对边缘智能研究的潜在启发，不超过50字>",
    "should_include": <true/false，是否值得推送给研究边缘智能的研究生>
}}

评分标准:
- 9-10分: 直接研究边缘智能、边缘推理、Transformer 优化
- 7-8分: 相关研究如联邦学习、模型压缩、移动计算
- 5-6分: 间接相关如网络优化、分布式系统
- 1-4分: 关联性较弱的 AI 研究
"""


class Summarizer:
    """LLM 摘要器"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 5,  # 增加重试次数以提高成功率
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.max_retries = max_retries
    
    def _extract_json(self, content: str) -> Optional[dict]:
        """
        从 LLM 响应中提取 JSON 对象
        """
        import re
        
        # 1. 替换中文引号为英文引号
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        
        # 2. 尝试提取 markdown 代码块中的 JSON
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if code_block_match:
            content = code_block_match.group(1).strip()
        
        # 3. 尝试找到最外层的 {} 对
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(content):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    json_str = content[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # 继续尝试下一个
                        start_idx = -1
                        continue
        
        # 4. 如果上述方法都失败，尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 5. 最后尝试用正则提取关键字段
        score_match = re.search(r'"?relevance_score"?\s*:\s*(\d+)', content)
        core_match = re.search(r'"?core_contribution"?\s*:\s*"([^"]*)"', content)
        insight_match = re.search(r'"?edge_insight"?\s*:\s*"([^"]*)"', content)
        include_match = re.search(r'"?should_include"?\s*:\s*(true|false)', content, re.IGNORECASE)
        
        if score_match:
            return {
                "relevance_score": int(score_match.group(1)),
                "core_contribution": core_match.group(1) if core_match else "无法解析",
                "edge_insight": insight_match.group(1) if insight_match else "无法解析",
                "should_include": include_match.group(1).lower() == "true" if include_match else False,
            }
        
        return None
    
    def analyze_paper(self, paper: Paper) -> Optional[PaperSummary]:
        """
        分析单篇论文
        
        Args:
            paper: 论文对象
            
        Returns:
            摘要结果，失败返回 None
        """
        prompt = ANALYSIS_PROMPT.format(
            title=paper.title,
            authors=", ".join(paper.authors[:3]),  # 最多3个作者
            abstract=paper.abstract[:1000],  # 限制摘要长度
        )
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": RESEARCH_CONTEXT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=1.0,  # Kimi K2.5 只支持 temperature=1
                    max_tokens=500,
                )
                
                # 获取响应内容（兼容 Kimi K2 的 reasoning_content）
                message = response.choices[0].message
                content = ""
                
                # 尝试多种字段
                if hasattr(message, 'content') and message.content:
                    content = message.content.strip()
                elif hasattr(message, 'reasoning_content') and message.reasoning_content:
                    content = message.reasoning_content.strip()
                
                # 记录响应状态
                if not content:
                    logger.warning(f"响应内容为空 (尝试 {attempt + 1})")
                    continue
                
                result = self._extract_json(content)
                
                if result is None:
                    logger.warning(f"JSON 解析失败 (尝试 {attempt + 1}): 无法提取有效 JSON")
                    continue
                
                return PaperSummary(
                    title=paper.title,
                    authors=paper.authors,
                    url=paper.url,
                    relevance_score=int(result.get("relevance_score", 5)),
                    core_contribution=result.get("core_contribution", "无法解析"),
                    edge_insight=result.get("edge_insight", "无法解析"),
                    should_include=result.get("should_include", False),
                )
                
            except Exception as e:
                logger.error(f"LLM 调用失败 (尝试 {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                continue
        
        return None
    
    def analyze_papers(
        self, 
        papers: List[Paper],
        max_count: int = 10,
    ) -> List[PaperSummary]:
        """
        批量分析论文
        
        Args:
            papers: 论文列表
            max_count: 最终保留的最大数量
            
        Returns:
            摘要结果列表
        """
        summaries = []
        
        for i, paper in enumerate(papers):
            logger.info(f"分析论文 {i + 1}/{len(papers)}: {paper.title[:50]}...")
            
            try:
                summary = self.analyze_paper(paper)
                if summary and summary.should_include:
                    summaries.append(summary)
                    logger.info(f"  -> 相关度: {summary.relevance_score}/10, 已保留")
                else:
                    logger.info(f"  -> 跳过（不符合推送条件）")
            except Exception as e:
                logger.error(f"分析失败: {e}")
                continue
            
            # 如果已经收集到足够的论文，提前结束
            if len(summaries) >= max_count:
                break
        
        # 按相关度排序
        summaries.sort(key=lambda s: s.relevance_score, reverse=True)
        
        return summaries[:max_count]


def summarize_papers(papers: List[Paper]) -> List[PaperSummary]:
    """
    摘要论文的主函数
    
    Args:
        papers: 论文列表
        
    Returns:
        摘要结果列表
    """
    settings = get_settings()
    
    summarizer = Summarizer(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )
    
    summaries = summarizer.analyze_papers(
        papers=papers,
        max_count=settings.max_papers,
    )
    
    logger.info(f"完成摘要，共 {len(summaries)} 篇论文")
    
    return summaries


# ============================================================================
# 每日总结生成
# ============================================================================

OVERVIEW_PROMPT = """你是一个 AI 前沿动态分析专家。请根据以下今日 AI 领域的论文和项目，生成一段简洁的中文总结。

今日内容:
{content_list}

请生成一段 100-150 字的总结，要求:
1. 概括今日 AI 领域的主要动态和趋势
2. 突出最值得关注的 2-3 个亮点
3. 使用简洁专业的语言
4. 不要使用 Markdown 格式，使用纯文本

直接输出总结内容，不要有任何前缀或解释。
"""


def generate_daily_overview(
    paper_summaries: list = None,
    project_summaries: list = None,
) -> str:
    """
    生成每日总结概览
    
    Args:
        paper_summaries: 论文摘要列表 (PaperSummary)
        project_summaries: 项目摘要列表 (ProjectSummary)
        
    Returns:
        str: 今日总结文本
    """
    settings = get_settings()
    
    # 构建内容列表
    content_items = []
    
    # 添加论文
    if paper_summaries:
        for i, s in enumerate(paper_summaries[:5], 1):  # 最多 5 篇
            content_items.append(f"论文{i}: {s.title} - {s.core_contribution}")
    
    # 添加项目
    if project_summaries:
        for i, s in enumerate(project_summaries[:5], 1):  # 最多 5 个
            content_items.append(f"项目{i}: {s.name} ({s.stars}⭐) - {s.summary}")
    
    if not content_items:
        return "今日暂无重要 AI 动态。"
    
    content_list = "\n".join(content_items)
    
    try:
        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": RESEARCH_CONTEXT},
                {"role": "user", "content": OVERVIEW_PROMPT.format(content_list=content_list)},
            ],
            max_tokens=300,
        )
        
        overview = response.choices[0].message.content.strip()
        logger.info("每日总结生成成功")
        return overview
        
    except Exception as e:
        logger.error(f"每日总结生成失败: {e}")
        # 返回默认总结
        return f"今日收录 {len(paper_summaries or [])} 篇论文和 {len(project_summaries or [])} 个热门项目。"

