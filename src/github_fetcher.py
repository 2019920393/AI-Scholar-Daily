"""
GitHub Trending AI 项目抓取模块

获取 GitHub Trending 中的 AI 相关项目
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class GithubProject:
    """GitHub 项目信息"""
    name: str           # 项目名称 (owner/repo)
    url: str            # 项目 URL
    description: str    # 项目描述
    language: str       # 主要语言
    stars: int          # Star 数量
    forks: int          # Fork 数量
    stars_today: int    # 今日新增 Star
    topics: List[str]   # 标签列表


# ============================================================================
# AI 相关关键词
# ============================================================================

AI_KEYWORDS = [
    # 核心术语
    "llm", "gpt", "transformer", "neural", "deep-learning", "machine-learning",
    "ai", "ml", "nlp", "cv", "computer-vision", "natural-language",
    # 模型
    "bert", "llama", "mistral", "gemini", "claude", "chatgpt", "openai",
    "stable-diffusion", "diffusion", "gan", "vae",
    # 框架
    "pytorch", "tensorflow", "huggingface", "langchain", "llamaindex",
    # 应用
    "chatbot", "rag", "agent", "embedding", "vector", "fine-tuning",
    "quantization", "inference",
]

AI_TOPICS = [
    "machine-learning", "deep-learning", "artificial-intelligence",
    "natural-language-processing", "computer-vision", "reinforcement-learning",
    "neural-network", "llm", "large-language-models", "generative-ai",
    "stable-diffusion", "transformers", "gpt", "chatgpt", "langchain",
]


# ============================================================================
# 抓取函数
# ============================================================================

def fetch_github_trending(
    language: str = "python",
    since: str = "daily",
    max_results: int = 30,
) -> List[GithubProject]:
    """
    抓取 GitHub Trending 项目
    
    Args:
        language: 编程语言 (python/javascript/...)
        since: 时间范围 (daily/weekly/monthly)
        max_results: 最大返回数量
        
    Returns:
        GithubProject 列表
    """
    url = f"https://github.com/trending/{language}?since={since}"
    
    try:
        logger.info(f"抓取 GitHub Trending: {url}")
        
        # 禁用 SSL 警告 (代理环境下可能需要)
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # verify=False 解决代理 SSL 证书验证问题
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        projects = []
        articles = soup.select("article.Box-row")
        
        for article in articles[:max_results]:
            project = _parse_trending_article(article)
            if project:
                projects.append(project)
        
        logger.info(f"获取到 {len(projects)} 个 Trending 项目")
        return projects
        
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub Trending 抓取失败: {e}")
        return []


def _parse_trending_article(article) -> Optional[GithubProject]:
    """解析单个 Trending 项目"""
    try:
        # 项目名称和 URL
        name_elem = article.select_one("h2 a")
        if not name_elem:
            return None
        
        name = name_elem.text.strip().replace("\n", "").replace(" ", "")
        url = "https://github.com" + name_elem.get("href", "")
        
        # 描述
        desc_elem = article.select_one("p")
        description = desc_elem.text.strip() if desc_elem else ""
        
        # 语言
        lang_elem = article.select_one("[itemprop='programmingLanguage']")
        language = lang_elem.text.strip() if lang_elem else "Unknown"
        
        # Stars 和 Forks
        stats = article.select("a.Link--muted")
        stars = 0
        forks = 0
        
        for stat in stats:
            href = stat.get("href", "")
            text = stat.text.strip().replace(",", "")
            if "/stargazers" in href:
                stars = _parse_number(text)
            elif "/forks" in href:
                forks = _parse_number(text)
        
        # 今日新增
        stars_today_elem = article.select_one("span.d-inline-block.float-sm-right")
        stars_today = 0
        if stars_today_elem:
            match = re.search(r"(\d+)", stars_today_elem.text.replace(",", ""))
            if match:
                stars_today = int(match.group(1))
        
        return GithubProject(
            name=name,
            url=url,
            description=description,
            language=language,
            stars=stars,
            forks=forks,
            stars_today=stars_today,
            topics=[],  # 需要额外 API 调用获取
        )
        
    except Exception as e:
        logger.warning(f"解析项目失败: {e}")
        return None


def _parse_number(text: str) -> int:
    """解析数字 (支持 k 后缀)"""
    text = text.strip().lower()
    if "k" in text:
        return int(float(text.replace("k", "")) * 1000)
    try:
        return int(text)
    except ValueError:
        return 0


# ============================================================================
# 筛选函数
# ============================================================================

def filter_ai_projects(projects: List[GithubProject]) -> List[GithubProject]:
    """
    筛选 AI 相关项目
    
    Args:
        projects: 项目列表
        
    Returns:
        筛选后的 AI 相关项目
    """
    ai_projects = []
    
    for project in projects:
        # 检查描述和名称是否包含 AI 关键词
        text = f"{project.name} {project.description}".lower()
        
        is_ai = False
        for keyword in AI_KEYWORDS:
            if keyword in text:
                is_ai = True
                break
        
        # 检查 topics
        for topic in project.topics:
            if topic.lower() in AI_TOPICS:
                is_ai = True
                break
        
        if is_ai:
            ai_projects.append(project)
    
    logger.info(f"筛选出 {len(ai_projects)} 个 AI 相关项目")
    return ai_projects


def fetch_ai_trending(
    language: str = "python",
    since: str = "daily",  # 初始时间范围
    max_results: int = 10,
    min_results: int = 5,  # 最少需要的结果数
) -> List[GithubProject]:
    """
    获取 AI 相关 Trending 项目 (带 fallback 机制)
    
    如果 "daily" 获取的项目不足 min_results 个，
    则自动尝试 "weekly" 和 "monthly"。
    
    Args:
        language: 编程语言
        since: 初始时间范围
        max_results: 最大返回数量
        min_results: 最少需要的结果数
        
    Returns:
        AI 相关项目列表
    """
    timeframes = ["daily", "weekly", "monthly"]
    
    # 确定起始索引
    try:
        start_idx = timeframes.index(since)
    except ValueError:
        start_idx = 0
    
    # 按顺序尝试获取 (daily -> weekly -> monthly)
    for tf in timeframes[start_idx:]:
        logger.info(f"正在尝试获取 {tf} Trending...")
        
        # 获取所有 Trending (多抓取一些以便过滤)
        all_projects = fetch_github_trending(language, tf, max_results * 4)
        
        # 筛选 AI 相关
        ai_projects = filter_ai_projects(all_projects)
        
        # 如果数量足够，直接返回
        if len(ai_projects) >= min_results:
            logger.info(f"✅ {tf} 获取到足够的 AI 项目 ({len(ai_projects)} 个)")
            return ai_projects[:max_results]
        else:
            logger.warning(f"⚠️ {tf} AI 项目不足 ({len(ai_projects)} < {min_results})，尝试更大范围...")
    
    # 如果都尝试完了还是不足，就返回最后一次的结果
    logger.warning("所有时间范围尝试完毕，返回最终结果")
    return ai_projects[:max_results]


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    projects = fetch_ai_trending(max_results=5)
    
    for p in projects:
        print(f"\n{p.name}")
        print(f"  ⭐ {p.stars} (+{p.stars_today} today)")
        print(f"  📝 {p.description[:100]}...")
