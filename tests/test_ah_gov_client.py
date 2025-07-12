import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import sys
import os
from datetime import datetime

# 将 src 目录添加到模块搜索路径，以便测试代码可以导入 src 目录中的模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# 导入需要被测试的类
from ah_gov_client import AhGovClient
# 导入 Selenium 的异常类，以便在测试中模拟它
from selenium.common.exceptions import TimeoutException


# 这是一个类装饰器。由于 AhGovClient 在 __init__ 方法中就会启动浏览器，
# 我们需要对整个测试类应用 patch，以防止任何测试用例意外地启动真实浏览器。
# 它会将 'ah_gov_client.webdriver.Edge' 替换为一个 MagicMock 对象。
@patch('ah_gov_client.webdriver.Edge')
class TestAhGovClient(unittest.TestCase):

    def setUp(self):
        """
        这个方法在每个测试用例运行前都会被执行。
        我们在这里准备一些通用的模拟数据。
        """
        # 模拟 fetch_articles 方法成功时应该返回的文章数据
        self.mock_articles = [
            {
                'url': 'http://example.com/article1',
                'title': '安徽省发布重要通知',
                'content': '这是第一篇文章的内容。',
                'images': ['http://example.com/img1.jpg']
            },
            {
                'url': 'http://example.com/article2',
                'title': '合肥市发展新规划',
                'content': '这是第二篇文章的内容。',
                'images': []
            }
        ]

    def test_init_success(self, mock_webdriver_edge):
        """
        测试场景：客户端初始化成功。
        验证它是否正确地尝试启动了浏览器。
        """
        # 'mock_webdriver_edge' 参数由类装饰器 @patch 传入
        client = AhGovClient()
        # 断言：webdriver.Edge 这个类被调用过一次，意味着代码尝试了启动浏览器
        mock_webdriver_edge.assert_called_once()
        # 断言：客户端实例的 driver 属性不为空，已被赋值
        self.assertIsNotNone(client.driver)

    @patch('ah_gov_client.LOG.error')
    def test_init_failure(self, mock_log_error, mock_webdriver_edge):
        """
        测试场景：浏览器启动过程中发生异常。
        验证错误是否被正确记录，并且异常被抛出。
        """
        # 准备：让模拟的 webdriver.Edge 在实例化时抛出异常
        mock_webdriver_edge.side_effect = Exception("浏览器驱动未找到")

        # 执行与断言：确认在创建 AhGovClient 实例时会抛出异常
        with self.assertRaises(Exception):
            AhGovClient()

        # 断言：检查 LOG.error 是否以预期的错误信息被调用
        mock_log_error.assert_called_with("浏览器启动失败: 浏览器驱动未找到")

    @patch('ah_gov_client.AhGovClient._extract_article_data')
    @patch('ah_gov_client.AhGovClient._get_article_urls')
    def test_fetch_articles_success(self, mock_get_urls, mock_extract_data, mock_webdriver_edge):
        """
        测试场景：测试核心的 fetch_articles 编排方法。
        我们通过模拟它的两个辅助方法来独立测试其自身的逻辑。
        """
        # 准备：配置各个模拟对象的返回值
        mock_get_urls.return_value = ['http://example.com/article1', 'http://example.com/article2']
        # 使用 side_effect 可以让 mock_extract_data 每次被调用时返回不同的值
        mock_extract_data.side_effect = self.mock_articles

        # 执行：调用被测试的方法
        client = AhGovClient()
        articles = client.fetch_articles()

        # 断言：检查返回结果和模拟对象的调用情况
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['title'], '安徽省发布重要通知')
        # 确认 _get_article_urls 被调用了一次
        mock_get_urls.assert_called_once()
        # 确认 _extract_article_data 为每个URL都被调用了一次
        self.assertEqual(mock_extract_data.call_count, 2)
        # 更精确地检查 _extract_article_data 的调用参数
        mock_extract_data.assert_has_calls([
            call('http://example.com/article1', '#container > div.container'),
            call('http://example.com/article2', '#container > div.container')
        ])

    @patch('ah_gov_client.AhGovClient._extract_article_data', return_value=None)
    @patch('ah_gov_client.AhGovClient._get_article_urls')
    @patch('ah_gov_client.LOG.error')
    def test_fetch_articles_extraction_fails(self, mock_log_error, mock_get_urls, mock_extract_data,
                                             mock_webdriver_edge):
        """
        测试场景：当 _extract_article_data 方法提取失败时，程序能优雅地处理。
        """
        # 准备：模拟获取到一个URL，但在提取时发生异常
        mock_get_urls.return_value = ['http://example.com/bad_article']
        mock_extract_data.side_effect = Exception("提取失败")

        client = AhGovClient()
        articles = client.fetch_articles()

        # 断言：文章列表应为空，因为唯一的一篇文章提取失败了
        self.assertEqual(len(articles), 0)
        # 断言：记录了相应的错误日志
        mock_log_error.assert_called_with("提取文章内容时出错: http://example.com/bad_article - 提取失败")

    @patch('ah_gov_client.os.makedirs')
    @patch('ah_gov_client.open', new_callable=mock_open)
    @patch('ah_gov_client.AhGovClient.fetch_articles')
    def test_export_articles_success(self, mock_fetch_articles, mock_open_func, mock_makedirs, mock_webdriver_edge):
        """
        测试场景：成功将获取到的文章导出为 Markdown 文件。
        """
        # 准备：模拟 fetch_articles 方法，让它直接返回我们的测试数据
        mock_fetch_articles.return_value = self.mock_articles

        # 执行：调用导出方法
        client = AhGovClient()
        file_path = client.export_articles(date="2024-09-02")

        # 断言：检查文件和目录操作是否符合预期
        expected_dir = os.path.join('ah_gov', '2024-09-02')
        expected_path = os.path.join(expected_dir, '2024-09-02.md')

        mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)
        mock_open_func.assert_called_once_with(expected_path, 'w')
        self.assertEqual(file_path, expected_path)

        # 断言：检查写入文件的内容是否正确
        handle = mock_open_func()  # 获取文件句柄的模拟对象
        handle.write.assert_any_call("# 安徽政府网站最新文件 (2024-09-02)\n\n")
        handle.write.assert_any_call("---\n\n## 1. [安徽省发布重要通知](http://example.com/article1)\n\n")
        handle.write.assert_any_call("这是第一篇文章的内容。\n\n")
        handle.write.assert_any_call("![Image](http://example.com/img1.jpg)\n")

    @patch('ah_gov_client.LOG.warning')
    @patch('ah_gov_client.os.makedirs')
    @patch('ah_gov_client.open', new_callable=mock_open)
    @patch('ah_gov_client.AhGovClient.fetch_articles')
    def test_export_articles_no_articles_found(self, mock_fetch, mock_open_func, mock_makedirs, mock_log_warning,
                                               mock_webdriver_edge):
        """
        测试场景：当没有获取到任何文章时，程序的行为。
        """
        # 准备：模拟 fetch_articles 返回一个空列表
        mock_fetch.return_value = []

        # 执行
        client = AhGovClient()
        file_path = client.export_articles()

        # 断言
        self.assertIsNone(file_path)  # 确认返回值为 None
        mock_log_warning.assert_called_once_with("未找到任何安徽政府的最新文章。")
        # 确认没有进行任何文件或目录的创建操作
        mock_makedirs.assert_not_called()
        mock_open_func.assert_not_called()


if __name__ == '__main__':
    # 这样可以在不使用测试运行器的情况下直接运行此脚本
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
