<template>
  <div class="setup-page">
    <!-- 标题区 -->
    <div class="setup-hero">
      <span class="setup-badge">面试配置</span>
      <h1>准备开始沉浸式面试</h1>
      <p>先上传简历，再选择面试模式、风格和大模型，AI 面试官会基于简历内容进行针对性提问。</p>
    </div>

    <!-- 步骤 1: 简历上传 -->
    <section class="setup-section">
      <div class="section-head">
        <span class="step-num">01</span>
        <h2>上传简历</h2>
        <span class="hint">支持 PDF / Word / TXT / Markdown / 图片</span>
      </div>

      <div v-if="!resumeText" class="upload-zone" @click="$refs.fileInput.click()" @dragover.prevent @drop.prevent="handleDrop">
        <input ref="fileInput" type="file" accept=".pdf,.docx,.doc,.txt,.md,.jpg,.jpeg,.png,.bmp,.webp" hidden @change="handleFile" />
        <div class="upload-icon">📄</div>
        <p class="upload-title">{{ uploading ? '解析中...' : '点击或拖拽上传简历' }}</p>
        <p class="upload-hint">PDF, Word (.docx), TXT, Markdown (.md), 图片 (JPG/PNG/BMP/WEBP)</p>
        <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
      </div>

      <div v-else class="resume-loaded">
        <div class="resume-preview">
          <div class="resume-preview-head">
            <span class="resume-icon">📄</span>
            <div>
              <strong>{{ resumeFileName }}</strong>
              <span class="resume-char-count">{{ resumeText.length }} 字符</span>
            </div>
            <button class="btn-ghost" @click="clearResume">✕ 重新上传</button>
          </div>
          <div class="resume-preview-text">{{ resumeText.slice(0, 500) }}{{ resumeText.length > 500 ? '...' : '' }}</div>
        </div>
      </div>
    </section>

    <!-- 步骤 2: 面试配置 -->
    <section class="setup-section">
      <div class="section-head">
        <span class="step-num">02</span>
        <h2>面试配置</h2>
        <span class="hint">选择面试类型、风格和 AI 模型</span>
      </div>

      <div class="config-grid">
        <!-- 面试类型 -->
        <div class="config-card">
          <label class="config-label">面试类型</label>
          <div class="chip-group">
            <button
              v-for="opt in typeOptions" :key="opt.value"
              class="chip" :class="{ active: config.interview_type === opt.value }"
              @click="config.interview_type = opt.value"
            >
              <span class="chip-emoji">{{ opt.emoji }}</span>
              <span class="chip-label">{{ opt.label }}</span>
            </button>
          </div>
          <p class="chip-desc">{{ currentType.desc }}</p>
        </div>

        <!-- 难度 -->
        <div class="config-card">
          <label class="config-label">难度级别</label>
          <div class="chip-group">
            <button
              v-for="opt in diffOptions" :key="opt.value"
              class="chip" :class="{ active: config.difficulty === opt.value }"
              @click="config.difficulty = opt.value"
            >
              <span class="chip-emoji">{{ opt.emoji }}</span>
              <span class="chip-label">{{ opt.label }}</span>
            </button>
          </div>
          <p class="chip-desc">{{ currentDiff.desc }}</p>
        </div>

        <!-- 面试风格 -->
        <div class="config-card config-card--full">
          <label class="config-label">面试风格</label>
          <div class="style-grid">
            <button
              v-for="s in styles" :key="s.key"
              class="style-card" :class="{ active: config.style === s.key }"
              @click="config.style = s.key"
            >
              <span class="style-emoji">{{ styleEmojis[s.key] || '📘' }}</span>
              <div>
                <strong>{{ s.name }}</strong>
                <small>{{ s.desc }}</small>
              </div>
            </button>
          </div>
        </div>

        <!-- AI 模型 -->
        <div class="config-card">
          <label class="config-label">AI 大模型</label>
          <div class="chip-group">
            <button
              v-for="m in models" :key="m.key"
              class="chip" :class="{ active: config.model === m.key, disabled: !m.available }"
              :disabled="!m.available"
              @click="m.available && (config.model = m.key)"
            >
              <span class="chip-dot" :class="m.available ? 'dot-on' : 'dot-off'"></span>
              {{ m.label }}
            </button>
          </div>
          <p class="chip-desc">{{ currentModel?.desc || '选择可用的模型' }}</p>
        </div>

        <!-- 目标岗位 -->
        <div class="config-card">
          <label class="config-label">目标岗位</label>
          <input
            v-model="config.position"
            class="input-text"
            placeholder="如：后端开发工程师"
          />
        </div>
      </div>
    </section>

    <!-- 启动确认 -->
    <section class="setup-start">
      <div class="start-summary">
        <span class="summary-item">📄 {{ resumeText ? '简历已上传' : '❌ 未上传简历' }}</span>
        <span class="summary-item">🤖 {{ currentModel?.label || '未选择模型' }}</span>
        <span class="summary-item">🎯 {{ currentType.label }} / {{ currentDiff.label }} / {{ currentStyle?.name || '标准' }}</span>
        <span class="summary-item">💼 {{ config.position || '岗位待填写' }}</span>
      </div>

      <button class="btn-start" :disabled="starting || !canStart" @click="handleStart">
        <span v-if="starting" class="spinner"></span>
        {{ starting ? '初始化中...' : '▶ 开始沉浸式面试' }}
      </button>
      <p v-if="startError" class="start-error">{{ startError }}</p>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { healthCheck, listModels, listStyles, uploadResume, setupInterview } from '../services/api'

