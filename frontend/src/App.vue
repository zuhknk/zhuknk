<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <div>
          <h1 class="app-title">
            <span class="title-accent">LaienTech</span> App Review Analyzer
          </h1>
          <p class="app-subtitle">AI 驱动的应用评论智能分析平台</p>
        </div>
        <div class="header-actions">
          <div class="llm-status" :class="llmConnected ? 'connected' : 'disconnected'" @click="showSettings = true">
            <span class="status-dot"></span>
            <span>{{ llmConnected ? llmLabel : '未配置 LLM' }}</span>
          </div>
          <button class="btn-icon" @click="showSettings = true" title="LLM 设置">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path>
            </svg>
          </button>
          <button class="btn-history" @click="showHistory = true">历史记录</button>
        </div>
      </div>
    </header>
    <main class="app-main">
      <InputPanel />
      <ProgressPipeline />
    </main>
    <HistorySidebar :visible="showHistory" @close="showHistory = false" @loaded="showHistory = false" />
    <LlmSettingsModal :visible="showSettings" @close="showSettings = false" @saved="fetchLlmStatus" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import InputPanel from './components/InputPanel.vue'
import ProgressPipeline from './components/ProgressPipeline.vue'
import HistorySidebar from './components/HistorySidebar.vue'
import LlmSettingsModal from './components/LlmSettingsModal.vue'

const showHistory = ref(false)
const showSettings = ref(false)
const llmConnected = ref(false)
const llmLabel = ref('')

async function fetchLlmStatus() {
  try {
    const res = await fetch('/api/settings/llm')
    const data = await res.json()
    const cur = data.current || {}
    llmConnected.value = cur.api_key_set || false
    llmLabel.value = cur.api_key_set ? `${cur.provider}/${cur.model}` : ''
  } catch (e) {
    llmConnected.value = false
  }
}

onMounted(fetchLlmStatus)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-family);
}
.app-header {
  text-align: center;
  padding: 32px 20px 16px;
  border-bottom: 1px solid var(--border-color);
}
.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.llm-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--border-radius);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.llm-status.connected {
  background: rgba(0, 230, 118, 0.1);
  color: var(--color-success);
}
.llm-status.disconnected {
  background: rgba(100, 116, 139, 0.1);
  color: var(--text-muted);
}
.llm-status:hover { filter: brightness(1.2); }
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-icon:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.app-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.title-accent {
  color: var(--color-primary);
}
.app-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 8px 0 0;
}
.btn-history {
  padding: 8px 20px;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--border-radius);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-history:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.app-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 20px;
}
</style>
