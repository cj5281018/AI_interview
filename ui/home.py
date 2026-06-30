"""
首页 — 仪表盘

展示历史面试记录、快速入口、统计概览。
参照原项目 HistoryListView 的设计。
"""
import streamlit as st
from core.storage import InterviewStorage
from core.model_registry import list_available_providers

# 风格显示映射
STYLE_LABEL_MAP = {
    "default": "标准", "strict": "高压", "friendly": "温和",
    "technical_deep": "技术深挖", "behavioral": "行为面试",
    "system_design": "系统设计", "rapid_fire": "快问快答",
    "project_focused": "项目追问",
}
TYPE_LABEL_MAP = {"technical": "技术面", "hr": "HR面", "manager": "主管面"}
DIFF_LABEL_MAP = {"junior": "初级", "mid": "中级", "senior": "高级"}


def render(storage: InterviewStorage):
    """渲染首页"""
    st.title("🏠 ProView AI 面试官")
    st.caption("本地优先的 AI 模拟面试工具 — 基于 DeepSeek & 通义千问")

    # ── 模型状态 ──
    providers = list_available_providers()
    available = [p for p in providers if p["available"]]
    if not available:
        st.warning("⚠️ 尚未配置任何 LLM API Key，请先前往「⚙️ 设置」页面配置。")
    else:
        labels = [p["label"] for p in available]
        st.success(f"✅ 已就绪: {', '.join(labels)}")

    # ── 快捷操作 ──
    st.markdown("---")
    st.subheader("🚀 快速开始")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎤 开始新面试", use_container_width=True, type="primary"):
            st.session_state["nav_page"] = "interview"
            st.rerun()
    with col2:
        if st.button("📄 管理简历", use_container_width=True):
            st.session_state["nav_page"] = "resume"
            st.rerun()
    with col3:
        if st.button("⚙️ 配置 API Key", use_container_width=True):
            st.session_state["nav_page"] = "settings"
            st.rerun()

    # ── 历史记录 ──
    st.markdown("---")
    st.subheader("📋 面试历史记录")

    sessions = storage.list_sessions(limit=10)

    if not sessions:
        st.info("暂无面试记录，点击上方「开始新面试」开始你的第一次模拟面试吧！")
        return

    for s in sessions:
        status_icon = "🟢" if s["status"] == "active" else "✅"
        status_text = "进行中" if s["status"] == "active" else "已完成"
        style_label = STYLE_LABEL_MAP.get(s.get("interview_style", ""), "标准")

        # 解析 metadata
        meta = s.get("metadata") or {}
        if isinstance(meta, str):
            import json
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        type_label = TYPE_LABEL_MAP.get(meta.get("type", ""), "")
        diff_label = DIFF_LABEL_MAP.get(meta.get("diff", ""), "")

        tags = " · ".join(filter(None, [style_label, type_label, diff_label]))

        with st.expander(
            f"{status_icon} {s['position'] or '未指定岗位'} — "
            f"{s.get('candidate_name', '匿名')} "
            f"({s['start_time'][:10] if s.get('start_time') else '未知时间'})"
        ):
            st.caption(f"🏷️ {tags} | 📅 {status_text}")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("状态", status_text)
            with c2:
                st.metric("风格", style_label)
            with c3:
                stats = storage.get_session_statistics(s["session_id"])
                st.metric("对话轮数", stats.get("turn_count", 0))

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("📊 查看报告", key=f"report_{s['session_id']}"):
                    st.session_state["view_session_id"] = s["session_id"]
                    st.session_state["nav_page"] = "report"
                    st.rerun()
            with btn_col2:
                if s["status"] == "active":
                    if st.button("▶️ 继续面试", key=f"continue_{s['session_id']}"):
                        st.session_state["active_session_id"] = s["session_id"]
                        st.session_state["nav_page"] = "interview"
                        st.rerun()
            with btn_col3:
                if st.button("🗑️ 删除", key=f"delete_{s['session_id']}"):
                    storage.delete_session(s["session_id"])
                    st.rerun()
