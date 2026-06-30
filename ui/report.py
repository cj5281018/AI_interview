"""
评估报告页 — 展示面试评估结果

参照原项目 ReportView 的设计：
- 综合评分 + 各维度彩色进度条
- 优势亮点 + 改进建议双卡片
- AI 总评
- 历史报告切换
"""
import streamlit as st
import pandas as pd
from core.storage import InterviewStorage

# 颜色映射（参照原项目 Tailwind 配色）
def _score_color(score: int) -> str:
    """根据分数返回颜色"""
    if score >= 7:
        return "#10b981"  # emerald-500
    elif score >= 5:
        return "#f59e0b"  # amber-500
    else:
        return "#ef4444"  # red-500


def _score_bg(score: int) -> str:
    """根据分数返回背景色"""
    if score >= 7:
        return "#ecfdf5"  # emerald-50
    elif score >= 5:
        return "#fffbeb"  # amber-50
    else:
        return "#fef2f2"  # red-50


def render(storage: InterviewStorage):
    """渲染评估报告页"""
    st.title("📊 面试评估报告")

    # ── 获取会话 ──
    session_id = st.session_state.get("view_session_id") or st.session_state.get("session_id")
    sessions = storage.list_sessions()

    finished_sessions = [s for s in sessions if s["status"] == "completed"]
    if not finished_sessions:
        st.info("暂无已完成的面试记录。完成一次面试后，评估报告会显示在这里。")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🎤 开始新面试", type="primary"):
                st.session_state["nav_page"] = "interview"
                st.rerun()
        return

    # ── 历史报告切换 ──
    session_options = {
        f"{s['position'] or '未知岗位'} — {s.get('candidate_name', '匿名')} ({s.get('start_time', '')[:10]})": s["session_id"]
        for s in finished_sessions
    }
    selected_label = st.selectbox(
        "📋 选择面试记录",
        list(session_options.keys()),
        index=_find_index(list(session_options.values()), session_id),
    )
    session_id = session_options[selected_label]

    # ── 获取数据 ──
    session_info = storage.get_session_info(session_id)
    evaluations = storage.get_session_evaluations(session_id)
    statistics = storage.get_session_statistics(session_id)
    history = storage.get_session_history(session_id)

    if not session_info:
        st.warning("会话信息不存在")
        return

    # ── 尝试从 session_state 获取实时评估 ──
    eval_result = st.session_state.get("eval_result")
    strengths = st.session_state.get("eval_strengths", "")
    weaknesses = st.session_state.get("eval_weaknesses", "")
    summary = st.session_state.get("eval_summary", "")

    # 如果当前 session_id 匹配且没有 DB 中的评估数据，用 session_state 的
    if not evaluations and eval_result and session_id == st.session_state.get("session_id"):
        evaluations = eval_result.get("evaluations", [])
        strengths = strengths or eval_result.get("strengths", "")
        weaknesses = weaknesses or eval_result.get("weaknesses", "")
        summary = summary or eval_result.get("summary", "")

    # ═══════════════════════════════════════
    # 面试概要
    # ═══════════════════════════════════════
    st.subheader("📋 面试概要")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("岗位", session_info.get("position", "未知"))
    with col2:
        style_map = {
            "default": "标准", "strict": "高压", "friendly": "温和",
            "technical_deep": "技术深挖", "behavioral": "行为面试",
            "system_design": "系统设计", "rapid_fire": "快问快答",
            "project_focused": "项目追问",
        }
        st.metric("风格", style_map.get(session_info.get("interview_style", ""), "标准"))
    with col3:
        st.metric("对话轮数", statistics.get("turn_count", 0))
    with col4:
        st.metric("综合均分", f"{statistics.get('avg_score', 0)}/10")

    # ── 加载中的评估 ──
    if not evaluations and session_id == st.session_state.get("session_id"):
        st.info("⏳ 评估报告正在生成中...")

    # ═══════════════════════════════════════
    # AI 总评
    # ═══════════════════════════════════════
    if summary:
        st.markdown("---")
        st.subheader("💬 AI 面试官总评")
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
                        border:1px solid #bfdbfe; border-radius:16px; padding:20px 24px;
                        font-size:15px; line-height:1.8; color:#1e3a5f;">
            {summary}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ═══════════════════════════════════════
    # 多维度评分（参照原项目 ReportView 的进度条设计）
    # ═══════════════════════════════════════
    st.markdown("---")
    st.subheader("📈 多维度评估")

    if evaluations:
        cols = st.columns([1, 2])
        with cols[0]:
            # 综合评分大圆显示
            avg_score = statistics.get("avg_score", 0)
            st.metric("综合评分", f"{avg_score:.1f} / 10")

        with cols[1]:
            for ev in evaluations:
                score = ev["score"]
                pct = score / 10.0
                color = _score_color(score)
                bg = _score_bg(score)

                st.markdown(
                    f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <span style="font-weight:600; font-size:14px; color:#334155;">{ev['dimension']}</span>
                            <span style="font-weight:700; font-size:14px; color:{color};">{score}/10</span>
                        </div>
                        <div style="background:#f1f5f9; border-radius:999px; height:12px; overflow:hidden;">
                            <div style="background:{color}; width:{pct*100}%; height:100%; border-radius:999px;
                                        transition: width 500ms ease-out;"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if ev.get("comment"):
                    st.caption(f"📝 {ev['comment']}")

        # 表格形式（备选）
        with st.expander("📊 查看评分明细表"):
            df = pd.DataFrame(evaluations)
            df_display = df.rename(columns={
                "dimension": "评估维度", "score": "评分(1-10)", "comment": "评语",
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        # 柱状图
        df_chart = pd.DataFrame(evaluations)
        st.bar_chart(df_chart.set_index("dimension")["score"], use_container_width=True)
    else:
        st.info("暂无评估数据。如果刚结束面试，评分正在生成中...")

    # ═══════════════════════════════════════
    # 优势与不足（双卡片布局，参照原项目）
    # ═══════════════════════════════════════
    if strengths or weaknesses:
        st.markdown("---")
        st.subheader("💪 优势与改进")

        col1, col2 = st.columns(2)
        with col1:
            if strengths:
                st.markdown(
                    f"""
                    <div style="background:linear-gradient(180deg, #f0fdf4 0%, #ecfdf5 100%);
                                border:1px solid #86efac; border-radius:16px; padding:20px 24px; min-height:160px;">
                        <h4 style="color:#166534; margin:0 0 12px 0;">✅ 优势亮点</h4>
                        <p style="color:#14532d; font-size:14px; line-height:1.8; margin:0;">{strengths}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("优势数据生成中...")

        with col2:
            if weaknesses:
                st.markdown(
                    f"""
                    <div style="background:linear-gradient(180deg, #fffbeb 0%, #fefce8 100%);
                                border:1px solid #fcd34d; border-radius:16px; padding:20px 24px; min-height:160px;">
                        <h4 style="color:#92400e; margin:0 0 12px 0;">⚠️ 改进建议</h4>
                        <p style="color:#78350f; font-size:14px; line-height:1.8; margin:0;">{weaknesses}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("改进建议生成中...")

    # ═══════════════════════════════════════
    # 对话回顾
    # ═══════════════════════════════════════
    st.markdown("---")
    with st.expander("💬 查看完整对话记录", expanded=False):
        if history:
            for msg in history:
                role_label = "🟢 候选人" if msg["role"] == "user" else "🔵 面试官"
                ts = msg.get("timestamp", "")[:19] if msg.get("timestamp") else ""
                st.caption(f"{role_label} ({ts})")
                st.markdown(msg["content"][:1000])
                st.markdown("---")
        else:
            st.info("暂无对话记录")

    # ═══════════════════════════════════════
    # 操作按钮
    # ═══════════════════════════════════════
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧭 查看职业规划", use_container_width=True, type="primary"):
            st.session_state["plan_session_id"] = session_id
            st.session_state["nav_page"] = "career"
            st.rerun()
    with col2:
        if st.button("🔄 重新挑战", use_container_width=True):
            st.session_state["nav_page"] = "interview"
            st.rerun()
    with col3:
        if st.button("🗑️ 删除此记录", use_container_width=True):
            if storage.delete_session(session_id):
                st.success("已删除")
                st.session_state["nav_page"] = "home"
                st.rerun()


def _find_index(session_ids: list, target: str) -> int:
    """在会话ID列表中查找目标索引"""
    if not target:
        return 0
    try:
        return session_ids.index(target)
    except ValueError:
        return 0
