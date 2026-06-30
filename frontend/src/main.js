import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'

import SetupView from './views/SetupView.vue'
import InterviewView from './views/InterviewView.vue'
import ReportView from './views/ReportView.vue'

const routes = [
  { path: '/', name: 'setup', component: SetupView },
  { path: '/interview', name: 'interview', component: InterviewView },
  { path: '/report', name: 'report', component: ReportView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 导航守卫：未设置面试配置不能进面试房间
router.beforeEach((to) => {
  if (to.name === 'interview') {
    const config = sessionStorage.getItem('proview_interview_config')
    if (!config) return '/'
  }
  if (to.name === 'report') {
    const reportData = sessionStorage.getItem('proview_report')
    const sessionId = sessionStorage.getItem('proview_session_id')
    if (!reportData && !sessionId) return '/'
  }
})

const app = createApp(App)
app.use(router)
app.mount('#app')
