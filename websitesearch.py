# websearch.py - 动态年份处理版
from mcp.server.fastmcp import FastMCP
import sys
import logging
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime, timedelta

logger = logging.getLogger('xiaozhi_search')

mcp = FastMCP("mcps")

def extract_and_validate_time(text: str) -> datetime:
    """从文本提取时间并验证是否为本年度"""
    now = datetime.now()
    current_year = now.year
    
    # 1. 处理完整日期 (2024年6月15日)
    if match := re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text):
        year, month, day = map(int, match.groups())
        if year == current_year:
            return datetime(year, month, day)
    
    # 2. 处理无年份日期 (6月15日)
    elif match := re.search(r'(\d{1,2})月(\d{1,2})日', text):
        month, day = map(int, match.groups())
        return datetime(current_year, month, day)
    
    # 3. 处理简写日期 (06-15)
    elif match := re.search(r'(\d{1,2})-(\d{1,2})', text):
        month, day = map(int, match.groups())
        return datetime(current_year, month, day)
    
    # 4. 处理相对时间 (3小时前)
    elif '小时前' in text:
        hours = int(re.search(r'\d+', text).group())
        return now - timedelta(hours=hours)
    elif '分钟前' in text:
        mins = int(re.search(r'\d+', text).group())
        return now - timedelta(minutes=mins)
    
    return None  # 非本年度或无效时间

def generate_time_description(time_obj: datetime) -> str:
    """生成口语化时间描述"""
    delta = datetime.now() - time_obj
    if delta.days == 0:
        if delta.seconds >= 3600:
            return f"{delta.seconds//3600}小时前"
        return f"{delta.seconds//60}分钟前"
    return f"{time_obj.month}月{time_obj.day}日"

async def fetch_current_year_results(query: str) -> list:
    """仅获取本年度的搜索结果"""
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.baidu.com/s?wd={quote(query)}&rn=10&gpc=stf%3D{datetime.now().year}0101%7C{datetime.now().year}1231"
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            soup = BeautifulSoup(await resp.text(), 'html.parser')
            valid_results = []
            
            for item in soup.select('.result.c-container'):
                title = item.select_one('h3').get_text(strip=True)
                content = item.select_one('.c-span-last').get_text(strip=True) if item.select_one('.c-span-last') else ""
                
                # 提取并验证时间
                if time_obj := extract_and_validate_time(f"{title} {content}"):
                    # 生成优化后的文本
                    clean_text = re.sub(r'$$.*?$$|【.*?】', '', f"{title} {content}")
                    time_desc = generate_time_description(time_obj)
                    voice_text = f"{clean_text}（{time_desc}）"
                    
                    valid_results.append({
                        "time": time_obj,
                        "text": voice_text,
                        "raw": f"{title}\n{content}"
                    })
            
            # 按时间倒序排列（最新在最前）
            return sorted(valid_results, key=lambda x: x["time"], reverse=True)

@mcp.tool()
async def websitesearch(query_text: str) -> list:
    """仅返回本年度最新3条结果"""
    results = await fetch_current_year_results(query_text)
    return {
        "success": bool(results),
        "result": [item["text"] for item in results[:3]]
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")