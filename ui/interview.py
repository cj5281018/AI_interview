"""
面试页 — 核心面试交互界面

参照原项目 SetupView + InterviewView 的设计，在 Streamlit 中合并为：
- 侧边栏：面试预设卡片 + 精调参数 + 简历选择 + 岗位输入
- 主区域：流式聊天界面 + 思维链折叠展示
"""
import uuid
import streamlit as st
from core.storage import InterviewStorage
from core.interview_agent import InterviewAgent
from core.model_registry import get_provider, list_available_providers
from services.resume_parser import summarize_resume, get_resume_preview

# ═══════════════════════════════════════════════════════════════
# 面试预设卡片（参照原项目 SetupView 的 6 个 preset）
# ═══════════════════════════════════════════════════════════════
INTERVIEW_PRESETS = [
    {
        "id": "warmup",
        "emoji": "🧊",
        "label": "轻压热身局",
        "desc": "温和引导建立节奏，适合刚开始练习表达和破冰。",
        "focus": "技术面 · 初级",
        "rhythm": "引导式追问",
        "interview_type": "technical",
        "difficulty": "junior",
        "style": "friendly",
    },
    {
        "id": "deep-dive",
        "emoji": "🚀",
        "label": "技术深挖局",
        "desc": "围绕原理、实现细节和项目拆解追问，强调真实技术深度。",
        "focus": "技术面 · 中级",
        "rhythm": "连续下钻",
        "interview_type": "technical",
        "difficulty": "mid",
        "style": "technical_deep",
    },
    {
        "id": "salary",
        "emoji": "💰",
        "label": "谈薪练习局",
        "desc": "围绕薪资、涨幅空间、福利结构和 offer 预期进行表达训练。",
        "focus": "HR面 · 中级",
        "rhythm": "谈判表达",
        "interview_type": "hr",
        "difficulty": "mid",
        "style": "behavioral",
    },
    {
        "id": "system",
        "emoji": "🏗️",
        "label": "系统设计局",
        "desc": "高阶架构与取舍场景，考查方案能力和系统化表达。",
        "focus": "技术面 · 高级",
        "rhythm": "架构权衡",
        "interview_type": "technical",
        "difficulty": "senior",
        "style": "system_design",
    },
    {
        "id": "behavior",
        "emoji": "🗣️",
        "label": "行为表达局",
        "desc": "围绕 STAR、稳定性、团队协作和动机表达组织追问。",
        "focus": "HR面 · 中级",
        "rhythm": "故事复盘",
        "interview_type": "hr",
        "difficulty": "mid",
        "style": "behavioral",
    },
    {
        "id": "leadership",
        "emoji": "📈",
        "label": "主管复盘局",
        "desc": "聚焦项目结果、协作推进与业务理解，强调判断力。",
        "focus": "主管面 · 高级",
        "rhythm": "结果导向",
        "interview_type": "manager",
        "difficulty": "senior",
        "style": "project_focused",
    },
]

# 精调选项
INTERVIEW_TYPE_OPTIONS = [
    {"value": "technical", "label": "技术面", "desc": "代码能力与技术深度", "emoji": "💻"},
    {"value": "hr", "label": "HR面", "desc": "职业动机与稳定性", "emoji": "🤝"},
    {"value": "manager", "label": "主管面", "desc": "业务理解与协作能力", "emoji": "📋"},
]

DIFFICULTY_OPTIONS = [
    {"value": "junior", "label": "初级", "desc": "基础概念与常见实践", "emoji": "🌱"},
    {"value": "mid", "label": "中级", "desc": "实战经验与原理理解", "emoji": "🚀"},
    {"value": "senior", "label": "高级", "desc": "架构能力与系统思考", "emoji": "🧭"},
]

STYLE_OPTIONS = [
    {"value": "default", "label": "标准模式", "desc": "专业均衡，客观评估", "emoji": "📘"},
    {"value": "strict", "label": "高压模式", "desc": "追问更深，要求更高", "emoji": "🎯"},
    {"value": "friendly", "label": "温和引导", "desc": "更适合练习和热身", "emoji": "🌤"},
    {"value": "technical_deep", "label": "技术深挖", "desc": "关注原理和实现细节", "emoji": "🧠"},
    {"value": "behavioral", "label": "行为面试", "desc": "聚焦经历表达与 STAR", "emoji": "🗣"},
    {"value": "system_design", "label": "系统设计", "desc": "考察架构设计与权衡", "emoji": "🏗"},
    {"value": "rapid_fire", "label": "快问快答", "desc": "强调知识广度和反应速度", "emoji": "⚡"},
    {"value": "project_focused", "label": "项目追问", "desc": "重点深挖项目细节", "emoji": "📂"},
]