const router = useRouter()

// 简历
const resumeText = ref('')
const resumeFileName = ref('')
const resumeFilePath = ref('')
const uploading = ref(false)
const uploadError = ref('')

// 配置
const config = reactive({
  interview_type: 'technical',
  difficulty: 'mid',
  style: 'default',
  model: 'deepseek',
  position: '',
})

// 远程数据
const models = ref([])
const styles = ref([])

// 启动状态
const starting = ref(false)
const startError = ref('')

// 选项
const typeOptions = [
  { value: 'technical', label: '技术面', emoji: '💻', desc: '代码能力与技术深度' },
  { value: 'hr', label: 'HR面', emoji: '🤝', desc: '职业动机与稳定性' },
  { value: 'manager', label: '主管面', emoji: '📋', desc: '业务理解与协作能力' },
]
const diffOptions = [
  { value: 'junior', label: '初级', emoji: '🌱', desc: '基础概念与常见实践' },
  { value: 'mid', label: '中级', emoji: '🚀', desc: '实战经验与原理理解' },
  { value: 'senior', label: '高级', emoji: '🧭', desc: '架构能力与系统思考' },
]
const styleEmojis = {
  default: '📘', strict: '🎯', friendly: '🌤', technical_deep: '🧠',
  behavioral: '🗣', system_design: '🏗', rapid_fire: '⚡', project_focused: '📂',
}

const currentType = computed(() => typeOptions.find(o => o.value === config.interview_type) || typeOptions[0])
const currentDiff = computed(() => diffOptions.find(o => o.value === config.difficulty) || diffOptions[0])
const currentStyle = computed(() => styles.value.find(s => s.key === config.style))
const currentModel = computed(() => models.value.find(m => m.key === config.model))
const canStart = computed(() => resumeText.value && models.value.some(m => m.available))

// 文件处理
async function handleFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  await processFile(file)
}
function handleDrop(e) {
  const file = e.dataTransfer.files?.[0]
  if (file) processFile(file)
}
async function processFile(file) {
  uploadError.value = ''
  uploading.value = true
  try {
    const result = await uploadResume(file)
    if (result.error) { uploadError.value = result.error; return }
    resumeText.value = result.resume_text
    resumeFileName.value = result.file_name
    resumeFilePath.value = result.file_path
  } catch (e) {
    uploadError.value = e.message
  } finally {
    uploading.value = false
  }
}
function clearResume() {
  resumeText.value = ''
  resumeFileName.value = ''
  resumeFilePath.value = ''
}

// 启动面试
async function handleStart() {
  if (!canStart.value || starting.value) return
  starting.value = true
  startError.value = ''

  try {
    const result = await setupInterview({
      model: config.model,
      style: config.style,
      position: config.position,
      interview_type: config.interview_type,
      difficulty: config.difficulty,
      resume_text: resumeText.value,
      file_name: resumeFileName.value,
      file_path: resumeFilePath.value,
    })

    // 保存到 sessionStorage 以便其他页面使用
    sessionStorage.setItem('proview_session_id', result.session_id)
    sessionStorage.setItem('proview_interview_config', JSON.stringify({
      ...config,
      greeting: result.greeting,
      model_label: result.model,
    }))

    router.push('/interview')
  } catch (e) {
    startError.value = e.message
  } finally {
    starting.value = false
  }
}

// 初始化
onMounted(async () => {
  try {
    await healthCheck()
  } catch { /* ignore */ }
  try {
    models.value = await listModels()
  } catch { /* ignore */ }
  try {
    styles.value = await listStyles()
  } catch { /* ignore */ }
})
</script>

