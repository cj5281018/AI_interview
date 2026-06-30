<template>
  <div class="report-page">
    <div class="report-hero">
      <span class="report-badge">评估报告</span>
      <h1>面试评估报告</h1>
      <p v-if="sessionInfo">{{ sessionInfo.position || '未知岗位' }} · {{ styleLabel }}</p>
      <p class="report-meta">本次面试共进行了 {{ statistics.turn_count || 0 }} 轮对话</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <template v-else>
      <!-- AI 总评 -->
      <div v-if="report.summary" class="summary-card">
        <h3>💬 AI 面试官总评</h3>
        <p>{{ report.summary }}</p>
      </div>

      <!-- 评分区域 -->
      <div class="score-section">
        <div class="score-main">
          <div class="score-circle">
            <svg viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="var(--border)" stroke-width="10" />
              <circle
                cx="60" cy="60" r="52" fill="none"
                :stroke="scoreColor"
                stroke-width="10"
                stroke-linecap="round"
                :stroke-dasharray="dashArray"
                :stroke-dashoffset="0"
                transform="rotate(-90 60 60)"
                style="transition: stroke-dashoffset 0.8s ease;"
              />
            </svg>
            <div class="score-text">
              <span class="score-number">{{ statistics.avg_score || 0 }}</span>
              <span class="score-max">/ 10</span>
            </div>
          </div>
          <p class="score-subtitle">综合评分</p>
        </div>

        <div class="dimension-list">
          <div v-for="ev in report.evaluations" :key="ev.dimension" class="dimension-row">
            <div class="dim-head">
              <span class="dim-name">{{ ev.dimension }}</span>
              <span class="dim-score" :style="{ color: scoreColorFor(ev.score) }">{{ ev.score }}/10</span>
            </div>
            <div class="dim-bar-bg">
              <div
                class="dim-bar-fill"
                :style="{ width: (ev.score * 10) + '%', background: scoreColorFor(ev.score) }"
              ></div>
            </div>
            <p v-if="ev.comment" class="dim-comment">{{ ev.comment }}</p>
          </div>
        </div>
      </div>

      <!-- 优劣势 -->
      <div v-if="report.strengths || report.weaknesses" class="insight-grid">
        <div v-if="report.strengths" class="insight-card insight-good">
          <h3>✅ 优势亮点</h3>
          <p>{{ report.strengths }}</p>
        </div>
        <div v-if="report.weaknesses" class="insight-card insight-warn">
          <h3>⚠️ 改进建议</h3>
          <p>{{ report.weaknesses }}</p>
        </div>
      </div>

      <!-- 对话回顾 -->
      <details class="history-details">
        <summary>💬 查看完整对话记录 ({{ history.length }} 条)</summary>
        <div class="history-list">
          <div v-for="(msg, i) in history" :key="i" class="history-item">
            <span class="h-role">{{ msg.role === 'user' ? '👤 候选人' : '🤖 面试官' }}</span>
            <p class="h-content">{{ msg.content }}</p>
          </div>
        </div>
      </details>
    </template>

    <div class="report-actions">
      <button class="btn-primary" @click="$router.push('/')">🔄 重新挑战</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getReport } from '../services/api'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const report = ref({})
const sessionInfo = ref(null)
const statistics = ref({})
const history = ref([])

const styleNames = {
  default: '标准模式', strict: '高压模式', friendly: '温和引导',
  technical_deep: '技术深挖', behavioral: '行为面试',
  system_design: '系统设计', rapid_fire: '快问快答', project_focused: '项目追问',
}
const styleLabel = computed(() => styleNames[sessionInfo.value?.interview_style] || '标准')

const scoreColor = computed(() => scoreColorFor(statistics.value.avg_score || 0))
const dashArray = computed(() => {
  const score = statistics.value.avg_score || 0
  const pct = score / 10
  const circumference = 2 * Math.PI * 52
  return `${circumference * pct} ${circumference * (1 - pct)}`
})

function scoreColorFor(score) {
  if (score >= 7) return '#10b981'
  if (score >= 5) return '#f59e0b'
  return '#ef4444'
}