def render(storage: InterviewStorage):
    """渲染面试页"""
    st.title("🎤 AI 模拟面试")

    # ── 初始化 session_state ──
    _init_session_state()

    # ── 检查模型可用性 ──
    providers = list_available_providers()
    available = [p for p in providers if p["available"]]
    if not available:
        st.error("⚠️ 请先在「⚙️ 设置」页配置 API Key")
        if st.button("前往设置"):
            st.session_state["nav_page"] = "settings"
            st.rerun()
        return

    # ── 渲染侧边栏配置 ──
    provider = _render_sidebar_config(storage, available)

    # ── 渲染主区域 ──
    if st.session_state.get("show_end_dialog"):
        _render_end_dialog(storage)
    elif st.session_state["interview_started"]:
        _render_chat_area(storage, provider)
    else:
        _render_start_prompt(storage, provider)


def _init_session_state():
    """初始化所有需要的 session_state 变量"""
    defaults = {
        "messages": [],
        "agent": None,
        "session_id": None,
        "resume_context": "",
        "interview_started": False,
        "show_end_dialog": False,
        "active_session_id": None,
        # 精调参数
        "interview_type": "technical",
        "difficulty": "mid",
        "style": "default",
        "target_position": "",
        "selected_preset": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ═══════════════════════════════════════════════════════════════
# 侧边栏：面试配置
# ═══════════════════════════════════════════════════════════════

def _render_sidebar_config(storage: InterviewStorage, available_providers: list):
    """渲染侧边栏的完整面试配置"""
    with st.sidebar:
        st.subheader("⚙️ 面试配置")

        # ── 模型选择 ──
        provider_labels = [p["label"] for p in available_providers]
        provider_keys = [p["key"] for p in available_providers]
        if "model_select_idx" not in st.session_state:
            st.session_state["model_select_idx"] = 0
        selected_label = st.selectbox(
            "🤖 AI 模型",
            provider_labels,
            index=min(st.session_state["model_select_idx"], len(provider_labels) - 1),
            key="model_select",
        )
        selected_key = provider_keys[provider_labels.index(selected_label)]
        provider = get_provider(selected_key)

        st.markdown("---")

        # ── 简历选择 ──
        st.caption("📄 简历")
        resumes = storage.list_resumes(limit=10)
        resume_options = ["(不使用简历)"] + [
            f"{r['file_name']} ({r.get('candidate_name', '')} - {r.get('position', '')})"
            for r in resumes
        ]
        selected_resume = st.selectbox(
            "选择简历",
            resume_options,
            key="resume_select",
            label_visibility="collapsed",
        )
        if selected_resume != "(不使用简历)":
            idx = resume_options.index(selected_resume) - 1
            resume_data = storage.get_session_resume(resumes[idx]["session_id"])
            if resume_data:
                st.session_state["resume_context"] = summarize_resume(
                    resume_data.get("resume_text", "")
                )
                st.session_state["active_session_id"] = resumes[idx]["session_id"]
                st.caption(f"✅ 已加载: {get_resume_preview(resume_data.get('resume_text', ''), max_chars=80)}")
            else:
                st.session_state["resume_context"] = ""
        else:
            st.session_state["resume_context"] = ""

        # 上传新简历
        with st.expander("📤 上传新简历"):
            uploaded = st.file_uploader(
                "支持 PDF/DOCX/TXT",
                type=["pdf", "docx", "txt", "md"],
                key="quick_resume_upload",
                label_visibility="collapsed",
            )
            if uploaded:
                _quick_upload_resume(storage, uploaded)

        st.markdown("---")

        # ── 面试预设卡片 ──
        st.caption("🎯 面试场景预设")
        preset_id = _render_preset_cards()

        # ── 自定义精调（当选中自定义或需要微调时展开）──
        with st.expander("🔧 精调参数", expanded=(preset_id == "custom")):
            _render_fine_tuning()

        st.markdown("---")

        # ── 目标岗位 ──
        st.session_state["target_position"] = st.text_input(
            "💼 目标岗位",
            value=st.session_state.get("target_position", ""),
            placeholder="如：后端开发工程师",
        )

        # ── 当前配置摘要 ──
        _render_config_summary()

    return provider


def _render_preset_cards() -> str:
    """渲染面试预设卡片选择器（参照 StageDeck 设计，简化为 radio cards）"""
    preset_options = INTERVIEW_PRESETS + [
        {
            "id": "custom",
            "emoji": "⚙️",
            "label": "自定义场景",
            "desc": "自由组合轮次、难度与风格，打造专属面试场景。",
            "focus": "自由组合",
            "rhythm": "精细配置",
            "style": "",
        }
    ]

    # 默认选中匹配当前参数的预设
    current_style = st.session_state.get("style", "default")
    current_type = st.session_state.get("interview_type", "technical")
    current_diff = st.session_state.get("difficulty", "mid")

    def _get_default_preset():
        for p in INTERVIEW_PRESETS:
            if (p["style"] == current_style and
                p["interview_type"] == current_type and
                p["difficulty"] == current_diff):
                return p["id"]
        return st.session_state.get("selected_preset", "warmup")

    default_id = _get_default_preset()
    preset_ids = [p["id"] for p in preset_options]
    default_idx = preset_ids.index(default_id) if default_id in preset_ids else 0

    selected_id = st.radio(
        "面试场景预设",
        preset_ids,
        format_func=lambda x: _format_preset_label(x, preset_options),
        index=default_idx,
        key="preset_radio",
        label_visibility="collapsed",
    )

    # 当选中预设时，自动同步参数
    if selected_id != "custom":
        preset = next((p for p in INTERVIEW_PRESETS if p["id"] == selected_id), None)
        if preset:
            st.session_state["interview_type"] = preset["interview_type"]
            st.session_state["difficulty"] = preset["difficulty"]
            st.session_state["style"] = preset["style"]
            st.session_state["selected_preset"] = selected_id
    else:
        st.session_state["selected_preset"] = "custom"

    # 显示当前选中卡片的描述
    selected_preset = next((p for p in preset_options if p["id"] == selected_id), preset_options[0])
    st.caption(
        f"{selected_preset['emoji']} **{selected_preset['label']}** — "
        f"{selected_preset.get('focus', '')} · {selected_preset.get('rhythm', '')}"
    )

    return selected_id


def _format_preset_label(preset_id: str, presets: list) -> str:
    """格式化预设卡片标签"""
    p = next((x for x in presets if x["id"] == preset_id), None)
    if not p:
        return preset_id
    return f"{p['emoji']} {p['label']}"


def _render_fine_tuning():
    """渲染精调参数：面试轮次、难度、风格（参照 SetupView 的精调面板）"""
    # 面试轮次
    st.caption("**面试轮次**")
    type_options = [o["value"] for o in INTERVIEW_TYPE_OPTIONS]
    type_labels = [f"{o['emoji']} {o['label']} - {o['desc']}" for o in INTERVIEW_TYPE_OPTIONS]
    current_type = st.session_state.get("interview_type", "technical")
    try:
        type_idx = type_options.index(current_type)
    except ValueError:
        type_idx = 0
    st.session_state["interview_type"] = st.radio(
        "轮次", type_options, index=type_idx,
        format_func=lambda x: dict(zip(type_options, type_labels))[x],
        key="type_radio", label_visibility="collapsed",
    )

    st.markdown("")

    # 难度级别
    st.caption("**难度级别**")
    diff_options = [o["value"] for o in DIFFICULTY_OPTIONS]
    diff_labels = [f"{o['emoji']} {o['label']} - {o['desc']}" for o in DIFFICULTY_OPTIONS]
    current_diff = st.session_state.get("difficulty", "mid")
    try:
        diff_idx = diff_options.index(current_diff)
    except ValueError:
        diff_idx = 1
    st.session_state["difficulty"] = st.radio(
        "难度", diff_options, index=diff_idx,
        format_func=lambda x: dict(zip(diff_options, diff_labels))[x],
        key="diff_radio", label_visibility="collapsed",
    )

    st.markdown("")

    # 面试风格
    st.caption("**面试风格**")
    style_options = [o["value"] for o in STYLE_OPTIONS]
    style_labels = [f"{o['emoji']} **{o['label']}** — {o['desc']}" for o in STYLE_OPTIONS]
    current_style = st.session_state.get("style", "default")
    try:
        style_idx = style_options.index(current_style)
    except ValueError:
        style_idx = 0
    st.session_state["style"] = st.radio(
        "风格", style_options, index=style_idx,
        format_func=lambda x: dict(zip(style_options, style_labels))[x],
        key="style_radio", label_visibility="collapsed",
    )


def _render_config_summary():
    """渲染当前配置摘要（参照原项目 confirmSummaryItems）"""
    type_label = next((o["label"] for o in INTERVIEW_TYPE_OPTIONS if o["value"] == st.session_state.get("interview_type")), "技术面")
    diff_label = next((o["label"] for o in DIFFICULTY_OPTIONS if o["value"] == st.session_state.get("difficulty")), "中级")
    style_label = next((o["label"] for o in STYLE_OPTIONS if o["value"] == st.session_state.get("style")), "标准")
    position = st.session_state.get("target_position", "") or "待填写"
    has_resume = "✅" if st.session_state.get("resume_context") else "❌"

    st.caption(
        f"📋 当前配置: {type_label} / {diff_label} / {style_label}\n"
        f"💼 岗位: {position} | 📄 简历: {has_resume}"
    )


def _quick_upload_resume(storage: InterviewStorage, uploaded_file):
    """快速上传简历并自动关联"""
    import os as _os
    from services.resume_parser import extract_resume_text
    import config

    with st.spinner("解析简历中..."):
        ext = _os.path.splitext(uploaded_file.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = config.UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())

        resume_text = extract_resume_text(str(filepath))
        if resume_text.startswith("[错误]"):
            st.error(resume_text)
            _os.remove(filepath)
            return

        session_id = uuid.uuid4().hex[:12]
        storage.create_session(
            session_id=session_id,
            candidate_name="面试候选人",
            position=st.session_state.get("target_position", "未指定岗位"),
        )
        storage.save_resume(
            session_id=session_id,
            file_name=uploaded_file.name,
            file_path=str(filepath),
            resume_text=resume_text,
        )
        st.session_state["resume_context"] = summarize_resume(resume_text)
        st.session_state["active_session_id"] = session_id
        st.success(f"✅ 简历已解析 ({len(resume_text)} 字符)")


# ═══════════════════════════════════════════════════════════════
# 启动面试
# ═══════════════════════════════════════════════════════════════

def _render_start_prompt(storage: InterviewStorage, provider):
    """面试未开始时的启动界面"""
    st.info("👋 在左侧配置面试参数后，点击下方按钮开始面试")

    # 配置摘要
    col1, col2, col3 = st.columns(3)
    model_label = provider.label if provider else "未选择"
    style_label = next((o["label"] for o in STYLE_OPTIONS if o["value"] == st.session_state.get("style")), "标准")
    position = st.session_state.get("target_position", "") or "未指定"
    with col1:
        st.metric("模型", model_label)
    with col2:
        st.metric("风格", style_label)
    with col3:
        st.metric("岗位", position)

    st.markdown("")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("▶️ 开始沉浸式面试", type="primary", use_container_width=True):
            _start_interview(storage, provider)
            st.rerun()


def _start_interview(storage: InterviewStorage, provider):
    """开始新面试"""
    agent = InterviewAgent(
        api_key=provider.api_key,
        base_url=provider.base_url,
        model=provider.model,
        max_history_turns=10,
    )
    agent.set_style(st.session_state.get("style", "default"))

    session_id = st.session_state.get("active_session_id") or uuid.uuid4().hex[:12]
    if not st.session_state.get("active_session_id"):
        storage.create_session(
            session_id=session_id,
            candidate_name="面试候选人",
            position=st.session_state.get("target_position", "未指定岗位"),
            interview_style=st.session_state.get("style", "default"),
            metadata={
                "type": st.session_state.get("interview_type", "technical"),
                "diff": st.session_state.get("difficulty", "mid"),
                "style": st.session_state.get("style", "default"),
            },
        )

    st.session_state["agent"] = agent
    st.session_state["session_id"] = session_id
    st.session_state["interview_started"] = True

    greeting = agent.get_greeting()
    st.session_state["messages"] = [{"role": "assistant", "content": greeting}]
    storage.save_message(session_id, "assistant", greeting)


# ═══════════════════════════════════════════════════════════════
# 聊天界面
# ═══════════════════════════════════════════════════════════════

def _render_chat_area(storage: InterviewStorage, provider):
    """渲染聊天区域（参照原项目 ChatPanel + AiVisualization 双面板设计）"""
    # ── 状态指示器 ──
    style_label = next((o["label"] for o in STYLE_OPTIONS if o["value"] == st.session_state.get("style")), "标准")
    position = st.session_state.get("target_position", "未指定岗位")
    st.caption(f"🎯 {style_label} | 💼 {position} | 🤖 {provider.label}")

    # ── 对话消息 ──
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state["messages"]):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ── 用户输入 ──
    if prompt := st.chat_input("输入你的回答...", key="chat_input_main"):
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # AI 回复
        agent: InterviewAgent = st.session_state.get("agent")
        if agent and agent.llm_client:
            with st.chat_message("assistant"):
                thinking_expander = st.expander("🧠 思考过程", expanded=False)
                content_placeholder = st.empty()

                thinking_text = ""
                content_text = ""

                for chunk_type, chunk in agent.run_stream(
                    prompt, context=st.session_state.get("resume_context", "")
                ):
                    if chunk_type == "thinking":
                        thinking_text += chunk
                        if thinking_text.strip():
                            thinking_expander.markdown(
                                f"```\n{thinking_text[:2000]}\n```"
                            )
                    elif chunk_type == "content":
                        content_text += chunk
                        content_placeholder.markdown(content_text + "▌")

                content_placeholder.markdown(content_text or "(无回复)")

                if content_text:
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": content_text}
                    )
                    sid = st.session_state.get("session_id")
                    if sid:
                        storage.save_message(sid, "user", prompt)
                        storage.save_message(sid, "assistant", content_text)
        else:
            with st.chat_message("assistant"):
                st.error("Agent 未初始化，请检查 API Key 配置")

    # ── 操作栏 ──
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🛑 结束面试", use_container_width=True):
            st.session_state["show_end_dialog"] = True
            st.rerun()
    with col2:
        if st.button("🔄 重新开始", use_container_width=True):
            _reset_interview()
            st.rerun()
    with col3:
        if st.button("⬅️ 返回首页", use_container_width=True):
            _reset_interview()
            st.session_state["nav_page"] = "home"
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# 结束确认对话框
# ═══════════════════════════════════════════════════════════════

