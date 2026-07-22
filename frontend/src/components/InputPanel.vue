<template>
  <div class="input-panel">
    <div class="input-tabs">
      <button
        :class="['tab-btn', { active: inputMode === 'url' }]"
        @click="inputMode = 'url'"
      >URL 输入</button>
      <button
        :class="['tab-btn', { active: inputMode === 'file' }]"
        @click="inputMode = 'file'"
      >文件导入</button>
    </div>

    <!-- URL 输入模式 -->
    <div v-if="inputMode === 'url'" class="input-content">
      <div class="url-input-row">
        <input
          v-model="appStoreUrl"
          type="text"
          class="url-input"
          placeholder="输入 App Store 链接，例如 https://apps.apple.com/us/app/xxx/id123456789"
          @keyup.enter="submitURL"
          :disabled="store.isRunning"
        />
        <button
          class="btn-analyze"
          @click="submitURL"
          :disabled="!appStoreUrl.trim() || store.isRunning"
        >
          {{ store.isRunning ? '分析中...' : '开始分析' }}
        </button>
      </div>
      <p class="input-hint">支持任意国家/地区的 App Store 链接，评论数据始终从 US 区采集</p>

      <!-- 分析目标 -->
      <div class="goal-section">
        <label class="goal-label">分析目标（可选）</label>
        <input
          v-model="analysisGoal"
          type="text"
          class="goal-input"
          placeholder="例如：关注订阅转化率、低评分评论、特定版本 v3.2、健身可用性..."
          :disabled="store.isRunning"
        />
      </div>
    </div>

    <!-- 文件导入模式 -->
    <div v-else class="input-content">
      <div
        class="drop-zone"
        @dragover.prevent
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <div class="drop-icon">&#x1F4C4;</div>
        <p class="drop-text">拖拽文件到此处，或点击选择文件</p>
        <p class="drop-hint">支持 JSON / CSV 格式的评论数据</p>
      </div>
      <input ref="fileInput" type="file" accept=".json,.csv" @change="handleFileSelect" style="display:none" />
      <div v-if="fileName" class="file-info">
        <span class="file-name">{{ fileName }}</span>
        <button class="btn-analyze" @click="submitFile" :disabled="store.isRunning">
          {{ store.isRunning ? '分析中...' : '开始分析' }}
        </button>
      </div>

      <!-- 分析目标 -->
      <div class="goal-section">
        <label class="goal-label">分析目标（可选）</label>
        <input
          v-model="analysisGoal"
          type="text"
          class="goal-input"
          placeholder="例如：关注订阅转化率、低评分评论、特定版本..."
          :disabled="store.isRunning"
        />
      </div>
    </div>

    <div v-if="store.hasError" class="error-message">{{ store.error }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'

const store = useAnalysisStore()

const inputMode = ref('url')
const appStoreUrl = ref('')
const analysisGoal = ref('')
const fileInput = ref(null)
const fileName = ref('')
const fileData = ref(null)
const fileFormat = ref('') // 'json' | 'csv'

function buildPayload() {
  const payload = {}
  if (inputMode.value === 'url') {
    payload.app_store_url = appStoreUrl.value.trim()
  } else {
    payload.file_data = fileData.value
    payload.file_format = fileFormat.value
  }
  if (analysisGoal.value.trim()) {
    payload.analysis_goal = analysisGoal.value.trim()
  }
  return payload
}

function submitURL() {
  if (!appStoreUrl.value.trim() || store.isRunning) return
  store.runAnalysis(buildPayload())
}

function triggerFileInput() {
  fileInput.value?.click()
}

function parseCSV(text) {
  const lines = text.trim().split('\n')
  if (lines.length < 2) throw new Error('CSV 至少需要标题行和一行数据')
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows = []
  for (let i = 1; i < lines.length; i++) {
    const vals = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    const row = {}
    headers.forEach((h, idx) => { row[h] = vals[idx] || '' })
    if (row.rating) row.rating = parseInt(row.rating) || 0
    if (row.vote_sum) row.vote_sum = parseInt(row.vote_sum) || 0
    if (row.vote_count) row.vote_count = parseInt(row.vote_count) || 0
    rows.push(row)
  }
  return rows
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (!file) return
  fileName.value = file.name
  const isCSV = file.name.toLowerCase().endsWith('.csv')
  fileFormat.value = isCSV ? 'csv' : 'json'
  const reader = new FileReader()
  reader.onload = (ev) => {
    try {
      if (isCSV) {
        fileData.value = parseCSV(ev.target.result)
      } else {
        fileData.value = JSON.parse(ev.target.result)
      }
    } catch (err) {
      store.setError((isCSV ? 'CSV' : 'JSON') + ' 文件解析失败，请检查文件格式: ' + err.message)
    }
  }
  reader.readAsText(file)
}

function handleDrop(e) {
  const file = e.dataTransfer.files[0]
  if (!file) return
  fileName.value = file.name
  const isCSV = file.name.toLowerCase().endsWith('.csv')
  fileFormat.value = isCSV ? 'csv' : 'json'
  const reader = new FileReader()
  reader.onload = (ev) => {
    try {
      if (isCSV) {
        fileData.value = parseCSV(ev.target.result)
      } else {
        fileData.value = JSON.parse(ev.target.result)
      }
    } catch (err) {
      store.setError((isCSV ? 'CSV' : 'JSON') + ' 文件解析失败，请检查文件格式: ' + err.message)
    }
  }
  reader.readAsText(file)
}

function submitFile() {
  if (!fileData.value || store.isRunning) return
  store.runAnalysis(buildPayload())
}
</script>

<style scoped>
.input-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 24px;
  margin-bottom: 24px;
}
.input-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}
.tab-btn {
  padding: 10px 24px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}
.tab-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.url-input-row {
  display: flex;
  gap: 12px;
}
.url-input {
  flex: 1;
  padding: 12px 16px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-size: 14px;
  font-family: var(--font-family-mono);
  outline: none;
  transition: border-color 0.2s;
}
.url-input:focus {
  border-color: var(--color-primary);
}
.url-input:disabled {
  opacity: 0.5;
}
.btn-analyze {
  padding: 12px 32px;
  background: var(--color-primary);
  color: var(--bg-primary);
  border: none;
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}
.btn-analyze:hover:not(:disabled) {
  filter: brightness(1.1);
}
.btn-analyze:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.input-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}
.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius);
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}
.drop-zone:hover {
  border-color: var(--color-primary);
}
.drop-icon {
  font-size: 40px;
  margin-bottom: 12px;
}
.drop-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 8px;
}
.drop-hint {
  color: var(--text-muted);
  font-size: 12px;
  margin: 0;
}
.file-info {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-input);
  border-radius: var(--border-radius);
}
.file-name {
  color: var(--text-secondary);
  font-size: 14px;
}
.error-message {
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(255, 82, 82, 0.1);
  border: 1px solid var(--color-error);
  border-radius: var(--border-radius);
  color: var(--color-error);
  font-size: 14px;
}
.goal-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}
.goal-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-weight: 500;
}
.goal-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}
.goal-input:focus {
  border-color: var(--color-primary);
}
.goal-input:disabled {
  opacity: 0.5;
}
</style>
