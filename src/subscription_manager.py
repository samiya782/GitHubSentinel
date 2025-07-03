import json
import os

class SubscriptionManager:
    def __init__(self, subscriptions_file):
        # 如果传入的是相对路径，将其转换为相对于项目根目录的绝对路径
        if not os.path.isabs(subscriptions_file):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.subscriptions_file = os.path.join(project_root, subscriptions_file)
        else:
            self.subscriptions_file = subscriptions_file

        self.subscriptions = self.load_subscriptions()
    
    def load_subscriptions(self):
        with open(self.subscriptions_file, 'r') as f:
            return json.load(f)
    
    def save_subscriptions(self):
        with open(self.subscriptions_file, 'w') as f:
            json.dump(self.subscriptions, f, indent=4)
    
    def get_subscriptions(self):
        return self.subscriptions
    
    def add_subscription(self, repo):
        if repo not in self.subscriptions:
            self.subscriptions.append(repo)
            self.save_subscriptions()
    
    def remove_subscription(self, repo):
        if repo in self.subscriptions:
            self.subscriptions.remove(repo)
            self.save_subscriptions()
