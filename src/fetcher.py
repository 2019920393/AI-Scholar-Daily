"""
AI-Scholar-Daily 数据获取模块

负责从 arXiv 和 RSS 源获取论文数据
"""

import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import arxiv
import feedparser
import requests

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """论文数据类"""
    title: str
    authors: List[str]
    abstract: str
    url: str
    published: datetime
    source: str  # "arxiv" 或 "rss"
    categories: List[str] = field(default_factory=list)
    relevance_score: float = 0.0  # 关键词匹配得分
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "published": self.published.isoformat(),
            "source": self.source,
            "categories": self.categories,
            "relevance_score": self.relevance_score,
        }


class ArxivFetcher:
    """arXiv 论文获取器"""
    
    def __init__(self, categories: List[str], max_results: int = 50):
        self.categories = categories
        self.max_results = max_results
        self.client = arxiv.Client()
    
    def fetch(self, days: int = 1) -> List[Paper]:
        """
        获取最近 N 天的论文
        
        Args:
            days: 获取最近几天的论文
            
        Returns:
            论文列表
        """
        papers = []
        
        # 构建查询：按分类搜索
        category_query = " OR ".join([f"cat:{cat}" for cat in self.categories])
        
        try:
            search = arxiv.Search(
                query=category_query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for result in self.client.results(search):
                # 过滤日期
                if result.published.replace(tzinfo=None) < cutoff_date:
                    continue
                
                paper = Paper(
                    title=result.title.replace("\n", " ").strip(),
                    authors=[author.name for author in result.authors[:5]],  # 最多5个作者
                    abstract=result.summary.replace("\n", " ").strip(),
                    url=result.entry_id,
                    published=result.published.replace(tzinfo=None),
                    source="arxiv",
                    categories=[cat for cat in result.categories],
                )
                papers.append(paper)
                
            logger.info(f"从 arXiv 获取了 {len(papers)} 篇论文")
            
        except Exception as e:
            logger.error(f"arXiv 获取失败: {e}")
            raise
        
        return papers


class RSSFetcher:
    """RSS 源获取器"""
    
    # 默认 RSS 源列表
    DEFAULT_FEEDS = [
        {
            "name": "MIT Technology Review - AI",
            "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        },
        {
            "name": "Google AI Blog",
            "url": "https://blog.google/technology/ai/rss/",
        },
    ]
    
    def __init__(self, feeds: Optional[List[Dict[str, str]]] = None):
        self.feeds = feeds or self.DEFAULT_FEEDS
    
    def fetch(self, days: int = 1) -> List[Paper]:
        """
        获取最近 N 天的 RSS 内容
        
        Args:
            days: 获取最近几天的内容
            
        Returns:
            论文/文章列表
        """
        papers = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for feed_info in self.feeds:
            try:
                feed = feedparser.parse(feed_info["url"])
                
                for entry in feed.entries:
                    # 解析发布时间
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    else:
                        published = datetime.now()
                    
                    # 过滤日期
                    if published < cutoff_date:
                        continue
                    
                    # 提取摘要
                    abstract = ""
                    if hasattr(entry, "summary"):
                        # 移除 HTML 标签
                        abstract = re.sub(r"<[^>]+>", "", entry.summary)
                    elif hasattr(entry, "description"):
                        abstract = re.sub(r"<[^>]+>", "", entry.description)
                    
                    paper = Paper(
                        title=entry.title.strip() if hasattr(entry, "title") else "Untitled",
                        authors=[feed_info["name"]],  # RSS 源名称作为作者
                        abstract=abstract.strip()[:500],  # 限制长度
                        url=entry.link if hasattr(entry, "link") else "",
                        published=published,
                        source="rss",
                        categories=["news"],
                    )
                    papers.append(paper)
                
                logger.info(f"从 {feed_info['name']} 获取了 {len([p for p in papers if p.authors[0] == feed_info['name']])} 篇文章")
                
            except Exception as e:
                logger.warning(f"RSS 源 {feed_info['name']} 获取失败: {e}")
                continue
        
        return papers


class PaperFilter:
    """论文过滤和评分器"""
    
    def __init__(
        self,
        core_keywords: List[str],
        related_keywords: List[str],
        core_weight: float = 3.0,
        related_weight: float = 1.0,
    ):
        self.core_keywords = [kw.lower() for kw in core_keywords]
        self.related_keywords = [kw.lower() for kw in related_keywords]
        self.core_weight = core_weight
        self.related_weight = related_weight
    
    def calculate_relevance(self, paper: Paper) -> float:
        """
        计算论文的相关性得分
        
        Args:
            paper: 论文对象
            
        Returns:
            相关性得分
        """
        text = f"{paper.title} {paper.abstract}".lower()
        score = 0.0
        
        # 核心关键词匹配
        for kw in self.core_keywords:
            if kw in text:
                score += self.core_weight
        
        # 相关关键词匹配
        for kw in self.related_keywords:
            if kw in text:
                score += self.related_weight
        
        return score
    
    def filter_and_rank(
        self, 
        papers: List[Paper], 
        min_score: float = 1.0,
        max_count: int = 10,
    ) -> List[Paper]:
        """
        过滤并排序论文
        
        Args:
            papers: 论文列表
            min_score: 最低相关性得分
            max_count: 最大返回数量
            
        Returns:
            过滤后的论文列表
        """
        # 计算相关性得分
        for paper in papers:
            paper.relevance_score = self.calculate_relevance(paper)
        
        # 过滤低分论文
        filtered = [p for p in papers if p.relevance_score >= min_score]
        
        # 按得分排序
        filtered.sort(key=lambda p: p.relevance_score, reverse=True)
        
        # 限制数量
        return filtered[:max_count]


def fetch_papers(days: int = 1) -> List[Paper]:
    """
    获取并过滤论文的主函数
    
    Args:
        days: 获取最近几天的论文
        
    Returns:
        过滤后的论文列表
    """
    settings = get_settings()
    
    # 初始化获取器
    arxiv_fetcher = ArxivFetcher(
        categories=settings.arxiv_categories_list,
        max_results=50,
    )
    rss_fetcher = RSSFetcher()
    
    # 获取论文
    all_papers = []
    
    try:
        arxiv_papers = arxiv_fetcher.fetch(days=days)
        all_papers.extend(arxiv_papers)
    except Exception as e:
        logger.error(f"arXiv 获取失败: {e}")
    
    try:
        rss_papers = rss_fetcher.fetch(days=days)
        all_papers.extend(rss_papers)
    except Exception as e:
        logger.error(f"RSS 获取失败: {e}")
    
    if not all_papers:
        logger.warning("没有获取到任何论文")
        return []
    
    # 初始化过滤器
    paper_filter = PaperFilter(
        core_keywords=settings.core_keywords_list,
        related_keywords=settings.related_keywords_list,
    )
    
    # 过滤并排序
    filtered_papers = paper_filter.filter_and_rank(
        papers=all_papers,
        min_score=0.5,  # 允许低分论文（后续 LLM 会进一步筛选）
        max_count=settings.max_papers * 2,  # 获取更多，LLM 筛选后保留最佳
    )
    
    logger.info(f"过滤后保留 {len(filtered_papers)} 篇论文")
    
    return filtered_papers
