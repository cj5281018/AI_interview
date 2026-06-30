# 🤖 AI 在线面试官

基于大模型的智能模拟面试系统，支持 **DeepSeek + 阿里云通义千问** 双模型热切换、**8 种面试风格** Prompt 模板化切换、**SSE 双通道流式对话**（推理过程 + 正式回复分离）和 **PaddleOCR v2 简历解析管线**。

---

## 功能概览

| 模块 | 功能 |
|---|---|
| 🎤 **AI 面试** | 上传简历 → 选择面试风格/难度/模型 → 流式多轮对话 → 自动生成 5 维评估报告 |
| 📄 **简历解析** | 支持 PDF/DOCX/TXT/MD/JPG/PNG 9 种格式，PaddleOCR v2 云端识别 + 4 层文本清洗管线 |
| 🎯 **面试风格** | 8 种预设风格（标准/高压/温和/技术深挖/行为面试/系统设计/快问快答/项目追问）+ 6 套场景预设 |
| 🤖 **多模型** | 注册表模式管理，DeepSeek + 通义千问一键切换，新增模型仅需 1 行配置 |
| 📊 **评估报告** | 面试结束后自动生成技术深度/沟通表达/逻辑思维/项目经验/学习潜力 5 维度评分 |
| 💬 **流式对话** | SSE 双通道流式——推理过程折叠展示 + 正式回复打字机效果 |
| 🧠 **LLM 简历分析** | 结构化分段 + 6 类问题检测 + 优化建议 + Builder 数据提取 |

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + 纯 CSS Variables |
| 后端 | Flask + SSE 流式 |
| AI | DeepSeek API / 阿里云通义千问 API（OpenAI 兼容协议） |
| OCR | PaddleOCR v2 云端 API |
| 存储 | SQLite（零配置，本地运行） |
| Prompt 工程 | 结构化 JSON 配置 + 运行时动态注入 |

---

## 项目结构

```
AI_interviewer/
├── backend/
│   └── app.py                     # Flask API 后端（10 REST + 1 SSE）
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── SetupView.vue      # 面试配置页
│       │   ├── InterviewView.vue  # 面试房间
│       │   └── ReportView.vue     # 评估报告页
│       ├── services/api.js        # API 调用层（含 SSE 流式）
│       └── App.vue                # 根组件 + 侧边栏导航
├── core/
│   ├── interview_agent.py         # AI 面试官核心
│   ├── llm_client.py              # OpenAI 兼容 LLM 客户端
│   ├── model_registry.py          # 多模型注册表
│   ├── storage.py                 # SQLite 持久化
│   ├── resume_analyzer.py         # LLM 简历结构化分析
│   ├── ocr_processor.py           # PaddleOCR v2 云识别
│   └── prompts.json               # 8 种风格 Prompt 模板
├── services/
│   ├── resume_text_extraction.py  # 简历文本提取 + 清洗管线
│   ├── resume_parser.py           # 简历摘要 + 预览
│   └── career_service.py          # 职业规划服务
├── config.py                      # 全局配置
├── .env.example                   # 环境变量模板
└── requirements.txt               # Python 依赖
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/cj5281018/AI_interview.git
cd AI_interview
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
copy .env.example .env
```

编辑 `.env`，至少配置一个 LLM 模型：

```env
# DeepSeek（推荐）
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 阿里云通义千问
ALIYUN_API_KEY=sk-your-key-here
ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# PaddleOCR（可选，用于图片/扫描版 PDF 简历解析）
PADDLEOCR_API_URL=https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
PADDLE_OCR_TOKEN=your-token-here
```

### 4. 启动后端

```bash
cd backend
python app.py
# 后端运行在 http://127.0.0.1:5000
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

浏览器访问 **http://localhost:5173** 即可使用。

---

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/models` | 可用模型列表 |
| GET | `/api/styles` | 面试风格列表 |
| POST | `/api/resume/upload` | 上传简历（返回解析文本） |
| POST | `/api/setup` | 创建面试会话 |
| POST | `/api/chat` | 发送消息（SSE 流式返回） |
| POST | `/api/chat-stop` | 停止生成 |
| POST | `/api/end` | 结束面试（生成报告） |
| GET | `/api/report/<sid>` | 获取评估报告 |
| GET | `/api/sessions` | 历史会话列表 |

---

## 用户流程

```
① 上传简历（PDF/DOCX/图片/TXT）
     ↓
② 选择面试风格 + 难度 + AI 模型
     ↓
③ 进入面试房间，AI 根据简历内容逐轮提问
     ↓  （SSE 流式 + 思维链折叠展示）
④ 结束时自动生成 5 维评估报告
```

---

## License

MIT
