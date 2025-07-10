import os
import re
from urllib.parse import urljoin
from tqdm import tqdm  # 用于显示漂亮的进度条

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- 配置区 ---
# 目标列表页 URL
LIST_PAGE_URLS = [
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7036435&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7036440&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7036443&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6711231&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6711261&isChild=true',
    'https://www.hefei.gov.cn/xxgk/szfgb/2025/dlh/index.html',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6711241&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6979911&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6979901&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=7018043&isChild=true',
    'https://www.hefei.gov.cn/public/column/1741?type=4&action=list&nav=3&catId=6979891&isChild=true',
    'https://www.hefei.gov.cn/xxgk/gsgg/index.html',
]
# 列表页中，文章链接<a>标签的XPath
# A_XPATH = '//a[@class = "left" or normalize-space(@class) = "title"]'
A_CSS = 'a.left, a.title'
# 文章详情页中，正文内容的XPath
CONTENT_CSS = '#container div.gk_container, #container div.container:has(.con_main), .main-content #content'
# Markdown 文件保存目录
OUTPUT_DIR = "hefei_gov_md"


# --- 第1部分: 从列表页获取所有文章链接 ---

def get_article_urls(driver, list_urls):
    """
    遍历所有列表页，提取所有新闻文章的链接。
    """
    print("🚀 正在访问列表页并获取所有文章链接...")
    all_urls = []
    wait = WebDriverWait(driver, 15)
    for list_url in tqdm(list_urls, desc="扫描列表页"):
        try:
            driver.get(list_url)
            # 等待文章链接出现，这是页面加载成功的标志
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, A_CSS)))
            alinks = driver.find_elements(by=By.CSS_SELECTOR, value=A_CSS)
            for alink in alinks:
                href = alink.get_attribute('href')
                if href:
                    # 将相对链接转换为绝对链接
                    absolute_url = urljoin(list_url, href)
                    all_urls.append(absolute_url)
        except Exception as e:
            print(f"❌ 访问或解析列表页时出错: {list_url} - {e}")

    unique_urls = list(set(all_urls))
    print(f"✅ 扫描完成！共找到 {len(unique_urls)} 个独特的文章链接。")
    return unique_urls


# --- 第2部分: 逐一访问链接并提取内容 ---

def extract_article_data(driver, url):
    """
    让浏览器访问单个文章URL，并提取标题和内容。
    """
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # 等待内容区域加载完成，这是页面加载成功的关键标志
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, CONTENT_CSS)))

        # 提取正文
        content_element = driver.find_element(By.CSS_SELECTOR, CONTENT_CSS)
        content = content_element.text.strip()
        images = list(map(lambda x: x.get_attribute('src'), content_element.find_elements(By.TAG_NAME, "img")))

        return {
            "url": url,
            "title": driver.title,
            "content": content,
            "images": images  # 提取所有图片的 src 属性
        }

    except TimeoutException:
        print(f"❌ 访问超时或未找到内容元素: {url}")
    except NoSuchElementException:
        print(f"❌ 页面结构不匹配，无法找到内容: {url}")
    except Exception as e:
        print(f"❌ 处理页面时发生未知错误 {url}: {e}")

    return None


# --- 第3部分: 保存为 Markdown ---

def save_to_markdown(article_data: dict):
    """
    将提取的文章数据保存为 Markdown 文件。
    """
    if not article_data or not article_data.get('title') or not article_data.get('content'):
        print(f"⚠️ 跳过保存，因为数据不完整: {article_data.get('url')}")
        return False

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    title = article_data['title']
    content = article_data['content']
    url = article_data['url']
    images = article_data['images']

    # 清理标题作为文件名，避免非法字符
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title).strip()
    # 尝试从URL中提取一个唯一ID作为文件名，如果失败则使用标题
    filename_match = re.search(r'/(\w+)\.html', url)
    if filename_match:
        filename = f"{filename_match.group(1)}.md"
    else:
        filename = f"{safe_title[:60]}.md"

    filepath = os.path.join(OUTPUT_DIR, title + '_' + filename)

    md_content = f"# {title}\n\n"
    md_content += f"**Source URL:** {url}\n\n"
    md_content += "---\n\n"
    md_content += content
    md_content += "\n\n"
    for image in images:
        if image:
            md_content += f"![Image]({image})\n\n"

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        return True
    except Exception as e:
        print(f"❌ 保存文件失败 {filepath}: {e}")
        return False


# --- 主执行函数 ---

def main():
    """
    主函数，协调整个爬取流程。
    """
    print("🚀 正在启动浏览器...")
    options = webdriver.EdgeOptions()
    options.add_argument("--headless")
    options.add_argument('--edge-skip-compat-layer-relaunch')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--disable-blink-features=AutomationControlled')
    service = Service()
    driver = webdriver.Edge(service=service, options=options)

    saved_count = 0
    total_urls = 0
    try:
        # 1. 获取所有链接
        urls_to_fetch = get_article_urls(driver, LIST_PAGE_URLS)
        total_urls = len(urls_to_fetch)

        if not urls_to_fetch:
            print("未找到任何文章链接，程序退出。")
            return

        print(f"\n📰 开始逐一抓取 {total_urls} 个页面的内容...")

        # 2. 循环处理每个链接
        for url in tqdm(urls_to_fetch, desc="正在爬取文章"):
            article_data = extract_article_data(driver, url)

            # 3. 如果成功提取，则保存
            if article_data:
                if save_to_markdown(article_data):
                    saved_count += 1

    finally:
        driver.quit()
        print("\n🚪 浏览器已关闭。")

    print(f"\n🎉 全部完成！成功保存 {saved_count} / {total_urls} 篇文章到 '{OUTPUT_DIR}' 目录。")


if __name__ == "__main__":
    main()
