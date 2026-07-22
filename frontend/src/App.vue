<template>
  <div class="app-root">
    <!-- 顶部导航 -->
    <header class="app-header">
      <div class="header-inner container">
        <div class="brand">
          <span class="brand-icon">◆</span>
          <span class="brand-name">LaienTech</span>
          <span class="brand-subtitle">iOS App Review Analyzer</span>
        </div>
        <div class="header-status">
          <span class="status-dot" :class="statusClass"></span>
          <span class="status-text">{{ statusText }}</span>
        </div>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="app-main container">
      <InputPanel />
      <ProgressPipeline />
    </main>

    <!-- 底部 -->
    <footer class="app-footer">
      <span>LaienTech iOS App Review Analysis &amp; Version Planning Assessment</span>
      <span class="footer-divider">|</span>
      <span>v0.1.0</span>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAnalysisStore } from './stores/analysis.js'
import InputPanel from './components/InputPanel.vue'
import ProgressPipeline from './components/ProgressPipeline.vue'

const store = useAnalysisStore()

const statusClass = computed(() => {
  if (store.isRunning) return 'status-running'
  if (store.stage === 'done') return 'status-done'
  if (store.stage === 'error') return 'status-error'
  return 'status-idle'
})

const statusText = computed(() => {
  if (store.isRunning) return `分析中 — ${store.stageLabel}`
  if (store.stage === 'done') return '分析完成'
  if (store.stage === 'error') return '分析出错'
  return '系统就绪'
})
</script>

<style scoped>
.app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ---- Header ---- */
.app-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.brand-icon {
  color: var(--color-primary);
  font-size: 1.4rem;
}

.brand-name {
  font-weight: 700;
  font-size: var(--font-size-lg);
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.brand-subtitle {
  color: var(--text-muted);
  font-size: var(--font-size-sm);
  margin-left: var(--space-xs);
}

.header-status {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-dot.status-idle { background: var(--text-muted); }
.status-dot.status-running { background: var(--color-primary); animation: pulse 1.5s infinite; }
.status-dot.status-done { background: var(--color-success); }
.status-dot.status-error { background: var(--color-error); }

.status-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* ---- Main ---- */
.app-main {
  flex: 1;
  padding-top: var(--space-xl);
  padding-bottom: var(--space-2xl);
}

/* ---- Footer ---- */
.app-footer {
  text-align: center;
  padding: var(--space-md) var(--space-lg);
  color: var(--text-muted);
  font-size: var(--font-size-sm);
  border-top: 1px solid var(--border-color);
}

.footer-divider {
  margin: 0 var(--space-sm);
  color: var(--border-color);
}
</style>