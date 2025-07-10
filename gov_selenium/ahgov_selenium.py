import os
import re
from tqdm import tqdm  # 用于显示漂亮的进度条

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- 配置区 ---
# 主页 URL
HOME_URL = "https://www.ah.gov.cn/public/index.html"
# Markdown 文件保存目录
OUTPUT_DIR = "ahgov_md"
A_CSS = "a.tit"
CONTENT_CSS = "#container > div.container"
# --- 第1部分: 使用 Selenium 获取文章链接 (与之前基本相同) ---

def get_article_urls(driver):
    """
    使用 Selenium 访问主页，并提取所有新闻文章的链接。
    """
    print("🚀 正在访问主页并获取文章链接...")
    urls = []
    try:
        driver.get(HOME_URL)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, A_CSS)))

        alinks = driver.find_elements(by=By.CSS_SELECTOR, value=A_CSS)
        for alink in alinks:
            href = alink.get_attribute('href')
            if href and href.startswith('http'):
                urls.append(href)

        print(f"✅ 成功找到 {len(set(urls))} 个独特的文章链接。")
    except Exception as e:
        print(f"❌ 获取链接时出错: {e}")

    return list(set(urls))  # 返回去重后的链接列表


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
        content = content_element.text.strip()  # .text 会自动提取所有子标签的文本内容
        images = list(map(lambda x: x.get_attribute('src'), content_element.find_elements(By.TAG_NAME, "img")))

        return {
            "url": url,
            "title": driver.title,
            "content": content,
            "images": images  # 提取所有图片的 src 属性
        }

    except TimeoutException:
        print(f"❌ 访问超时或未找到关键元素: {url}")
    except NoSuchElementException:
        print(f"❌ 页面结构不同，无法找到标题或内容: {url}")
    except Exception as e:
        print(f"❌ 处理页面时发生未知错误 {url}: {e}")

    return None


# --- 第3部分: 保存为 Markdown (与之前相同) ---

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

    # 从 URL 中提取文件名
    filename_match = re.search(r'/(\d+)\.html', url)
    if filename_match:
        filename = f"{filename_match.group(1)}.md"
    else:
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = f"{safe_title[:50]}.md"

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
    options.add_argument("--disable-gpu")  # 在无头模式下有时需要
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service()
    driver = webdriver.Edge(service=service, options=options)

    saved_count = 0
    try:
        # 1. 获取所有链接
        urls_to_fetch = get_article_urls(driver)

        if not urls_to_fetch:
            print("未找到任何链接，程序退出。")
            return

        print(f"\n📰 开始逐一抓取 {len(urls_to_fetch)} 个页面的内容...")

        # 2. 循环处理每个链接
        # 使用 tqdm 创建一个进度条
        for url in tqdm(urls_to_fetch, desc="正在爬取文章"):
            article_data = extract_article_data(driver, url)

            # 3. 如果成功提取，则保存
            if article_data:
                if save_to_markdown(article_data):
                    saved_count += 1

    finally:
        driver.quit()
        print("\n🚪 浏览器已关闭。")

    print(f"\n🎉 全部完成！成功保存 {saved_count} / {len(urls_to_fetch)} 篇文章到 '{OUTPUT_DIR}' 目录。")


if __name__ == "__main__":
    main()
