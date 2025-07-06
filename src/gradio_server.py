import gradio as gr  # 导入gradio库用于创建GUI

from config import Config  # 导入配置管理模块
from github_client import GitHubClient  # 导入用于GitHub API操作的客户端
from report_generator import ReportGenerator  # 导入报告生成器模块
from llm import LLM  # 导入可能用于处理语言模型的LLM类
from subscription_manager import SubscriptionManager  # 导入订阅管理器
from logger import LOG  # 导入日志记录器

# 创建各个组件的实例
config = Config()
github_client = GitHubClient(config.github_token)
llm = LLM()
report_generator = ReportGenerator(llm)
subscription_manager = SubscriptionManager(config.subscriptions_file)

# 修改前的函数
# def export_progress_by_date_range(repo, days):
#     raw_file_path = github_client.export_progress_by_date_range(repo, days)
#     report, report_file_path = report_generator.generate_report_by_date_range(raw_file_path, days)
#     return report, report_file_path

# 修改后的函数
def export_progress_by_date_range(repo, days):
    # 1. 导出和生成报告（这部分逻辑不变）
    raw_file_path = github_client.export_progress_by_date_range(repo, days)
    report, report_file_path = report_generator.generate_report_by_date_range(raw_file_path, days)

    # 2. 检查报告是否成功生成
    if report and report_file_path:
        # 如果成功，返回 update 对象，设置值并设为可见
        return (
            gr.update(value=report, visible=True),
            gr.update(value=report_file_path, visible=True)
        )
    else:
        # 如果失败或为空，可以返回一个提示信息，或者保持隐藏
        # 这里我们选择显示一个错误信息，但只在 Markdown 组件中，文件组件保持隐藏
        error_message = "抱歉，未能生成报告。请检查输入或稍后再试。"
        return (
            gr.update(value=error_message, visible=True),
            gr.update(visible=False) # 确保文件组件保持隐藏
        )


# # 创建Gradio界面
# demo = gr.Interface(
#     fn=export_progress_by_date_range,  # 指定界面调用的函数
#     title="GitHubSentinel",  # 设置界面标题
#     inputs=[
#         gr.Dropdown(
#             subscription_manager.list_subscriptions(), label="订阅列表", info="已订阅GitHub项目"
#         ),  # 下拉菜单选择订阅的GitHub项目
#         gr.Slider(value=2, minimum=1, maximum=7, step=1, label="报告周期", info="生成项目过去一段时间进展，单位：天"),
#         # 滑动条选择报告的时间范围
#     ],
#     outputs=[gr.Markdown(), gr.File(label="下载报告")],  # 输出格式：Markdown文本和文件下载
# )
custom_css = """
.row-flex-start {
    align-items: flex-start !important; /* !important 确保覆盖默认样式 */
}

"""
# 使用 gr.Blocks 创建界面
with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:
    gr.Markdown("# GitHubSentinel 订阅管理与报告生成")

    # --- 区域1: 订阅管理 ---
    with gr.Accordion("管理我的订阅", open=False):  # 使用可折叠区域，让界面更整洁
        repo_to_manage = gr.Textbox(
            label="输入GitHub仓库地址",
            placeholder="例如: microsoft/vscode",
            scale=4  # 占据更多空间
        )
        with gr.Row():
            add_button = gr.Button("添加订阅")
            remove_button = gr.Button("移除订阅")

    # --- 区域2: 报告生成 (你原来的核心功能) ---
    gr.Markdown("## 生成项目进展报告")

    with gr.Row(elem_classes=['row-flex-start']):
        # 这是我们要动态更新的关键组件！
        with gr.Column(scale=3):
            repo_dropdown = gr.Dropdown(
                choices=subscription_manager.list_subscriptions(),
                label="订阅列表",
                info="从已订阅的GitHub项目中选择"
            )
            days_slider = gr.Slider(
                value=2, minimum=1, maximum=7, step=1,
                label="报告周期",
                info="生成项目过去一段时间进展，单位：天"
            )

            generate_button = gr.Button("🚀 生成报告", variant="primary")

        with gr.Column(scale=5):
            # 修改前
            # report_output = gr.Markdown(label="报告预览")
            # file_output = gr.File(label="下载报告")

            # 修改后
            report_output = gr.Markdown(label="报告预览")
            file_output = gr.File(label="下载报告")


    # --- 事件处理逻辑 ---

    # 定义添加订阅的函数
    def add_subscription_and_update(repo_name):
        message = subscription_manager.add_subscription(repo_name)
        # 关键！返回一个 update 对象来更新 Dropdown 的选项
        # 同时更新状态文本框
        return (
            gr.update(choices=subscription_manager.list_subscriptions())
        )


    # 定义移除订阅的函数
    def remove_subscription_and_update(repo_name):
        message = subscription_manager.remove_subscription(repo_name)
        # 同样返回 update 对象
        return (
            gr.update(choices=subscription_manager.list_subscriptions())
        )


    # 绑定事件：将按钮点击与函数关联起来
    add_button.click(
        fn=add_subscription_and_update,
        inputs=[repo_to_manage],
        outputs=[repo_dropdown]  # 指定要更新的组件
    )

    remove_button.click(
        fn=remove_subscription_and_update,
        inputs=[repo_to_manage],
        outputs=[repo_dropdown]
    )

    # 绑定报告生成按钮的事件 (这部分和你原来类似)
    generate_button.click(
        fn=export_progress_by_date_range,
        inputs=[repo_dropdown, days_slider],
        outputs=[report_output, file_output]
    )

if __name__ == "__main__":
    demo.launch()  # 启动界面并设置为公共可访问
    # 可选带有用户认证的启动方式
    # demo.launch(share=True, server_name="0.0.0.0", auth=("django", "1234"))