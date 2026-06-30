"""
职业规划页 — 基于面试评估生成学习建议和发展路线
"""
import streamlit as st
from core.storage import InterviewStorage
from core.model_registry import get_default_provider
from services.career_service import CareerPlanningService


def render(storage: InterviewStorage):
    """渲染职业规划页"""
    st.title("🧭 职业规划")
    st.caption("基于面试评估结果，AI 为你生成个性化的学习路线和职业建议")

    # ── 汇总所有面试数据 ──
    sessions = storage.list_sessions(limit=20)
    completed = [s for s in sessions if s["status"] == "completed"]

    if not completed:
        st.info("暂无已完成的面试记录。请先完成至少一次模拟面试，系统将基于评估结果生成职业规划建议。")
        if st.button("⬅️ 返回首页"):
            st.session_state["nav_page"] = "home"
            st.rerun()
        return

    # ── 历史评估总览 ──
    st.subheader("📊 历史评估总览")

    all_eval_data = []
    for s in completed:
        evals = storage.get_session_evaluations(s["session_id"])
        stats = storage.get_session_statistics(s["session_id"])
        if evals:
            all_eval_data.append({
                "session_id": s["session_id"],
                "position": s.get("position", "未知"),
                "date": s.get("start_time", "")[:10],
                "evaluations": evals,
                "avg_score": stats.get("avg_score", 0),
            })

    if not all_eval_data:
        st.info("暂无有效的评估数据")
        return

    # 显示历史表格
    for item in all_eval_data:
        with st.expander(
            f"📋 {item['position']} — {item['date']} (均分: {item['avg_score']}/10)"
        ):
            for ev in item["evaluations"]:
                st.text(f"  {ev['dimension']}: {ev['score']}/10 — {ev['comment']}")

    # ── 综合雷达图数据 ──
    st.markdown("---")
    st.subheader("📈 能力雷达图（最近一次）")

    latest = all_eval_data[-1]
    career_svc = CareerPlanningService()
    radar_data = career_svc.build_radar_data(latest["evaluations"])
    if radar_data["dimensions"]:
        # 用 bar_chart 代替雷达图（Streamlit 内置）
        import pandas as pd
        df = pd.DataFrame({
            "维度": radar_data["dimensions"],
            "评分": radar_data["scores"],
        })
        st.bar_chart(df.set_index("维度"), use_container_width=True)

    # ── 生成学习计划 ──
    st.markdown("---")
    st.subheader("📝 AI 学习计划")

    target_role = st.text_input("目标岗位（用于制定学习计划）", value=latest.get("position", ""))
    col1, col2 = st.columns([2, 1])
    with col1:
        generate_plan = st.button(
            "🤖 生成个性化学习计划", type="primary", use_container_width=True
        )
    with col2:
        generate_advice = st.button(
            "💡 生成职业建议", use_container_width=True
        )

    if generate_plan or generate_advice:
        provider = get_default_provider()
        if not provider.available:
            st.error("请先在「设置」页配置 API Key")
            return

        from core.llm_client import OpenAICompatibleClient
        llm = OpenAICompatibleClient(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url,
        )
        career_svc = CareerPlanningService(llm)

    if generate_plan:
        with st.spinner("AI 正在为你量身定制学习计划..."):
            latest_evals = latest["evaluations"]
            # 聚合弱点
            weaknesses_list = [
                f"{ev['dimension']}({ev['score']}分): {ev['comment']}"
                for ev in latest_evals if ev["score"] < 6
            ]
            weaknesses_text = "\n".join(weaknesses_list) if weaknesses_list else "各维度表现均衡"

            plan = career_svc.generate_learning_plan(
                evaluations=latest_evals,
                weaknesses=weaknesses_text,
                target_role=target_role,
            )

            st.success(f"### {plan.get('plan_title', '学习计划')}")
            for week_data in plan.get("weekly_tasks", []):
                with st.expander(f"📅 第 {week_data['week']} 周: {week_data.get('topic', '')}"):
                    st.markdown("**任务清单:**")
                    for task in week_data.get("tasks", []):
                        st.markdown(f"- {task}")
                    st.markdown("**推荐资源:**")
                    for res in week_data.get("resources", []):
                        st.markdown(f"- 📖 {res}")

    if generate_advice:
        with st.spinner("AI 正在分析你的面试数据..."):
            advice = career_svc.generate_career_advice(all_eval_data)
            st.info(advice)
