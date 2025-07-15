"""
Gradio前端界面
集成了GitHub/HackerNews/安徽政务报告生成器 和 可动态加载知识库与模型的多模态聊天机器人的统一仪表盘
"""
import gradio as gr
import uuid
import os
import inspect

# --- 统一导入 ---
# 聊天机器人相关
from reflect_chat_bot import ChatBot
# 报告生成器相关
from github_client import GitHubClient
from hacker_news_client import HackerNewsClient
from ah_gov_client import AhGovClient
from report_generator import ReportGenerator
from llm import LLM
from subscription_manager import SubscriptionManager
# 通用
from config import Config
from logger import LOG

# --- 统一初始化 ---

# 1. 初始化通用配置和报告生成器组件
try:
    config = Config()
    github_client = GitHubClient(config.github_token)
    hacker_news_client = HackerNewsClient()
    ah_gov_client = AhGovClient()
    subscription_manager = SubscriptionManager(config.subscriptions_file)
    LOG.info("Config和报告生成器客户端初始化成功")
except Exception as e:
    LOG.error(f"核心组件初始化失败: {e}")
    print(f"核心组件初始化失败: {e}")
    exit()

# ChatBot不再在此处初始化，将由用户在UI中触发

# --- 报告生成器功能函数 ---

def generate_github_report(model_type, model_name, repo, days):
    config.llm_model_type = model_type
    if model_type == "openai": config.openai_model_name = model_name
    elif model_type == "ollama": config.ollama_model_name = model_name
    elif model_type == "gemini": config.gemini_model_name = model_name
    else: raise ValueError(f"不支持的模型类型: {model_type}")
    llm = LLM(config)
    report_generator = ReportGenerator(llm, config.report_types)
    raw_file_path = github_client.export_progress_by_date_range(repo, days)
    report, report_file_path = report_generator.generate_github_report(raw_file_path)
    return report, report_file_path

def generate_hn_hour_topic(model_type, model_name):
    config.llm_model_type = model_type
    if model_type == "openai": config.openai_model_name = model_name
    elif model_type == "ollama": config.ollama_model_name = model_name
    elif model_type == "gemini": config.gemini_model_name = model_name
    else: raise ValueError(f"不支持的模型类型: {model_type}")
    llm = LLM(config)
    report_generator = ReportGenerator(llm, config.report_types)
    markdown_file_path = hacker_news_client.export_top_stories()
    report, report_file_path = report_generator.generate_hn_topic_report(markdown_file_path)
    return report, report_file_path

def generate_ah_gov_report(model_type, model_name):
    config.llm_model_type = model_type
    if model_type == "openai": config.openai_model_name = model_name
    elif model_type == "ollama": config.ollama_model_name = model_name
    elif model_type == "gemini": config.gemini_model_name = model_name
    else: raise ValueError(f"不支持的模型类型: {model_type}")
    llm = LLM(config)
    report_generator = ReportGenerator(llm, config.report_types)
    markdown_file_path = ah_gov_client.export_articles()
    report, report_file_path = report_generator.generate_ah_gov_daily_report(markdown_file_path)
    return report, report_file_path

def update_model_list(model_type):
    if model_type == "openai":
        return gr.Dropdown(choices=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"], value="gpt-4o-mini", label="选择模型")
    elif model_type == "ollama":
        return gr.Dropdown(choices=["llama3.1", "gemma2:2b", "qwen2:7b"], value="llama3.1", label="选择模型")
    elif model_type == "gemini":
        return gr.Dropdown(choices=["gemini-2.5-flash", "gemini-2.5-pro"], value="gemini-2.5-flash", label="选择模型")
    return None

# --- 聊天机器人功能函数 ---

session_store = {}

def create_session():
    session_id = f"session_{uuid.uuid4()}"
    session_store[session_id] = []
    return session_id

def initialize_chatbot(db_path, model_type, model_name):
    """根据用户提供的路径和模型选择，初始化ChatBot实例"""
    if not db_path or not os.path.exists(db_path):
        error_msg = f"❌ 错误：知识库路径不存在或为空 '{db_path}'"
        LOG.error(error_msg)
        return error_msg, None, False, gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False)

    try:
        LOG.info(f"配置更新：模型类型='{model_type}', 模型名称='{model_name}'")
        config.llm_model_type = model_type
        if model_type == "openai": config.openai_model_name = model_name
        elif model_type == "ollama": config.ollama_model_name = model_name
        elif model_type == "gemini": config.gemini_model_name = model_name

        LOG.info(f"尝试使用路径 '{db_path}' 和模型 '{model_name}' 初始化ChatBot...")
        chatbot_instance = ChatBot(config, db_path=db_path)
        invoke_signature = inspect.signature(chatbot_instance.invoke)
        supports_multimodal = 'images' in invoke_signature.parameters
        LOG.info(f"ChatBot初始化成功。多模态支持: {supports_multimodal}")

        success_msg = (f"✅ **加载成功!**\n"
                       f"- **知识库:** `{db_path}`\n"
                       f"- **模型:** `{model_name}`\n"
                       f"- **多模态:** `{'支持' if supports_multimodal else '不支持'}`")

        return success_msg, chatbot_instance, supports_multimodal, gr.update(interactive=True), gr.update(interactive=True), gr.update(interactive=True), gr.update(interactive=True)

    except Exception as e:
        error_msg = f"❌ **ChatBot初始化失败:**\n`{e}`"
        LOG.error(error_msg, exc_info=True)
        return error_msg, None, False, gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False)


