"""
Flask API 后端 — 面试服务

API 端点:
  GET  /api/health           — 健康检查
  GET  /api/models            — 列出可用模型
  GET  /api/styles            — 列出面试风格
  POST /api/resume/upload     — 上传简历，返回解析文本
  POST /api/setup             — 创建面试会话
  POST /api/chat              — 发送消息，SSE 流式响应
  POST /api/end               — 结束面试，生成报告
  GET  /api/report/<sid>      — 获取评估报告
  GET  /api/sessions          — 列出历史会话

启动:
  python app.py
"""
import sys, os, uuid, json, re
from pathlib import Path

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

import config as app_config
from core.storage import InterviewStorage
from core.interview_agent import InterviewAgent
from core.model_registry import get_provider, list_available_providers, init_providers
from services.resume_text_extraction import extract_resume_content
from core.resume_analyzer import ResumeAnalyzer
from core.ocr_processor import perform_ocr, perform_ocr_full, get_ocr_runtime_settings
from services.resume_parser import summarize_resume, get_resume_preview

# ── OCR 适配器：PaddleOCR 云端 API ──

def _ocr_available() -> bool:
    url, token = get_ocr_runtime_settings()
    return bool(url and token)

def _ocr_text_loader(image_path: str, use_preprocessing: bool = True, is_screen_capture: bool = False) -> str:
    return perform_ocr(image_path, use_preprocessing=use_preprocessing, is_screen_capture=is_screen_capture)

def _ocr_full_loader(image_path: str, use_preprocessing: bool = True, is_screen_capture: bool = False) -> dict:
    return perform_ocr_full(image_path, use_preprocessing=use_preprocessing, is_screen_capture=is_screen_capture)

# 启动诊断
_url, _token = get_ocr_runtime_settings()
print(f"[init] PaddleOCR v2: URL={'已配置' if _url else '❌未配置'}, Token={'已配置' if _token else '❌未配置'}")

app = Flask(__name__)
CORS(app)

# 初始化
init_providers()
storage = InterviewStorage(str(app_config.DB_PATH))

# 内存中的 agent 管理
_agents: dict[str, InterviewAgent] = {}
_stop_flags: dict[str, bool] = {}

# ── 帮助函数 ──

def _get_style_list():
    """返回面试风格列表"""
    import json as _json
    prompts_path = PROJECT_ROOT / "core" / "prompts.json"
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
        return [
            {"key": k, "name": v.get("name", k), "desc": v.get("description", "")}
            for k, v in data.get("styles", {}).items()
        ]
    except Exception:
        return [
            {"key": "default", "name": "默认模式", "desc": "平衡的面试风格"},
            {"key": "strict", "name": "高压模式", "desc": "严格追问"},
            {"key": "friendly", "name": "温和模式", "desc": "友善鼓励"},
            {"key": "technical_deep", "name": "技术深挖", "desc": "专注底层原理"},
        ]

# ═══════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════

@app.route("/api/health")
def health():
    providers = list_available_providers()
    available = [p["label"] for p in providers if p["available"]]
    return jsonify({
        "status": "ok",
        "models_available": available,
    })


@app.route("/api/models")
def list_models():
    return jsonify(list_available_providers())


@app.route("/api/styles")
def list_styles():
    return jsonify(_get_style_list())


