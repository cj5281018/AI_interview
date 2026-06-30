"""
ProView AI Interviewer — 简化版 (Streamlit)

本地优先的 AI 模拟面试工具，支持 DeepSeek 和阿里云通义千问。

运行方式:
    streamlit run app.py

或:
    python -m streamlit run app.py
"""
import sys
import streamlit as st

# 确保项目根目录在 Python 路径中
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from core.storage import InterviewStorage

# ── 页面配置 ──
st.set_page_config(
    page_title="ProView AI Interviewer",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── 全局样式 ──
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .stChatMessage { padding: 1rem; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── 初始化全局服务 ──
@st.cache_resource
def get_storage() -> InterviewStorage:
    """获取存储实例（单例，跨会话缓存）"""
    return InterviewStorage(str(config.DB_PATH))


def main():
    """应用主入口"""
    storage = get_storage()

    # ── 侧边栏导航 ──
    with st.sidebar:
        st.title("🎤 ProView AI")
        st.caption("AI 模拟面试官")

        st.markdown("---")

        # 导航
        nav_options = {
            "home": "🏠 首页",
            "interview": "🎤 开始面试",
            "resume": "📄 简历管理",
            "report": "📊 评估报告",
            "career": "🧭 职业规划",
            "settings": "⚙️ 设置",
        }

        # 读取当前页面（从 session_state 或 radio）
        current_page = st.session_state.get("nav_page", "home")

        selected = st.radio(
            "导航",
            list(nav_options.keys()),
            format_func=lambda x: nav_options[x],
            index=list(nav_options.keys()).index(current_page),
            label_visibility="collapsed",
        )

        # 检测页面切换
        if selected != current_page:
            st.session_state["nav_page"] = selected
            current_page = selected

        st.markdown("---")
        st.caption(f"v0.1.0 | 本地数据存储")

    # ── 路由到对应页面 ──
    if current_page == "home":
        from ui.home import render
        render(storage)
    elif current_page == "interview":
        from ui.interview import render
        render(storage)
    elif current_page == "resume":
        from ui.resume import render
        render(storage)
    elif current_page == "report":
        from ui.report import render
        render(storage)
    elif current_page == "career":
        from ui.career import render
        render(storage)
    elif current_page == "settings":
        from ui.settings import render
        render()


if __name__ == "__main__":
    main()