def _render_end_dialog(storage: InterviewStorage):
    """
    渲染结束面试确认界面（参照原项目 showEndDialog）

    三个选项：
    - 保存并生成报告 → 跳转报告页
    - 不保存，直接结束 → 返回首页
    - 继续面试 → 关闭对话框
    """
    st.warning("### ⚠️ 确认结束面试")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("对话轮数", len([m for m in st.session_state.get("messages", []) if m["role"] == "user"]))
    with col2:
        duration = "进行中"
        st.metric("状态", duration)

    st.markdown("""
    你可以选择**保存**本次面试历史，保存后会生成评估报告；
    如果不保存，本次对话和报告都会被释放。
    """)

    st.markdown("")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("↩️ 继续面试", use_container_width=True):
            st.session_state["show_end_dialog"] = False
            st.rerun()
    with col2:
        if st.button("🗑️ 不保存，直接结束", use_container_width=True, type="secondary"):
            _end_without_save(storage)
            st.rerun()
    with col3:
        if st.button("💾 保存并生成报告", use_container_width=True, type="primary"):
            _end_with_save(storage)
            st.rerun()


def _end_with_save(storage: InterviewStorage):
    """保存并生成评估报告"""
    agent: InterviewAgent = st.session_state.get("agent")
    sid = st.session_state.get("session_id")

    if agent and sid:
        with st.spinner("🤖 AI 正在生成评估报告..."):
            eval_result = agent.evaluate_interview()

            if eval_result:
                for ev in eval_result.get("evaluations", []):
                    storage.save_evaluation(
                        sid, ev["dimension"], ev["score"], ev.get("comment", "")
                    )
                st.session_state["eval_result"] = eval_result
                st.session_state["eval_strengths"] = eval_result.get("strengths", "")
                st.session_state["eval_weaknesses"] = eval_result.get("weaknesses", "")
                st.session_state["eval_summary"] = eval_result.get("summary", "")

            storage.end_session(sid)

    st.session_state["show_end_dialog"] = False
    st.session_state["interview_started"] = False
    st.session_state["view_session_id"] = sid
    st.session_state["nav_page"] = "report"


def _end_without_save(storage: InterviewStorage):
    """不保存直接结束"""
    sid = st.session_state.get("session_id")
    if sid:
        storage.end_session(sid)
    _reset_interview()
    st.session_state["show_end_dialog"] = False
    st.session_state["nav_page"] = "home"


def _reset_interview():
    """重置面试状态"""
    st.session_state["agent"] = None
    st.session_state["session_id"] = None
    st.session_state["messages"] = []
    st.session_state["resume_context"] = ""
    st.session_state["interview_started"] = False
    st.session_state["show_end_dialog"] = False
    st.session_state["active_session_id"] = None
