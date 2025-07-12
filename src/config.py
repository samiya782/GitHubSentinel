import json
import os
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
CONFIG_JSON_PATH = project_root / "config.json"

class Config:
    def __init__(self):
        load_dotenv()
        self.load_config()
    
    def load_config(self):
        with open(CONFIG_JSON_PATH, 'r') as f:
            config = json.load(f)
            
            self.email = config.get('email', {})
            self.email['password'] = os.getenv('EMAIL_PASSWORD', self.email.get('password', ''))

            # 加载 GitHub 相关配置
            github_config = config.get('github', {})
            self.github_token = os.getenv('GITHUB_TOKEN', github_config.get('token'))
            self.subscriptions_file = project_root / github_config.get('subscriptions_file')
            self.freq_days = github_config.get('progress_frequency_days', 1)
            self.exec_time = github_config.get('progress_execution_time', "08:00")

            # 加载 LLM 相关配置
            llm_config = config.get('llm', {})
            self.llm_model_type = llm_config.get('model_type', 'gemini')
            self.openai_model_name = llm_config.get('openai_model_name', 'gpt-4o-mini')
            self.ollama_model_name = llm_config.get('ollama_model_name', 'llama3')
            self.gemini_model_name = llm_config.get('gemini_model_name', 'gemini-2.5-flash')
            self.ollama_api_url = llm_config.get('ollama_api_url', 'http://localhost:11434/api/chat')
            
            # 加载报告类型配置
            self.report_types = config.get('report_types', ["github", "hacker_news", "ah_gov"])  # 默认报告类型
            
            # 加载 Slack 配置
            slack_config = config.get('slack', {})
            self.slack_webhook_url = slack_config.get('webhook_url')
