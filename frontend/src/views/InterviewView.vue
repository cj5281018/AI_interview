<template>
  <div class="interview-room">
    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="top-bar-left">
        <span class="rec-dot"></span>
        <span class="rec-text">面试中</span>
        <span class="timer">{{ formattedTime }}</span>
      </div>
      <div class="top-bar-center">
        <span class="mode-badge" :class="'mode-' + interviewConfig.style">
          {{ currentStyleName }}
        </span>
        <span class="model-badge">{{ interviewConfig.model_label || 'AI' }}</span>
      </div>
      <div class="top-bar-right">
        <button class="btn-end" @click="showEndModal = true">🛑 结束面试</button>
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-area" ref="chatArea">
      <div class="messages" v-if="messages.length">
        <div
          v-for="(msg, i) in messages" :key="i"
          class="message" :class="msg.role"
        >
          <div class="msg-avatar">{{ msg.role === 'assistant' ? '🤖' : '👤' }}</div>
          <div class="msg-content">
            <div class="msg-text">{{ msg.content }}</div>
            <div v-if="msg.thinking" class="msg-thinking">
              <details>
                <summary>🧠 思考过程</summary>
                <pre>{{ msg.thinking }}</pre>
              </details>
            </div>
          </div>
        </div>

        <!-- 流式输出中的 AI 消息 -->
        <div v-if="streaming" class="message assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-content">
            <div class="msg-text">
              {{ streamingText || '▌' }}
              <span v-if="!streamingText" class="typing-dots"><span>.</span><span>.</span><span>.</span></span>
            </div>
            <div v-if="thinkingText" class="msg-thinking">
              <details open>
                <summary>🧠 思考过程</summary>
                <pre>{{ thinkingText }}</pre>
              </details>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!messages.length && !streaming" class="chat-empty">
        <div class="empty-icon">🤖</div>
        <p>面试即将开始，请等待 AI 面试官提问...</p>
      </div>
    </div>

    <!-- 输入区：textare实现多行输入+自动换行 -->
    <div class="input-area">
      <textarea
        v-model="userInput"
        class="chat-input"
        placeholder="输入你的回答...（Shift+Enter 换行，Enter 发送）"
        :disabled="streaming || ending"
        rows="1"
        ref="inputEl"
        @input="autoResize"
        @keydown="handleKeydown"
      ></textarea>
      <button
        class="btn-send"
        :disabled="!userInput.trim() || streaming || ending"
        @click="sendMessage"
      >
        <span v-if="streaming">⏳</span>
        <span v-else>📤</span>
      </button>
      <button
        v-if="streaming"
        class="btn-stop"
        @click="stopStream"
      >
        ⏹ 停止
      </button>
    </div>

    <!-- 结束确认弹窗 -->
    <div v-if="showEndModal" class="modal-overlay" @click.self="showEndModal = false">
      <div class="modal-card">
        <h3>🛑 结束面试</h3>
        <p>你可以选择保存面试历史并生成评估报告，或不保存直接结束。</p>
        <p v-if="endError" class="error-text">{{ endError }}</p>
        <div class="modal-actions">
          <button class="btn-ghost" @click="showEndModal = false">↩️ 继续面试</button>
          <button class="btn-danger" @click="endInterview(false)">🗑️ 不保存</button>
          <button class="btn-primary" :disabled="ending" @click="endInterview(true)">
            {{ ending ? '⏳ 生成报告中...' : '💾 保存并生成报告' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { chatStream, endInterview as apiEnd } from '../services/api'

const router = useRouter()

const interviewConfig = ref({})
const sessionId = ref('')
const styleNames = {
  default: '标准模式', strict: '高压模式', friendly: '温和引导',
  technical_deep: '技术深挖', behavioral: '行为面试',
  system_design: '系统设计', rapid_fire: '快问快答', project_focused: '项目追问',
}
const currentStyleName = computed(() => styleNames[interviewConfig.value.style] || '标准')

const messages = ref([])
const userInput = ref('')
const streaming = ref(false)
const streamingText = ref('')
const thinkingText = ref('')
const inputEl = ref(null)
let currentStream = null

const elapsed = ref(0)
let timer = null
const formattedTime = computed(() => {
  const m = Math.floor(elapsed.value / 60).toString().padStart(2, '0')
  const s = (elapsed.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const showEndModal = ref(false)
const ending = ref(false)
const endError = ref('')
const chatArea = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (chatArea.value) {
      chatArea.value.scrollTop = chatArea.value.scrollHeight
    }
  })
}

/* textarea 自动调高度 */
function autoResize() {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

/* 键盘事件：Enter 发送，Shift+Enter 换行 */
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || streaming.value || ending.value) return

  messages.value.push({ role: 'user', content: text })
  userInput.value = ''
  // 重置 textarea 高度
  nextTick(() => {
    if (inputEl.value) { inputEl.value.style.height = 'auto' }
  })
  scrollToBottom()

  streaming.value = true
  streamingText.value = ''
  thinkingText.value = ''

  try {
    currentStream = chatStream(sessionId.value, text)
    for await (const chunk of currentStream) {
      if (chunk.type === 'thinking') {
        thinkingText.value += chunk.text
      } else if (chunk.type === 'content') {
        streamingText.value += chunk.text
        scrollToBottom()
      } else if (chunk.type === 'done') {
        /* 完成 */
      } else if (chunk.type === 'error') {
        streamingText.value += `\n[错误: ${chunk.text}]`
      }
    }
    if (streamingText.value) {
      messages.value.push({
        role: 'assistant', content: streamingText.value,
        thinking: thinkingText.value || '',
      })
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', content: `[请求失败: ${e.message}]` })
    }
  }

  streaming.value = false
  streamingText.value = ''
  thinkingText.value = ''
  currentStream = null
  scrollToBottom()
}

function stopStream() {
  if (currentStream?.cancel) currentStream.cancel()
  if (streamingText.value) {
    messages.value.push({
      role: 'assistant',
      content: streamingText.value + ' [已停止]',
      thinking: thinkingText.value || '',
    })
  }
  streaming.value = false
  streamingText.value = ''
  thinkingText.value = ''
  currentStream = null
}

async function endInterview(save) {
  ending.value = true
  endError.value = ''
  try {
    if (save) {
      const result = await apiEnd(sessionId.value)
      sessionStorage.setItem('proview_report', JSON.stringify(result.report || {}))
    }
    sessionStorage.setItem('proview_report_session_id', sessionId.value)
    router.push('/report')
  } catch (e) {
    endError.value = e.message
    ending.value = false
  }
}

onMounted(() => {
  const raw = sessionStorage.getItem('proview_interview_config')
  if (!raw) { router.replace('/'); return }
  interviewConfig.value = JSON.parse(raw)
  sessionId.value = sessionStorage.getItem('proview_session_id') || ''
  if (interviewConfig.value.greeting) {
    messages.value.push({ role: 'assistant', content: interviewConfig.value.greeting })
  }
  timer = setInterval(() => { elapsed.value++ }, 1000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  if (currentStream?.cancel) currentStream.cancel()
})
</script>

<style scoped>
.interview-room {
  display: flex; flex-direction: column; height: 100vh;
  max-width: 900px; margin: 0 auto;
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(8px);
}

/* 顶部状态栏 */
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px;
  background: rgba(255,255,255,0.85); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 10;
  backdrop-filter: blur(8px);
}
.top-bar-left { display: flex; align-items: center; gap: 10px; }
.rec-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--pink); animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.rec-text { font-size: 12px; font-weight: 700; color: var(--pink); letter-spacing: 0.1em; }
.timer { font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--text); }

