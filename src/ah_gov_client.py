import asyncio
import os
import re
import base64
import uuid
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Dict, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm import tqdm

from logger import LOG

class AhGovClient:
    """
    一个高效的异步客户端，用于爬取安徽省政府网站的文章，
    并将结果导出为Markdown文件。
    内部使用 httpx, asyncio 和 BeautifulSoup 实现。
    """
    ParseConfigs = [
        {
            "urls": ["https://www.ah.gov.cn/public/index.html"],
            "a_css": "a.tit",
            "content_css": "#container > div.container",
        },
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self, output_dir="ah_gov"):
        """
        初始化客户端。

        Args:
            output_dir (str): 存放结果的根目录。
        """
        self.output_dir = output_dir
        LOG.info("AhGovClient (Async Version) 已初始化。")

    def _save_base64_image(self, data_uri: str, save_dir: str) -> Optional[str]:
        """解码Base64数据并保存为图片文件。"""
        try:
            header, encoded_data = data_uri.split(',', 1)
            match = re.search(r'image/(\w+);', header)
            file_extension = match.group(1) if match else 'png'
            image_data = base64.b64decode(encoded_data)
            filename = f"{uuid.uuid4()}.{file_extension}"
            filepath = os.path.join(save_dir, filename)

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(image_data)

            # 返回相对于主Markdown文件的相对路径
            return os.path.join('images', filename)
        except Exception as e:
            LOG.error(f"保存Base64图片失败: {e}")
            return None

    async def _get_article_urls(self, url: str, a_css: str, client: httpx.AsyncClient) -> List[str]:
        """异步访问URL，提取所有匹配的文章链接。"""
        try:
            response = await client.get(url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            article_tags = soup.select(a_css)

            found_urls = [urljoin(url, tag.get('href')) for tag in article_tags if tag.get('href')]
            return found_urls
        except httpx.RequestError as e:
            LOG.error(f"请求列表页 {url} 时发生网络错误: {e}")
            return []
        except Exception as e:
            LOG.error(f"解析列表页 {url} 时发生未知错误: {e}")
            return []

    async def _extract_and_process_article(self, url: str, content_css: str, client: httpx.AsyncClient,
                                           image_save_dir: str) -> Optional[Dict]:
        """访问单个文章URL，提取数据，并将内容转换为Markdown。"""
        try:
            response = await client.get(url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            title = soup.select_one('title').get_text(strip=True) if soup.select_one('title') else "无标题"
            content_element = soup.select_one(content_css)

            if not content_element:
                LOG.warning(f"在 {url} 未找到内容元素 (CSS: {content_css})")
                return None

            content_markdown = md(str(content_element), heading_style="ATX").strip()

            image_paths = []
            for img_tag in content_element.find_all('img'):
                src = img_tag.get('src')
                if not src:
                    continue

                if src.startswith('data:image/'):
                    local_path = self._save_base64_image(src, image_save_dir)
                    if local_path:
                        image_paths.append(local_path)
                else:
                    absolute_url = urljoin(url, src)
                    image_paths.append(absolute_url)

            return {
                "url": url,
                "title": title,
                "content": content_markdown,
                "image_paths": image_paths
            }
        except Exception as e:
            LOG.error(f"处理文章 {url} 失败: {e}")
            return None

    def _save_articles_to_markdown(self, articles: List[Dict], daily_output_dir: str, date_str: str) -> str:
        """将提取的文章数据保存到单个Markdown文件中。"""
        md_filename = f"{date_str}_安徽省政府公开信息.md"
        md_filepath = os.path.join(daily_output_dir, md_filename)

        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 安徽省政府网站公开信息 ({date_str})\n\n")
            for idx, article in enumerate(articles, 1):
                if not article: continue
                f.write(f"---\n\n")
                f.write(f"## {idx}. {article['title']}\n\n")
                f.write(f"**源链接:** [{article['url']}]({article['url']})\n\n")
                f.write(f"### 正文内容\n\n")
                f.write(f"{article['content']}\n\n")

                if article['image_paths']:
                    f.write(f"### 相关图片\n\n")
                    for img_path in article['image_paths']:
                        # 确保路径在Markdown中是有效的（使用正斜杠）
                        f.write(f"![Image]({img_path.replace(os.path.sep, '/')})\n")
                f.write("\n")

        LOG.info(f"所有文章已成功导出到: {md_filepath}")
        return md_filepath

    async def _run_async_pipeline(self, image_save_dir: str) -> List[Dict]:
        """
        执行完整的异步爬取和解析流程，正确处理多个配置。
        """
        # 我们将使用一个字典来存储待抓取的URL和其对应的content_css，
        # 这也天然地解决了URL去重的问题。
        # 格式: { "http://.../article1": "#css_selector_for_article1", ... }
        urls_to_scrape = {}

        async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True) as client:
            # --- 阶段一：并发获取所有文章链接，并保持其与content_css的关联 ---

            # 为了保持关联，我们创建一个临时的辅助函数
            async def get_urls_with_context(list_url: str, a_css: str, content_css: str) -> List[Tuple[str, str]]:
                """获取链接，并为每个链接附加上下文（它的content_css）"""
                found_urls = await self._get_article_urls(list_url, a_css, client)
                return [(url, content_css) for url in found_urls]

            LOG.info("开始从所有配置中获取文章链接...")
            list_page_tasks = []
            for config in self.ParseConfigs:
                content_css_for_this_config = config["content_css"]
                a_css_for_this_config = config["a_css"]
                for list_url in config["urls"]:
                    # 为每个列表页创建一个任务，这个任务会返回 (URL, content_css) 对
                    task = get_urls_with_context(list_url, a_css_for_this_config, content_css_for_this_config)
                    list_page_tasks.append(task)

            # results 将是一个列表的列表，例如： [[('url1', 'css1')], [('url2', 'css2'), ('url3', 'css2')]]
            results = await asyncio.gather(*list_page_tasks)

            # 将所有结果扁平化并存入字典，完成去重
            for url_css_pair_list in results:
                for url, content_css in url_css_pair_list:
                    urls_to_scrape[url] = content_css

            if not urls_to_scrape:
                LOG.warning("所有配置均未找到任何文章链接。")
                return []

            LOG.info(f"链接获取完成，共找到 {len(urls_to_scrape)} 个独特的文章链接。")

            # --- 阶段二：并发提取所有文章的内容，使用各自正确的 content_css ---
            LOG.info("开始提取文章内容...")
            article_tasks = []
            for url, content_css in urls_to_scrape.items():
                # 在创建任务时，传入与该URL绑定的正确的content_css
                task = self._extract_and_process_article(url, content_css, client, image_save_dir)
                article_tasks.append(task)

            # 使用tqdm显示进度条
            articles_data = []
            for future in tqdm(asyncio.as_completed(article_tasks), total=len(article_tasks), desc="提取文章内容"):
                result = await future
                articles_data.append(result)

        # 过滤掉提取失败的结果 (None)
        valid_articles = [data for data in articles_data if data]
        LOG.info(f"内容提取完成，成功提取 {len(valid_articles)} 篇文章。")
        return valid_articles

    def export_articles(self, date: Optional[str] = None) -> Optional[str]:
        """
        公开方法：执行整个爬取、解析和导出流程。
        这是一个同步方法，它在内部运行一个异步事件循环。

        Args:
            date (str, optional): YYYY-MM-DD格式的日期。如果为None，则使用当前日期。

        Returns:
            Optional[str]: 生成的Markdown文件的路径，如果失败则返回None。
        """
        LOG.info("开始执行文章导出任务...")

        if date is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        else:
            date_str = date

        # 构建存储路径
        daily_output_dir = os.path.join(self.output_dir, date_str)
        image_save_dir = os.path.join(daily_output_dir, 'images')
        os.makedirs(image_save_dir, exist_ok=True)

        # 运行异步核心流程并获取结果
        try:
            # 这是连接同步和异步世界的桥梁
            articles = asyncio.run(self._run_async_pipeline(image_save_dir))
        except Exception as e:
            LOG.error(f"异步爬取流程发生严重错误: {e}")
            return None

        if not articles:
            LOG.warning("未找到任何可导出的文章。")
            return None

        # 保存到文件
        file_path = self._save_articles_to_markdown(articles, daily_output_dir, date_str)
        return file_path


if __name__ == "__main__":
    # --- 调用方式和原来完全一样 ---
    LOG.info("创建 AhGovClient 实例...")
    client = AhGovClient()

    LOG.info("调用 export_articles 方法...")
    markdown_file_path = client.export_articles()

    if markdown_file_path:
        LOG.info(f"任务成功完成！文件保存在: {markdown_file_path}")
    else:
        LOG.error("任务失败，未能生成文件。")