def chat_interface(message, images, audio, history, session_id, chatbot_instance, supports_multimodal):
    """处理用户输入并返回响应"""
    if not chatbot_instance:
        history = history or []
        history.append({"role": "user", "content": message or "多模态输入"})
        history.append({"role": "assistant", "content": "❌ **错误：** 聊天机器人未初始化。请先在左侧配置并加载知识库和模型。"})
        return history, "", None, None, session_id

    try:
        if not session_id: session_id = create_session()
        final_question = message if message else ""
        if audio and hasattr(chatbot_instance, 'process_audio'):
            try:
                audio_text = chatbot_instance.process_audio(audio)
                if audio_text:
                    LOG.info(f"语音识别结果: {audio_text}")
                    final_question = f"{final_question}\n（语音补充：{audio_text}）" if final_question else audio_text
            except Exception as e: LOG.error(f"音频处理失败: {e}")

        if not final_question and images: final_question = "请分析这些图片的内容"
        if not final_question: return history, "", None, None, session_id

        if supports_multimodal:
            response = chatbot_instance.invoke(question=final_question, thread_id=session_id, images=images or None)
        else:
            if images: final_question += f"\n[用户上传了{len(images)}张图片]"
            response = chatbot_instance.invoke(final_question, session_id)

        history = history or []
        user_msg = message if message else "（多模态输入）"
        if images: user_msg += f"\n📷 包含{len(images)}张图片"
        if audio: user_msg += "\n🎤 包含语音输入"
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})
        return history, "", None, None, session_id

    except Exception as e:
        LOG.error(f"处理请求时出错: {e}", exc_info=True)
        error_msg = f"抱歉，处理您的请求时出现错误：{str(e)}"
        history = (history or []) + [{"role": "user", "content": message or "多模态输入"}, {"role": "assistant", "content": error_msg}]
        return history, "", None, None, session_id

def clear_chat_session():
    new_session_id = create_session()
    return [], "", None, None, new_session_id, f"新会话已创建: {new_session_id}"