@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():
    """上传简历，解析文本并返回 — 使用复刻版完整管线"""
    if "file" not in request.files:
        return jsonify({"error": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "文件名为空"}), 400

    # 保存文件
    ext = Path(file.filename).suffix.lower()
    supported = {".pdf", ".docx", ".doc", ".txt", ".md", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if ext not in supported:
        return jsonify({"error": f"不支持的格式: {ext}。支持: PDF, DOCX, TXT, MD, JPG, PNG, BMP, WEBP"}), 400

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = app_config.UPLOAD_DIR / filename
    file.save(str(filepath))

    # 使用复刻版简历文本提取 + PaddleOCR 云端 API
    try:
        ocr_ok = _ocr_available()
        print(f"[resume/upload] 文件类型: {ext}, OCR 可用: {ocr_ok}")
        if ext in (".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".webp") and not ocr_ok:
            return jsonify({"error": "当前文件类型需要 OCR，但 PaddleOCR 未配置。请在 .env 中设置 PADDLEOCR_API_URL 和 PADDLE_OCR_TOKEN"}), 400
        result = extract_resume_content(
            str(filepath),
            include_images=False,
            ocr_available=ocr_ok,
            ocr_text_loader=_ocr_text_loader if ocr_ok else None,
            ocr_full_loader=_ocr_full_loader if ocr_ok else None,
        )
    except Exception as e:
        os.remove(str(filepath))
        return jsonify({"error": f"简历解析失败: {str(e)}"}), 400

    if not result["success"]:
        os.remove(str(filepath))
        return jsonify({"error": result.get("error_message", "简历解析失败，请检查文件格式")}), 400

    return jsonify({
        "success": True,
        "resume_text": result["text"],
        "resume_preview": get_resume_preview(result["text"]),
        "file_name": file.filename,
        "file_path": str(filepath),
        "char_count": len(result["text"]),
        "source": result.get("source_label", ""),
        "mode": result.get("mode", ""),
    })


@app.route("/api/setup", methods=["POST"])
def setup_interview():
    """创建面试会话"""
    data = request.get_json() or {}

    model_key = data.get("model", "deepseek")
    provider = get_provider(model_key)
    if not provider or not provider.available:
        provider = get_provider("deepseek")
        if not provider or not provider.available:
            return jsonify({"error": "没有可用的模型，请先配置 API Key"}), 400

    style = data.get("style", "default")
    position = data.get("position", "未指定岗位")
    interview_type = data.get("interview_type", "technical")
    difficulty = data.get("difficulty", "mid")
    resume_text = data.get("resume_text", "")
    candidate_name = data.get("candidate_name", "面试候选人")

    # 创建 Agent
    agent = InterviewAgent(
        api_key=provider.api_key,
        base_url=provider.base_url,
        model=provider.model,
        max_history_turns=10,
    )
    agent.set_style(style)

    # 简历上下文
    context = summarize_resume(resume_text) if resume_text else ""

    # 创建存储会话
    session_id = uuid.uuid4().hex[:12]
    storage.create_session(
        session_id=session_id,
        candidate_name=candidate_name,
        position=position,
        interview_style=style,
        metadata={
            "type": interview_type,
            "diff": difficulty,
            "model": model_key,
        },
    )

    if resume_text:
        file_name = data.get("file_name", "uploaded_resume")
        file_path = data.get("file_path", "")
        storage.save_resume(
            session_id=session_id,
            file_name=file_name,
            file_path=file_path or str(app_config.UPLOAD_DIR / f"{session_id}_resume.txt"),
            resume_text=resume_text,
        )

    _agents[session_id] = agent

    # 获取开场白
    greeting = agent.get_greeting()
    storage.save_message(session_id, "assistant", greeting)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "greeting": greeting,
        "model": provider.label,
        "style": style,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """发送消息，SSE 流式返回"""
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    message = data.get("message", "")

    if not session_id or not message:
        return jsonify({"error": "缺少 session_id 或 message"}), 400

    agent = _agents.get(session_id)
    if not agent:
        return jsonify({"error": "会话不存在或已过期"}), 404

    _stop_flags[session_id] = False

    def generate():
        full_response = ""
        try:
            resume_text = ""
            resume_data = storage.get_session_resume(session_id)
            if resume_data:
                resume_text = summarize_resume(resume_data.get("resume_text", ""))

            for chunk_type, chunk in agent.run_stream(message, context=resume_text):
                if _stop_flags.get(session_id):
                    break
                if chunk_type == "content":
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"
                elif chunk_type == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'text': chunk})}\n\n"

            # 保存消息
            storage.save_message(session_id, "user", message)
            storage.save_message(session_id, "assistant", full_response)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/chat-stop", methods=["POST"])
def stop_chat():
    """停止生成"""
    data = request.get_json() or {}
    sid = data.get("session_id", "")
    if sid:
        _stop_flags[sid] = True
    return jsonify({"success": True})


@app.route("/api/end", methods=["POST"])
def end_interview():
    """结束面试并生成报告"""
    data = request.get_json() or {}
    session_id = data.get("session_id", "")

    agent = _agents.get(session_id)
    if not agent:
        return jsonify({"error": "会话不存在"}), 404

    # 生成评估
    eval_result = agent.evaluate_interview()

    if eval_result:
        for ev in eval_result.get("evaluations", []):
            storage.save_evaluation(session_id, ev["dimension"], ev["score"], ev.get("comment", ""))

    storage.end_session(session_id)

    # 清理
    _agents.pop(session_id, None)
    _stop_flags.pop(session_id, None)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "report": eval_result,
    })


@app.route("/api/report/<session_id>")
def get_report(session_id):
    """获取评估报告"""
    session_info = storage.get_session_info(session_id)
    if not session_info:
        return jsonify({"error": "会话不存在"}), 404

    evaluations = storage.get_session_evaluations(session_id)
    statistics = storage.get_session_statistics(session_id)
    history = storage.get_session_history(session_id)

    return jsonify({
        "session": session_info,
        "evaluations": evaluations,
        "statistics": statistics,
        "history": history,
    })


@app.route("/api/sessions")
def list_sessions():
    """列出所有会话"""
    sessions = storage.list_sessions(limit=50)
    return jsonify(sessions)


# ── 启动 ──

if __name__ == "__main__":
    port = int(os.getenv("PROVIEW_API_PORT", "5000"))
    host = os.getenv("PROVIEW_API_HOST", "127.0.0.1")
    print(f"\n{'='*50}")
    print(f"  ProView API Server")
    print(f"  http://{host}:{port}")
    print(f"  Models: {[p['label'] for p in list_available_providers() if p['available']]}")
    print(f"{'='*50}\n")
    app.run(host=host, port=port, debug=False)
