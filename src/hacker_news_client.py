from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
from logger import LOG


class HackerNewsClient:
    """
    A client responsible for fetching and exporting data from Hacker News.
    """
    @staticmethod
    def fetch_hackernews_top_stories(page=1):
        """
        Fetches top stories from the specified number of Hacker News pages.
        """
        base_url = 'https://news.ycombinator.com/?p={page}'
        top_stories = []

        for i in range(1, page + 1):
            current_url = base_url.format(page=i)
            print(f"Fetching from: {current_url}")
            try:
                response = requests.get(current_url)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching page {i}: {e}")
                continue  # Skip to the next page on error

            soup = BeautifulSoup(response.text, 'html.parser')
            stories = soup.find_all('tr', class_='athing')

            for story in stories:
                title_tag = story.find('span', class_='titleline').find('a')
                if title_tag:
                    title = title_tag.text
                    link = title_tag['href']
                    if link.startswith("item?id="):
                        link = "https://news.ycombinator.com/" + link
                    top_stories.append({'title': title, 'link': link})

        return top_stories

    @staticmethod
    def export_daily_news(page=1):
        """
        Fetches stories and exports them to a dated text file.
        """
        today = datetime.now().date().isoformat()
        stories_to_export = HackerNewsClient.fetch_hackernews_top_stories(page)

        if not stories_to_export:
            LOG.error("No stories were fetched. Aborting export.")
            return

        hacker_news_dir = os.path.join('daily_progress', 'hacker_news')  # 构建目录路径
        os.makedirs(hacker_news_dir, exist_ok=True)  # 确保目录存在
        file_path = os.path.join(hacker_news_dir, f'hackernews_top_{len(stories_to_export)}_stories_{today}.md')

        try:
            with open(file_path, 'w') as file:
                file.write(f"Top {len(stories_to_export)} Hacker News Stories for {today}\n\n")
                for idx, story in enumerate(stories_to_export, start=1):
                    file.write(f"{idx}. {story['title']}\n")
                    file.write(f"   Link: {story['link']}\n\n")

            LOG.info(f"\nSuccessfully exported {len(stories_to_export)} stories to {file_path}")
            return file_path
        except IOError as e:
            LOG.error(f"Error writing to file {file_path}: {e}")