.mode-badge {
  padding: 4px 14px; border-radius: 99px; font-size: 12px; font-weight: 600;
}
.mode-default         { background:#ecfdf5; color:#059669; }
.mode-strict          { background:#fef2f2; color:#dc2626; }
.mode-friendly        { background:#ecfdf5; color:#059669; }
.mode-technical_deep  { background:#fdf2f8; color:#be185d; }
.mode-behavioral      { background:#ecfeff; color:#0891b2; }
.mode-system_design   { background:#fffbeb; color:#d97706; }
.mode-rapid_fire      { background:#fefce8; color:#ca8a04; }
.mode-project_focused { background:#fdf2f8; color:#db2777; }
.model-badge { font-size: 12px; color: var(--text-muted); margin-left: 8px; }

.btn-end {
  padding: 8px 16px; border-radius: 10px;
  background: var(--pink-soft); color: var(--pink);
  border: 1px solid rgba(236,72,153,.2); cursor: pointer;
  font-size: 13px; font-weight: 600; transition: all 0.15s;
}
.btn-end:hover { background: rgba(236,72,153,.12); }

/* 聊天区域 */
.chat-area { flex: 1; overflow-y: auto; padding: 24px; }
.messages { display: flex; flex-direction: column; gap: 16px; }
.message { display: flex; gap: 12px; max-width: 80%; animation: fadeUp 0.3s ease-out; }
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message.assistant { align-self: flex-start; }
@keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

.msg-avatar {
  width: 40px; height: 40px; border-radius: 14px; display: flex;
  align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;
}
.message.user .msg-avatar { background: var(--accent-soft); }
.message.assistant .msg-avatar { background: var(--pink-soft); }

.msg-content { flex: 1; min-width: 0; overflow-wrap: break-word; word-wrap: break-word; }
.msg-text {
  padding: 14px 18px; border-radius: 20px; font-size: 15px; line-height: 1.75;
  white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;
}
.message.user .msg-text {
  background: linear-gradient(135deg, #10b981, #059669); color: #fff;
  border-bottom-right-radius: 6px;
}
.message.assistant .msg-text {
  background: var(--surface); border: 1px solid var(--border);
  border-bottom-left-radius: 6px; color: var(--text);
}

.msg-thinking { margin-top: 8px; }
.msg-thinking details { font-size: 13px; }
.msg-thinking summary {
  color: var(--accent); cursor: pointer; font-size: 12px; font-weight: 600;
}
.msg-thinking pre {
  background: var(--accent-soft); border-radius: 10px; padding: 12px; margin-top: 6px;
  font-size: 12px; line-height: 1.6; color: var(--text-secondary);
  white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto;
}

.typing-dots span { animation: dotBlink 1.4s infinite; opacity: 0; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBlink { 0%,20%{opacity:0} 50%{opacity:1} 100%{opacity:0} }

.chat-empty { text-align: center; padding: 80px 20px; color: var(--text-muted); }
.empty-icon { font-size: 64px; margin-bottom: 16px; }

/* 输入区 */
.input-area {
  display: flex; align-items: flex-end; gap: 10px; padding: 16px 24px;
  background: rgba(255,255,255,0.85); border-top: 1px solid var(--border);
  position: sticky; bottom: 0; backdrop-filter: blur(8px);
}
.chat-input {
  flex: 1; padding: 12px 18px; border-radius: 16px;
  border: 1.5px solid var(--border); font-size: 15px; line-height: 1.6;
  background: var(--bg); color: var(--text); outline: none;
  resize: none; overflow-y: auto;
  min-height: 46px; max-height: 160px;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.chat-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(16,185,129,.12);
}
.chat-input:disabled { opacity: 0.5; }
.chat-input::placeholder { color: var(--text-muted); }

.btn-send, .btn-stop {
  height: 46px; border-radius: 16px; border: none; cursor: pointer;
  font-size: 18px; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: all 0.15s;
}
.btn-send {
  width: 52px; background: var(--accent); color: #fff;
}
.btn-send:hover:not(:disabled) { background: var(--accent-hover); transform: scale(1.04); }
.btn-send:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-stop {
  width: auto; padding: 0 18px;
  background: var(--pink-soft); color: var(--pink);
  font-size: 14px; font-weight: 700;
}
.btn-stop:hover { background: rgba(236,72,153,.15); }

/* 弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(45,36,24,.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.modal-card {
  background: var(--surface); border-radius: 24px; padding: 36px;
  max-width: 480px; width: 90%;
  box-shadow: 0 24px 80px rgba(0,0,0,.12);
  border: 1px solid var(--border);
}
.modal-card h3 { font-size: 22px; font-weight: 800; margin: 0 0 12px; color: var(--text); }
.modal-card p { font-size: 14px; color: var(--text-secondary); line-height: 1.7; }
.modal-actions { display: flex; gap: 10px; margin-top: 28px; }
.btn-primary, .btn-danger, .btn-ghost {
  flex: 1; padding: 13px 16px; border-radius: 14px; font-size: 14px; font-weight: 700;
  border: none; cursor: pointer; transition: all 0.15s;
}
.btn-primary {
  background: linear-gradient(135deg, #10b981, #059669); color: #fff;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); }
.btn-danger {
  background: var(--danger-soft); color: var(--danger);
  border: 1px solid rgba(239,68,68,.15);
}
.btn-danger:hover { background: rgba(239,68,68,.1); }
.btn-ghost {
  background: var(--surface-2); color: var(--text-secondary);
  border: 1px solid var(--border);
}
.btn-ghost:hover { background: var(--border); }
.error-text { color: var(--danger); font-size: 13px; margin-top: 8px; }

@media (max-width: 640px) {
  .message { max-width: 92%; }
  .modal-actions { flex-direction: column; }
}
</style>
