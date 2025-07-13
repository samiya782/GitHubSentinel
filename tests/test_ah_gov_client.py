import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call, mock_open
import sys
import os
from datetime import datetime

# Add the source directory to the Python path
# This assumes your test file is in a 'tests' directory and the client is in 'src'
# Adjust the path if your project structure is different
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the class to be tested
from ah_gov_client import AhGovClient


# Since the new class is async, we don't need a class-level patch for the browser.
# We will patch async methods and functions as needed within each test.

class TestAhGovClient(unittest.TestCase):

    def setUp(self):
        """
        This method runs before each test case.
        We prepare mock data that matches the new async implementation's output.
        """
        # The client is now safe to instantiate without side effects.
        self.client = AhGovClient()

        # Mock articles with the new data structure ('content' is Markdown, 'image_paths')
        self.mock_articles = [
            {
                'url': 'http://example.com/article1',
                'title': '安徽省发布重要通知',
                'content': '## 重要通知\n\n这是第一篇文章的内容。',
                'image_paths': ['http://example.com/img1.jpg', 'images/some_base64_img.png']
            },
            {
                'url': 'http://example.com/article2',
                'title': '合肥市发展新规划',
                'content': '### 新规划详情\n\n这是第二篇文章的内容。',
                'image_paths': []
            }
        ]

    def test_init_success(self):
        """
        Test Case: Client initialization.
        Verification: The client is instantiated with the correct default attributes.
        """
        # The new __init__ is simple and doesn't start any external processes.
        self.assertIsInstance(self.client, AhGovClient)
        self.assertEqual(self.client.output_dir, "ah_gov")
        self.assertIsNotNone(self.client.log)

    # We now test the public `export_articles` method by mocking the async pipeline it runs.
    # This is the most important test for the class's public API.
    @patch('ah_gov_client.AhGovClient._run_async_pipeline')
    @patch('ah_gov_client.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_articles_success(self, mock_open_func, mock_makedirs, mock_async_pipeline):
        """
        Test Case: Successfully exporting articles to a Markdown file.
        Strategy: Mock the entire async pipeline to control its output directly.
        """
        # Arrange: Configure the mock async pipeline to return our test articles.
        mock_async_pipeline.return_value = self.mock_articles

        # Act: Call the public export method.
        file_path = self.client.export_articles(date="2024-09-02")

        # Assert: Verify file system operations and the final result.
        expected_dir = os.path.join('ah_gov', '2024-09-02')
        expected_path = os.path.join(expected_dir, '2024-09-02_安徽省政府公开信息.md')

        mock_makedirs.assert_called_once_with(os.path.join(expected_dir, 'images'), exist_ok=True)
        mock_open_func.assert_called_once_with(expected_path, 'w', encoding='utf-8')
        self.assertEqual(file_path, expected_path)

        # Assert: Check the content written to the mock file.
        handle = mock_open_func()
        handle.write.assert_any_call("# 安徽省政府网站公开信息 (2024-09-02)\n\n")
        handle.write.assert_any_call(f"## 1. {self.mock_articles[0]['title']}\n\n")
        handle.write.assert_any_call(f"{self.mock_articles[0]['content']}\n\n")
        # Check that image paths are correctly formatted (using forward slashes)
        handle.write.assert_any_call("![Image](http://example.com/img1.jpg)\n")
        handle.write.assert_any_call("![Image](images/some_base64_img.png)\n")

    @patch('ah_gov_client.AhGovClient._run_async_pipeline')
    @patch('ah_gov_client.LOG.warning')
    def test_export_articles_no_articles_found(self, mock_log_warning, mock_async_pipeline):
        """
        Test Case: The async pipeline finds no articles.
        Verification: The method should log a warning and return None without creating files.
        """
        # Arrange: Mock the pipeline to return an empty list.
        mock_async_pipeline.return_value = []

        # Act
        file_path = self.client.export_articles()

        # Assert
        self.assertIsNone(file_path)
        mock_log_warning.assert_called_once_with("未找到任何可导出的文章。")

    @patch('ah_gov_client.AhGovClient._run_async_pipeline')
    @patch('ah_gov_client.LOG.error')
    def test_export_articles_pipeline_fails(self, mock_log_error, mock_async_pipeline):
        """
        Test Case: The async pipeline raises an exception during execution.
        Verification: The exception should be caught, logged, and the method should fail gracefully.
        """
        # Arrange: Mock the pipeline to raise an exception.
        mock_async_pipeline.side_effect = Exception("Network connection failed")

        # Act
        file_path = self.client.export_articles()

        # Assert
        self.assertIsNone(file_path)
        # We patch asyncio.run, which is what calls the pipeline.
        # The exception is caught in the `export_articles` method.
        # We need to find the correct patch target for asyncio.run
        # A better way is to patch the pipeline itself, which is what we did.
        # The try-except block in export_articles will catch this.
        # Let's re-check the source code. `articles = asyncio.run(...)`
        # Ah, the `asyncio.run` is what we need to patch to simulate the exception.
        # Let's correct this test.

        # Re-arranging the test for better accuracy
        with patch('ah_gov_client.asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.side_effect = Exception("Async pipeline crashed")

            # Act
            file_path = self.client.export_articles()

            # Assert
            self.assertIsNone(file_path)
            mock_log_error.assert_called_with("异步爬取流程发生严重错误: Async pipeline crashed")

    # The following is a more advanced test for the internal async method itself.
    # It requires the test method to be async.
    @patch('ah_gov_client.httpx.AsyncClient')
    async def test_internal_get_article_urls(self, MockAsyncClient):
        """
        Test Case: Test the internal `_get_article_urls` async method.
        Strategy: Use `AsyncMock` to simulate the async httpx client.
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.text = '<html><body><a class="tit" href="/page1.html">Title 1</a></body></html>'
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        # Configure the class-level mock to return our instance when used as a context manager
        MockAsyncClient.return_value.__aenter__.return_value = mock_client_instance

        # Act
        urls = await self.client._get_article_urls(
            "http://base.url", "a.tit", mock_client_instance
        )

        # Assert
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], "http://base.url/page1.html")
        mock_client_instance.get.assert_awaited_once_with("http://base.url", timeout=20)


if __name__ == '__main__':
    # To run async tests, unittest needs a bit of help.
    # For modern Python (3.8+), unittest.main() can discover and run async tests automatically.
    unittest.main()