<style scoped>
.setup-page { max-width: 800px; margin: 0 auto; padding: 40px 24px; }
.setup-hero { text-align: center; margin-bottom: 48px; }
.setup-badge {
  display: inline-block; padding: 4px 14px; border-radius: 99px;
  background: var(--accent-soft); color: var(--accent); font-size: 13px; font-weight: 600;
  letter-spacing: 0.04em; margin-bottom: 16px;
}
.setup-hero h1 {
  font-size: 28px; font-weight: 800; margin: 0 0 8px;
  background: linear-gradient(135deg, #10b981, #059669);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.setup-hero p { color: var(--text-secondary); font-size: 15px; margin: 0; }

/* 分区 */
.setup-section {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 28px; margin-bottom: 24px;
}
.section-head { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.step-num {
  width: 36px; height: 36px; border-radius: 10px; background: var(--accent-soft);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px;
}
.section-head h2 { font-size: 18px; font-weight: 700; color: var(--text); margin: 0; }
.section-head .hint { color: var(--text-muted); font-size: 13px; margin-left: auto; }

/* 上传区域 */
.upload-zone {
  border: 2px dashed var(--border); border-radius: 16px; padding: 48px;
  text-align: center; cursor: pointer; transition: border-color 0.2s;
}
.upload-zone:hover { border-color: var(--accent); background: var(--accent-soft); }
.upload-icon { font-size: 48px; margin-bottom: 12px; }
.upload-title { font-size: 16px; font-weight: 600; color: var(--text); margin: 0 0 4px; }
.upload-hint { font-size: 13px; color: var(--text-muted); margin: 0; }
.upload-error { color: var(--danger); font-size: 13px; margin-top: 8px; }

/* 简历已加载 */
.resume-loaded { border: 1px solid var(--border); border-radius: 16px; overflow: hidden; }
.resume-preview-head {
  display: flex; align-items: center; gap: 12px; padding: 14px 20px;
  background: var(--surface-2); border-bottom: 1px solid var(--border);
}
.resume-icon { font-size: 24px; }
.resume-char-count { display: block; font-size: 12px; color: var(--text-muted); }
.resume-preview-text {
  padding: 16px 20px; font-size: 14px; line-height: 1.7; color: var(--text-secondary);
  max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;
}

/* 配置卡片 */
.config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.config-card { }
.config-card--full { grid-column: 1 / -1; }
.config-label { display: block; font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 10px; }

/* Chip 按钮 */
.chip-group { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  padding: 8px 16px; border-radius: 12px; border: 1.5px solid var(--border);
  background: var(--surface); cursor: pointer; font-size: 14px; font-weight: 600;
  color: var(--text-secondary); transition: all 0.15s;
  display: flex; align-items: center; gap: 6px;
}
.chip:hover { border-color: var(--accent); color: var(--text); }
.chip.active { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
.chip.disabled { opacity: 0.4; cursor: not-allowed; }
.chip-emoji { font-size: 16px; }
.chip-desc { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
.chip-dot { width: 8px; height: 8px; border-radius: 50%; }
.dot-on { background: #22c55e; }
.dot-off { background: #94a3b8; }

/* 风格卡片 */
.style-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.style-card {
  padding: 14px 12px; border-radius: 14px; border: 1.5px solid var(--border);
  background: var(--surface); cursor: pointer; text-align: left; transition: all 0.15s;
}
.style-card:hover { border-color: var(--accent); }
.style-card.active { border-color: var(--accent); background: var(--accent-soft); }
.style-emoji { font-size: 24px; display: block; margin-bottom: 6px; }
.style-card strong { display: block; font-size: 13px; color: var(--text); }
.style-card small { display: block; font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* 输入 */
.input-text {
  width: 100%; padding: 10px 16px; border-radius: 12px; border: 1.5px solid var(--border);
  font-size: 14px; background: var(--surface); color: var(--text); outline: none; box-sizing: border-box;
}
.input-text:focus { border-color: var(--accent); }

/* 启动区域 */
.setup-start {
  background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
  padding: 28px; text-align: center;
}
.start-summary { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; }
.summary-item {
  padding: 6px 14px; border-radius: 99px; background: var(--surface-2);
  font-size: 13px; color: var(--text-secondary); border: 1px solid var(--border);
}
.btn-start {
  padding: 14px 48px; border-radius: 16px; font-size: 16px; font-weight: 700;
  background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none;
  cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
  transition: all 0.2s; box-shadow: 0 4px 16px rgba(16,185,129,.25);
}
.btn-start:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(16,185,129,.35); }
.btn-start:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
.btn-ghost {
  padding: 6px 14px; border-radius: 8px; border: 1px solid var(--border);
  background: transparent; cursor: pointer; font-size: 13px; color: var(--text-secondary);
  margin-left: auto;
}
.start-error { color: var(--danger); font-size: 13px; margin-top: 10px; }

/* Spinner */
.spinner {
  width: 18px; height: 18px; border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 640px) {
  .config-grid { grid-template-columns: 1fr; }
  .style-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