onMounted(async () => {
  // 优先从 sessionStorage 获取
  const cachedReport = sessionStorage.getItem('proview_report')
  if (cachedReport) {
    try {
      const parsed = JSON.parse(cachedReport)
      if (parsed.evaluations?.length) {
        report.value = parsed
        statistics.value = { avg_score: parsed.evaluations.reduce((s, e) => s + e.score, 0) / parsed.evaluations.length, turn_count: 0 }
        loading.value = false
      }
    } catch { /* ignore */ }
  }

  const sid = sessionStorage.getItem('proview_report_session_id')
  if (!sid) {
    loading.value = false
    if (!report.value.evaluations?.length) {
      error.value = '暂无报告数据，请先完成一次面试'
    }
    return
  }

  try {
    const data = await getReport(sid)
    report.value = {
      evaluations: data.evaluations || [],
      strengths: data.session?.meta?.strengths || report.value.strengths || '',
      weaknesses: data.session?.meta?.weaknesses || report.value.weaknesses || '',
      summary: data.session?.meta?.summary || report.value.summary || '',
    }
    sessionInfo.value = data.session
    statistics.value = data.statistics
    history.value = data.history || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-page { max-width: 720px; margin: 0 auto; padding: 40px 24px; }
.report-hero { text-align: center; margin-bottom: 40px; }
.report-badge {
  display: inline-block; padding: 4px 14px; border-radius: 99px;
  background: var(--accent-soft); color: var(--accent); font-size: 13px; font-weight: 600;
  letter-spacing: 0.04em; margin-bottom: 16px;
}
.report-hero h1 {
  font-size: 28px; font-weight: 800; margin: 0 0 8px;
  background: linear-gradient(135deg, #10b981, #059669);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.report-hero p { color: var(--text-secondary); font-size: 15px; margin: 0; }
.report-meta {
  display: inline-block; margin-top: 12px; padding: 6px 16px; border-radius: 99px;
  font-size: 13px; color: var(--accent); background: var(--accent-soft);
}

.loading-state, .error-state { text-align: center; padding: 40px; color: var(--text-muted); }

/* 总评 */
.summary-card {
  background: linear-gradient(135deg, #ecfdf5, #f0fdf4); border: 1px solid #a7f3d0;
  border-radius: 16px; padding: 24px; margin-bottom: 32px;
}
.summary-card h3 { margin: 0 0 12px; font-size: 17px; color: #065f46; }
.summary-card p { margin: 0; font-size: 14px; line-height: 1.8; color: #064e3b; }

/* 评分 */
.score-section { display: grid; grid-template-columns: 200px 1fr; gap: 32px; margin-bottom: 32px; align-items: start; }
.score-main { text-align: center; }
.score-circle {
  position: relative; width: 160px; height: 160px; margin: 0 auto;
}
.score-circle svg { width: 100%; height: 100%; }
.score-text {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.score-number { font-size: 40px; font-weight: 900; color: var(--text); line-height: 1; }
.score-max { font-size: 14px; color: var(--text-muted); }
.score-subtitle { margin-top: 8px; font-size: 15px; font-weight: 700; color: var(--text); }

.dimension-list { display: flex; flex-direction: column; gap: 16px; }
.dimension-row {
  background: var(--surface-2); border-radius: 14px; padding: 14px 18px;
  border: 1px solid var(--border);
}
.dim-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.dim-name { font-size: 14px; font-weight: 700; color: var(--text); }
.dim-score { font-size: 14px; font-weight: 800; }
.dim-bar-bg {
  height: 10px; border-radius: 99px; background: var(--border); overflow: hidden;
}
.dim-bar-fill { height: 100%; border-radius: 99px; transition: width 0.6s ease; }
.dim-comment { font-size: 12px; color: var(--text-muted); margin: 6px 0 0; }

/* 优劣势 */
.insight-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px; }
.insight-card { border-radius: 16px; padding: 24px; }
.insight-good { background: linear-gradient(180deg, #f0fdf4, #ecfdf5); border: 1px solid #86efac; }
.insight-warn { background: linear-gradient(180deg, #fffbeb, #fefce8); border: 1px solid #fcd34d; }
.insight-card h3 { margin: 0 0 12px; font-size: 17px; }
.insight-good h3 { color: #166534; }
.insight-warn h3 { color: #92400e; }
.insight-card p { margin: 0; font-size: 14px; line-height: 1.8; color: var(--text-secondary); }

/* 对话回顾 */
.history-details { margin-bottom: 32px; }
.history-details summary {
  font-size: 15px; font-weight: 700; color: var(--text); cursor: pointer;
  padding: 14px 20px; background: var(--surface); border-radius: 14px; border: 1px solid var(--border);
}
.history-list { border: 1px solid var(--border); border-radius: 0 0 14px 14px; overflow: hidden; margin-top: -1px; }
.history-item { padding: 14px 20px; border-bottom: 1px solid var(--border); }
.history-item:last-child { border-bottom: none; }
.h-role { font-size: 12px; font-weight: 700; color: var(--text-muted); }
.h-content { font-size: 14px; line-height: 1.6; color: var(--text); margin: 4px 0 0; }

/* 操作 */
.report-actions { text-align: center; }
.btn-primary {
  padding: 14px 48px; border-radius: 16px; font-size: 16px; font-weight: 700;
  background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none;
  cursor: pointer; box-shadow: 0 4px 16px rgba(16,185,129,.25); transition: all 0.2s;
}
.btn-primary:hover { filter: brightness(1.08); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(16,185,129,.35); }

@media (max-width: 640px) {
  .score-section { grid-template-columns: 1fr; }
  .insight-grid { grid-template-columns: 1fr; }
}
</style>
