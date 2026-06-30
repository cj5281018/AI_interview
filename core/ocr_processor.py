"""
OCR 图像识别模块 — 基于 PaddleOCR v2 REST API

API 端点: https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
认证方式: Authorization: bearer {TOKEN}
流程: 提交 job → 轮询状态 → 下载 JSONL 结果 → 解析 Markdown + 图片

配置: 在 .env 中设置 PADDLEOCR_API_URL 和 PADDLE_OCR_TOKEN
"""
import json
import os
import time
import requests
import config as app_config

OUTPUT_DIR = str(app_config.DATA_DIR / "ocr_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_ocr_runtime_settings() -> tuple[str, str]:
    """从 .env 读取 PaddleOCR 配置"""
    url = str(os.getenv("PADDLEOCR_API_URL") or "").strip()
    token = str(os.getenv("PADDLE_OCR_TOKEN") or "").strip()
    return url, token


def perform_ocr(image_path: str, use_preprocessing: bool = True, is_screen_capture: bool = False) -> str:
    """
    执行 OCR — PaddleOCR v2 异步 API

    1. POST 提交文件 → 获取 jobId
    2. 轮询 GET /api/v2/ocr/jobs/{jobId} → 等待 state=done
    3. 下载 JSONL → 提取 layoutParsingResults.markdown.text
    4. 保存 Markdown 和图片到本地
    """
    if not os.path.exists(image_path):
        return f"错误: 找不到文件 '{image_path}'"

    api_url, token = get_ocr_runtime_settings()
    if not api_url:
        return "错误: OCR API 地址未配置，请在 .env 中设置 PADDLEOCR_API_URL。"
    if not token:
        return "错误: OCR API 令牌未配置，请在 .env 中设置 PADDLE_OCR_TOKEN。"

    headers = {"Authorization": f"bearer {token}"}

    optional_payload = {
        "useDocOrientationClassify": use_preprocessing,
        "useDocUnwarping": use_preprocessing,
        "useChartRecognition": False,
    }

    # ── Step 1: 提交 job ──
    print(f"[OCR] 提交任务: {os.path.basename(image_path)}")
    try:
        data = {
            "model": "PaddleOCR-VL-1.6",
            "optionalPayload": json.dumps(optional_payload),
        }
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(api_url, headers=headers, data=data, files=files)

        if response.status_code != 200:
            print(f"[OCR][ERROR] 提交失败 HTTP {response.status_code}: {response.text[:300]}")
            return f"错误: OCR API 返回 HTTP {response.status_code}"

        job_id = response.json()["data"]["jobId"]
        print(f"[OCR] Job 已提交: {job_id}")
    except Exception as e:
        return f"错误: 提交 OCR 任务失败 - {str(e)}"

    # ── Step 2: 轮询状态 ──
    jsonl_url = ""
    max_polls = 120  # 最多等 10 分钟（120 × 5 秒）
    for attempt in range(max_polls):
        time.sleep(5)

        try:
            status_resp = requests.get(f"{api_url}/{job_id}", headers=headers)
            if status_resp.status_code != 200:
                continue

            state = status_resp.json()["data"]["state"]

            if state == "pending":
                if attempt == 0:
                    print("[OCR] 任务排队中...")
            elif state == "running":
                try:
                    progress = status_resp.json()['data']['extractProgress']
                    print(f"[OCR] 处理中: {progress.get('extractedPages', '?')}/{progress.get('totalPages', '?')} 页")
                except KeyError:
                    print("[OCR] 处理中...")
            elif state == "done":
                progress = status_resp.json()['data']['extractProgress']
                print(f"[OCR] 完成: {progress.get('extractedPages', '?')} 页")
                jsonl_url = status_resp.json()['data']['resultUrl']['jsonUrl']
                break
            elif state == "failed":
                error_msg = status_resp.json()['data'].get('errorMsg', '未知错误')
                return f"错误: OCR 任务失败 - {error_msg}"

        except Exception as e:
            print(f"[OCR][WARN] 轮询异常: {e}")

    if not jsonl_url:
        return "错误: OCR 任务超时（等待 10 分钟仍未完成）"

    # ── Step 3: 下载 JSONL 并解析 ──
    try:
        jsonl_resp = requests.get(jsonl_url)
        jsonl_resp.raise_for_status()

        markdown_texts = []
        lines = jsonl_resp.text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                result = json.loads(line)["result"]
                for res in result.get("layoutParsingResults", []):
                    md_text = res.get("markdown", {}).get("text", "")
                    if md_text:
                        markdown_texts.append(md_text)
            except (json.JSONDecodeError, KeyError):
                continue

        if not markdown_texts:
            return "解析成功，但未能从图片中提取到任何有效文本。"

        # 保存 Markdown 结果到本地
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_path = os.path.join(OUTPUT_DIR, f"{base_name}_ocr_result.md")
        final_md = "\n\n---\n\n".join(markdown_texts)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(final_md)

        print(f"[OCR] Markdown 已保存: {save_path}, 共 {len(final_md)} 字符")
        return f"【解析成功】Markdown 文档已自动保存至本地: {save_path}\n\n以下是提取的内容:\n\n{final_md}"

    except Exception as e:
        import traceback
        print(f"[OCR][ERROR] {traceback.format_exc()}")
        return f"错误: 下载/解析 OCR 结果失败 - {str(e)}"


def perform_ocr_full(image_path: str, use_preprocessing: bool = True, is_screen_capture: bool = False) -> dict:
    """
    执行 OCR 并返回完整结果（文本 + 图片 base64）— 供前端预览使用
    """
    text_result = perform_ocr(image_path, use_preprocessing, is_screen_capture)

    # 收集本地保存的图片并转 base64
    imgs_dir = os.path.join(OUTPUT_DIR, "imgs")
    images_b64 = {}
    if os.path.isdir(imgs_dir):
        import base64
        for fname in os.listdir(imgs_dir):
            fpath = os.path.join(imgs_dir, fname)
            try:
                with open(fpath, "rb") as f:
                    ext = os.path.splitext(fname)[1].lower().lstrip('.')
                    mime = f"image/{ext}" if ext in ('png', 'jpg', 'jpeg', 'webp') else "image/jpeg"
                    images_b64[fname] = f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"
            except Exception:
                pass

    return {"text": text_result, "images": images_b64}
