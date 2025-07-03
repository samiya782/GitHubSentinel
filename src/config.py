import json
import os

class Config:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        # 获取项目根目录路径（src的上级目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.github_token = config.get('github_token')
            self.notification_settings = config.get('notification_settings')
            self.subscriptions_file = config.get('subscriptions_file')
            self.update_interval = config.get('update_interval', 24 * 60 * 60)  # Default to 24 hours
