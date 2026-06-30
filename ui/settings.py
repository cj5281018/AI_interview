"""
设置页 — API Key 配置

配置 DeepSeek 和阿里云通义千问的 API Key。
"""
import streamlit as st
import config
from core.model_registry import init_providers, list_available_providers


def render():
    """渲染设置页"""
    st.title("⚙️ 设置")
    st.caption("配置 LLM API Key 以启用 AI 面试功能")

    # ── LLM 配置 ──
    st.subheader("🔑 LLM 模型配置")

    st.markdown("至少配置一个提供商的 API Key 即可使用。")

    # DeepSeek
    st.markdown("### DeepSeek")
    col1, col2 = st.columns([3, 1])
    with col1:
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            value=config.DEEPSEEK_API_KEY,
            type="password",
            placeholder="sk-...",
            key="deepseek_key_input",
        )
    with col2:
        deepseek_url = st.text_input(
            "Base URL",
            value=config.DEEPSEEK_BASE_URL,
            placeholder="https://api.deepseek.com/v1",
            key="deepseek_url_input",
        )

    # 阿里云
    st.markdown("### 阿里云通义千问")
    col1, col2 = st.columns([3, 1])
    with col1:
        aliyun_key = st.text_input(
            "阿里云 API Key",
            value=config.ALIYUN_API_KEY,
            type="password",
            placeholder="sk-...",
            key="aliyun_key_input",
        )
    with col2:
        aliyun_url = st.text_input(
            "Base URL",
            value=config.ALIYUN_BASE_URL,
            placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1",
            key="aliyun_url_input",
        )

    # ── 保存 ──
    if st.button("💾 保存配置", type="primary", use_container_width=True):
        _save_env(
            DEEPSEEK_API_KEY=deepseek_key,
            DEEPSEEK_BASE_URL=deepseek_url,
            ALIYUN_API_KEY=aliyun_key,
            ALIYUN_BASE_URL=aliyun_url,
        )
        # 重新加载
        from dotenv import load_dotenv
        load_dotenv(config.BASE_DIR / ".env", override=True)
        init_providers()
        st.success("✅ 配置已保存！")
        st.rerun()

    # ── 当前状态 ──
    st.markdown("---")
    st.subheader("📡 当前状态")
    providers = list_available_providers()
    for p in providers:
        status = "✅ 已配置" if p["available"] else "❌ 未配置"
        st.text(f"{p['label']} ({p['model']}): {status}")

    # ── 获取密钥指引 ──
    st.markdown("---")
    st.subheader("📖 如何获取 API Key？")
    with st.expander("DeepSeek"):
        st.markdown("""
        1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
        2. 注册/登录账号
        3. 在「API Keys」页面创建新 Key
        4. 复制 Key 到上方的输入框
        """)
    with st.expander("阿里云通义千问"):
        st.markdown("""
        1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
        2. 注册/登录阿里云账号
        3. 在「模型服务」→「API Key」中创建新 Key
        4. 复制 Key 到上方的输入框
        """)


def _save_env(**kwargs):
    """保存配置到 .env 文件"""
    env_path = config.BASE_DIR / ".env"

    # 读取现有内容
    existing = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    existing[key.strip()] = value.strip()

    # 合并新值
    existing.update(kwargs)

    # 写入
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# ProView AI Interviewer 配置文件\n")
        f.write("# 此文件由应用自动生成，也可手动编辑\n\n")
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    # 更新内存中的配置
    for k, v in kwargs.items():
        setattr(config, k, v)
