import gradio as gr  # 导入gradio库用于创建GUI

from config import Config  # 导入配置管理模块
from hacker_news_client import HackerNewsClient  # 导入用于GitHub API操作的客户端
from report_generator import ReportGenerator  # 导入报告生成器模块
from llm import LLM, ReportType  # 导入可能用于处理语言模型的LLM类
from subscription_manager import SubscriptionManager  # 导入订阅管理器
from pydantic import Field, validate_call
from typing import Annotated

# 创建各个组件的实例
config = Config()
llm = LLM(ReportType.HACKER_NEWS)
report_generator = ReportGenerator(llm)
subscription_manager = SubscriptionManager(config.subscriptions_file)

@validate_call
def export_daily_news(page: Annotated[int, Field(ge=30, le=300, multiple_of=30, description="Hacker News 新闻条数")]) -> tuple[str, str]:
    # 定义一个函数，用于导出和生成指定时间范围内项目的进展报告
    raw_file_path = HackerNewsClient.export_daily_news(page // 30)  # 导出原始数据文件路径
    report, report_file_path = report_generator.generate_daily_report(raw_file_path)  # 生成并获取报告内容及文件路径

    return report, report_file_path  # 返回报告内容和报告文件路径

# 创建Gradio界面
demo = gr.Interface(
    fn=export_daily_news,  # 指定界面调用的函数
    title="HackerNews",  # 设置界面标题
    inputs=[
        gr.Slider(value=30, minimum=30, maximum=300, step=30, label="News条数", info="Hacker News 新闻条数"),
        # 滑动条选择HackerNewsClient
    ],
    outputs=[gr.Markdown(), gr.File(label="下载报告")],  # 输出格式：Markdown文本和文件下载
)

if __name__ == "__main__":
    demo.launch()  # 启动界面并设置为公共可访问
    # 可选带有用户认证的启动方式
    # demo.launch(share=True, server_name="0.0.0.0", auth=("django", "1234"))