# --- 创建Gradio界面 ---
with gr.Blocks(title="智能信息平台", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 智能信息分析与对话平台")

    # --- Tab 1: 安徽政务智能助手 ---
    with gr.Tab("安徽政务智能助手 (多模态对话)"):
        chatbot_state = gr.State(None)
        multimodal_state = gr.State(False)
        chat_session_id = gr.State("")

        gr.Markdown("## 🤖 安徽政务智能助手")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ❶ 配置并加载")
                db_path_input = gr.Textbox(label="知识库路径 (ChromaDB)", placeholder=r"例如: D:\path\to\chroma_db", value=r"D:\Python\PythonProject\GitHubSentinel\ah_gov\2025-07-14\chroma_db")
                chat_model_type = gr.Radio(["gemini", "openai", "ollama"], value="gemini", label="模型类型", info="选择用于对话的LLM")
                chat_model_name = gr.Dropdown(choices=["gemini-2.5-flash", "gemini-2.5-pro"], value="gemini-2.5-flash", label="选择模型")
                init_chatbot_btn = gr.Button("✅ 加载知识库与模型", variant="primary")
                chatbot_status_display = gr.Markdown("请加载知识库以开始...")

                gr.Markdown("---")
                gr.Markdown("### ❷ 对话输入")
                chat_session_info = gr.Textbox(label="会话信息", value="会话未开始", interactive=False)
                chat_text_input = gr.Textbox(label="文字输入", placeholder="请先加载知识库...", lines=3, interactive=False)
                chat_image_input = gr.File(label="图片上传", file_count="multiple", file_types=["image"], type="filepath", interactive=False)
                chat_audio_input = gr.Audio(label="语音输入", sources=["microphone", "upload"], type="filepath", interactive=False)
                with gr.Row():
                    chat_submit_btn = gr.Button("🚀 发送", variant="primary", scale=2, interactive=False)
                    chat_clear_btn = gr.Button("🔄 新建会话", scale=1)

            with gr.Column(scale=2):
                gr.Markdown("### ❸ 对话历史")
                chatbot_display = gr.Chatbot(height=600, type="messages", avatar_images=(None, "🤖"), label="对话窗口")

        # 绑定事件
        chat_model_type.change(fn=update_model_list, inputs=chat_model_type, outputs=chat_model_name)

        init_chatbot_btn.click(
            fn=initialize_chatbot,
            inputs=[db_path_input, chat_model_type, chat_model_name],
            outputs=[chatbot_status_display, chatbot_state, multimodal_state, chat_text_input, chat_image_input, chat_audio_input, chat_submit_btn]
        )

        chat_submit_btn.click(
            fn=chat_interface,
            inputs=[chat_text_input, chat_image_input, chat_audio_input, chatbot_display, chat_session_id, chatbot_state, multimodal_state],
            outputs=[chatbot_display, chat_text_input, chat_image_input, chat_audio_input, chat_session_id]
        )

        chat_clear_btn.click(
            fn=clear_chat_session,
            outputs=[chatbot_display, chat_text_input, chat_image_input, chat_audio_input, chat_session_id, chat_session_info]
        )

    # --- 其他Tabs (报告生成器) ---
    with gr.Tab("GitHub 项目进展"):
        gr.Markdown("## 跟踪分析 GitHub 项目的最新进展")
        with gr.Row():
            with gr.Column(scale=1):
                gh_model_type = gr.Radio(["gemini", "openai", "ollama"], value="gemini", label="模型类型", info="选择用于分析的LLM")
                gh_model_name = gr.Dropdown(choices=["gemini-2.5-flash", "gemini-2.5-pro"], value="gemini-2.5-flash", label="选择模型")
                gh_subscription_list = gr.Dropdown(subscription_manager.list_subscriptions(), label="订阅列表", info="已订阅GitHub项目")
                gh_days = gr.Slider(value=2, minimum=1, maximum=7, step=1, label="报告周期", info="单位：天")
                gh_button = gr.Button("生成报告", variant="primary")
                gh_model_type.change(fn=update_model_list, inputs=gh_model_type, outputs=gh_model_name)
            with gr.Column(scale=2):
                gh_markdown_output = gr.Markdown(label="分析报告")
                gh_file_output = gr.File(label="下载报告")
        gh_button.click(generate_github_report, inputs=[gh_model_type, gh_model_name, gh_subscription_list, gh_days], outputs=[gh_markdown_output, gh_file_output])

    with gr.Tab("Hacker News 热点话题"):
        gr.Markdown("## 洞察 Hacker News 的最新技术热点")
        with gr.Row():
            with gr.Column(scale=1):
                hn_model_type = gr.Radio(["gemini", "openai", "ollama"], value="gemini", label="模型类型", info="选择用于分析的LLM")
                hn_model_name = gr.Dropdown(choices=["gemini-2.5-flash", "gemini-2.5-pro"], value="gemini-2.5-flash", label="选择模型")
                hn_button = gr.Button("生成最新热点话题", variant="primary")
                hn_model_type.change(fn=update_model_list, inputs=hn_model_type, outputs=hn_model_name)
            with gr.Column(scale=2):
                hn_markdown_output = gr.Markdown(label="分析报告")
                hn_file_output = gr.File(label="下载报告")
        hn_button.click(generate_hn_hour_topic, inputs=[hn_model_type, hn_model_name], outputs=[hn_markdown_output, hn_file_output])

    with gr.Tab("安徽政府商机分析 (报告)"):
        gr.Markdown("## 每日速览安徽省政府公开信息，挖掘潜在商机")
        with gr.Row():
            with gr.Column(scale=1):
                ah_model_type = gr.Radio(["gemini", "openai", "ollama"], value="gemini", label="模型类型", info="选择用于分析的LLM")
                ah_model_name = gr.Dropdown(choices=["gemini-2.5-flash", "gemini-2.5-pro"], value="gemini-2.5-flash", label="选择模型")
                ah_button = gr.Button("生成最新商机分析", variant="primary")
                ah_model_type.change(fn=update_model_list, inputs=ah_model_type, outputs=ah_model_name)
            with gr.Column(scale=2):
                ah_markdown_output = gr.Markdown(label="分析报告")
                ah_file_output = gr.File(label="下载报告")
        ah_button.click(generate_ah_gov_report, inputs=[ah_model_type, ah_model_name], outputs=[ah_markdown_output, ah_file_output])


# --- 启动应用 ---
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
