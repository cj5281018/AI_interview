"""
应用配置管理模块

从 .env 文件加载环境变量，提供统一的配置访问接口。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 文件
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # 如果没有 .env，尝试加载 .env.example 中的默认值
    example_path = BASE_DIR / ".env.example"
    if example_path.exists():
        load_dotenv(example_path)

# ── 数据目录 ──
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "interviews.db"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _read_env(key: str, default: str = "") -> str:
    """读取环境变量，去除首尾空格"""
    value = os.getenv(key)
    if value is None:
        return default
    return str(value).strip() or default


# ── LLM 配置 ──
DEEPSEEK_API_KEY = _read_env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _read_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

ALIYUN_API_KEY = _read_env("ALIYUN_API_KEY")
ALIYUN_BASE_URL = _read_env("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── OCR 配置 ──
PADDLEOCR_API_URL = _read_env("PADDLEOCR_API_URL")
PADDLE_OCR_TOKEN = _read_env("PADDLE_OCR_TOKEN")

# ── 应用配置 ──
LOCAL_USER_NAME = _read_env("LOCAL_USER_NAME", "本地用户")
APP_PORT = int(_read_env("APP_PORT", "8501"))


# ── 密钥掩码（用于安全显示）──
def mask_secret(value: str) -> str:
    """对敏感信息进行掩码处理"""
    raw = str(value or "").strip()
    if not raw:
        return "(未配置)"
    if len(raw) <= 8:
        return "*" * len(raw)
    return f"{raw[:4]}{'*' * max(4, len(raw) - 8)}{raw[-4:]}"
