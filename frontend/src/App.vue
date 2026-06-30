<template>
  <div class="app-shell">
    <!-- 侧边栏导航 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-brand" @click="$router.push('/')">
        <span class="brand-icon">🤖</span>
        <span v-if="!sidebarCollapsed" class="brand-text">AI在线面试官</span>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="item in navItems" :key="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path, disabled: item.disabled }"
          :disabled="item.disabled"
          @click="navigate(item)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
          <span v-if="!sidebarCollapsed && item.hint" class="nav-hint">{{ item.hint }}</span>
        </button>
      </nav>

      <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
        {{ sidebarCollapsed ? '▶' : '◀' }}
      </button>
    </aside>

    <!-- 主内容 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const sidebarCollapsed = ref(false)

const hasConfig = computed(() => !!sessionStorage.getItem('proview_interview_config'))

const navItems = computed(() => [
  { path: '/', icon: '⚙️', label: '面试配置', disabled: false },
  { path: '/interview', icon: '💬', label: '面试房间', disabled: !hasConfig.value, hint: hasConfig.value ? '' : '需先配置' },
  { path: '/report', icon: '📊', label: '评估报告', disabled: false },
])

function navigate(item) {
  if (item.disabled) return
  router.push(item.path)
}
</script>

<style>
/* ═══════════════════════════════════════════
   CSS Variables — 浅色系 (绿/粉/黄/白)
   ═══════════════════════════════════════════ */
:root {
  --bg: #fefdf8;
  --surface: #ffffff;
  --surface-2: #fefce8;
  --surface-3: #fdf2f8;
  --border: #f0e8d8;
  --border-strong: #e8dcc8;
  --text: #2d2418;
  --text-secondary: #6b5e4a;
  --text-muted: #b8a890;
  --accent: #10b981;
  --accent-hover: #059669;
  --accent-soft: #ecfdf5;
  --pink: #ec4899;
  --pink-soft: #fdf2f8;
  --yellow: #f59e0b;
  --yellow-soft: #fffbeb;
  --danger: #ef4444;
  --danger-soft: #fef2f2;
  --radius: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  /* 淡色圆点背景纹理 */
  background-image: radial-gradient(circle, #e8dcc8 1px, transparent 1px);
  background-size: 30px 30px;
}

/* ═══════════════════════════════════════════
   Layout
   ═══════════════════════════════════════════ */
.app-shell { display: flex; min-height: 100vh; }

/* 侧边栏 */
.sidebar {
  width: 220px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  position: sticky; top: 0; height: 100vh;
  transition: width 0.2s ease; z-index: 20;
}
.sidebar.collapsed { width: 64px; }
.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 22px 18px; cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.sidebar-brand:hover { background: var(--accent-soft); }
.brand-icon { font-size: 28px; }
.brand-text {
  font-size: 16px; font-weight: 800;
  background: linear-gradient(135deg, #10b981, #059669);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.sidebar-nav { flex: 1; padding: 14px 10px; display: flex; flex-direction: column; gap: 4px; }
.nav-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 14px;
  border-radius: 12px; border: none; background: transparent;
  cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text-secondary);
  text-align: left; width: 100%; transition: all 0.15s;
}
.nav-item:hover:not(.disabled) { background: var(--accent-soft); color: #059669; }
.nav-item.active { background: var(--accent-soft); color: var(--accent); }
.nav-item.disabled { opacity: 0.35; cursor: not-allowed; }
.nav-icon { font-size: 18px; width: 24px; text-align: center; flex-shrink: 0; }
.nav-hint { font-size: 10px; color: var(--text-muted); margin-left: auto; }
.sidebar-toggle {
  margin: 12px; padding: 8px; border-radius: 10px;
  border: 1px solid var(--border); background: var(--surface);
  cursor: pointer; font-size: 12px; color: var(--text-muted);
  transition: all 0.15s;
}
.sidebar-toggle:hover { background: var(--accent-soft); color: var(--accent); }

/* 主内容 */
.main-content { flex: 1; min-width: 0; }
</style>
