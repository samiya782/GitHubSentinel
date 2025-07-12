from datetime import datetime
from urllib.parse import urljoin
import re
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from logger import LOG  # 导入日志模块
import os  # 导入os模块用于文件和目录操作
from tqdm import tqdm  # 导入tqdm模块用于显示进度条

class AhGovClient:
    ParseConfigs = [
        {
            "urls": ["https://www.ah.gov.cn/public/index.html"],
            "a_css": "a.tit",
            "content_css": "#container > div.container",
        },
        # {
        #     "urls": [
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7036435&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7036440&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7036443&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6711231&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6711261&isChild=true",
        #         "https://www.ah.gov.cn/xxgk/szfgb/2025/dlh/index.html",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6711241&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6979911&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6979901&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7018043&isChild=true",
        #         "https://www.ah.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6979891&isChild=true",
        #         "https://www.ah.gov.cn/xxgk/gsgg/index.html"
        #     ],
        #     "a_css": 'a.left, a.title',
        #     "content_css": '#container div.gk_container, #container div.container:has(.con_main), .main-content #content'
        # }
    ]
    def __init__(self):
        LOG.debug("正在启动浏览器...")
        options = webdriver.EdgeOptions()
        options.add_argument("--headless")
        options.add_argument('--edge-skip-compat-layer-relaunch')
        options.add_argument("--disable-gpu")  # 在无头模式下有时需要
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--disable-blink-features=AutomationControlled')
        service = Service()
        try:
            self.driver = webdriver.Edge(service=service, options=options)
            LOG.info("浏览器启动成功")
        except Exception as e:
            LOG.error(f"浏览器启动失败: {e}")
            raise e

    def _get_article_urls(self, urls, a_css):
        """
        遍历所有列表页，提取所有新闻文章的链接。
        """
        LOG.debug("正在访问列表页并获取所有文章链接...")
        all_urls = []
        wait = WebDriverWait(self.driver, 15)
        for url in tqdm(urls, desc="扫描列表页"):
            try:
                self.driver.get(url)
                # 等待文章链接出现，这是页面加载成功的标志
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, a_css)))
                alinks = self.driver.find_elements(by=By.CSS_SELECTOR, value=a_css)
                for alink in alinks:
                    href = alink.get_attribute('href')
                    if href:
                        # 将相对链接转换为绝对链接
                        absolute_url = urljoin(url, href)
                        all_urls.append(absolute_url)
            except Exception as e:
                LOG.error(f"访问或解析列表页时出错: {url} - {e}")

        unique_urls = list(set(all_urls))
        LOG.debug(f"扫描完成！共找到 {len(unique_urls)} 个独特的文章链接。")
        return unique_urls


    def _extract_article_data(self, url, content_css):
        """
            让浏览器访问单个文章URL，并提取标题和内容。
            """
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 15)

            # 等待内容区域加载完成，这是页面加载成功的关键标志
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, content_css)))

            # 提取正文
            content_element = self.driver.find_element(By.CSS_SELECTOR, content_css)
            content = self.driver.execute_script("return arguments[0].innerText;", content_element).strip()
            images = list(map(lambda x: x.get_attribute('src'), content_element.find_elements(By.TAG_NAME, "img")))

            return {
                "url": url,
                "title": self.driver.title,
                "content": content,
                "images": images  # 提取所有图片的 src 属性
            }

        except TimeoutException:
            LOG.error(f"访问超时或未找到内容元素: {url}")
        except NoSuchElementException:
            LOG.error(f"页面结构不匹配，无法找到内容: {url}")
        except Exception as e:
            LOG.error(f"处理页面时发生未知错误 {url}: {e}")

        return None

    def fetch_articles(self):
        """
        使用 Selenium 获取所有配置的新闻文章链接，并提取内容。
        """
        all_articles = []
        for config in self.ParseConfigs:
            article_urls = self._get_article_urls(config["urls"], config["a_css"])
            for url in tqdm(article_urls, desc="提取文章内容"):
                try:
                    article_data = self._extract_article_data(url, config["content_css"])
                    if article_data:
                        all_articles.append(article_data)
                except Exception as e:
                    LOG.error(f"提取文章内容时出错: {url} - {e}")

        LOG.info(f"共提取到 {len(all_articles)} 篇文章。")
        return all_articles

    # @staticmethod
    # def _save_to_markdown(output_dir: str, article_data: dict):
    #     """
    #     将提取的文章数据保存为 Markdown 文件。
    #     """
    #     if not article_data or not article_data.get('title') or not article_data.get('content'):
    #         LOG.error(f"跳过保存，因为数据不完整: {article_data.get('url')}")
    #         return False
    #
    #     os.makedirs(output_dir, exist_ok=True)
    #
    #     title = article_data['title']
    #     content = article_data['content']
    #     url = article_data['url']
    #     images = article_data['images']
    #
    #     filepath = os.path.join(output_dir, title)
    #
    #     md_content = f"# [{title}]({url})\n\n"
    #     md_content += "---\n\n"
    #     md_content += content
    #     md_content += "\n\n"
    #     for image in images:
    #         if image:
    #             md_content += f"![Image]({image})\n"
    #
    #     try:
    #         with open(filepath, 'w', encoding='utf-8') as f:
    #             f.write(md_content)
    #         return filepath
    #     except Exception as e:
    #         LOG.error(f"保存文件失败 {filepath}: {e}")
    #         return ""

    def export_articles(self, date=None):
        LOG.debug("准备导出安徽政府的最新文章。")
        articles = self.fetch_articles()  # 获取新闻数据

        if not articles:
            LOG.warning("未找到任何安徽政府的最新文章。")
            return None

        # 如果未提供 date 和 hour 参数，使用当前日期和时间
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 构建存储路径
        dir_path = os.path.join('ah_gov', date)
        os.makedirs(dir_path, exist_ok=True)  # 确保目录存在

        # for article_data in articles:
        #     if filepath := self._save_to_markdown(dir_path, article_data):
        #         LOG.debug(f"文章已保存: {filepath}")

        file_path = os.path.join(dir_path, f'{date}.md')  # 定义文件路径
        with open(file_path, 'w') as file:
            file.write(f"# 安徽政府网站最新文件 ({date})\n\n")
            for idx, article in enumerate(articles, start=1):
                file.write(f"---\n\n## {idx}. [{article['title']}]({article['url']})\n\n")
                file.write(f"{article['content']}\n\n")
                for image in article['images']:
                    if image:
                        file.write(f"![Image]({image})\n")
                file.write("\n")

        LOG.info(f"安徽政府网站最新文件生成：{file_path}")
        return file_path

if __name__ == "__main__":
    client = AhGovClient()
    client.export_articles()  # 默认情况下使用当前日期和时间
