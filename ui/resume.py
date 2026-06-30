"""
简历管理页 — 上传、查看、管理简历
"""
import os
import uuid
import streamlit as st
import config
from core.storage import InterviewStorage
from services.resume_parser import extract_resume_text, get_resume_preview


def render(storage: InterviewStorage):
    """渲染简历管理页"""
    st.title("📄 简历管理")
    st.caption("上传并管理你的简历，AI 面试官将基于简历内容进行针对性提问")

    # ── 上传简历 ──
    st.subheader("📤 上传新简历")
    uploaded_file = st.file_uploader(
        "支持 PDF、Word、TXT、Markdown、图片（JPG/PNG/BMP/WEBP）",
        type=["pdf", "docx", "txt", "md", "jpg", "jpeg", "png", "bmp", "webp"],
        key="resume_uploader",
    )

    candidate_name = st.text_input("候选人姓名（可选）", placeholder="张三")
    target_position = st.text_input("目标岗位（可选）", placeholder="如：后端开发工程师")

    if uploaded_file and st.button("📥 上传并解析", type="primary"):
        with st.spinner("正在解析简历..."):
            # 保存文件
            ext = os.path.splitext(uploaded_file.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = config.UPLOAD_DIR / filename
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 提取文本
            resume_text = extract_resume_text(str(filepath))

            if resume_text.startswith("[错误]"):
                st.error(resume_text)
                os.remove(filepath)
            else:
                # 创建会话并保存简历
                session_id = uuid.uuid4().hex[:12]
                storage.create_session(
                    session_id=session_id,
                    candidate_name=candidate_name or "未命名",
                    position=target_position or "未指定岗位",
                )
                storage.save_resume(
                    session_id=session_id,
                    file_name=uploaded_file.name,
                    file_path=str(filepath),
                    resume_text=resume_text,
                )
                st.success(f"✅ 简历解析成功！提取了 {len(resume_text)} 个字符")
                with st.expander("📝 预览解析内容"):
                    st.text_area(
                        "简历文本",
                        value=resume_text[:5000],
                        height=200,
                        disabled=True,
                    )
                st.info(f"简历已关联到会话 ID: {session_id}，可在面试页面使用")

    # ── 已上传的简历列表 ──
    st.markdown("---")
    st.subheader("📚 已上传的简历")

    resumes = storage.list_resumes()
    if not resumes:
        st.info("暂无简历，请上传你的第一份简历。")
        return

    for r in resumes:
        with st.expander(
            f"📄 {r['file_name']} — {r.get('candidate_name', '匿名')} "
            f"({r.get('position', '未指定岗位')}) — {r['upload_time'][:10] if r.get('upload_time') else ''}"
        ):
            # 获取简历文本
            resume_data = storage.get_session_resume(r["session_id"])
            if resume_data and resume_data.get("resume_text"):
                preview = get_resume_preview(resume_data["resume_text"], max_chars=200)
                st.text(preview)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("▶️ 用此简历开始面试", key=f"interview_{r['session_id']}"):
                    st.session_state["active_session_id"] = r["session_id"]
                    st.session_state["nav_page"] = "interview"
                    st.rerun()
            with c2:
                if st.button("🗑️ 删除", key=f"del_resume_{r['id']}"):
                    storage.delete_session(r["session_id"])
                    # 也删除本地文件
                    if resume_data and resume_data.get("file_path"):
                        try:
                            os.remove(resume_data["file_path"])
                        except Exception:
                            pass
                    st.rerun()
