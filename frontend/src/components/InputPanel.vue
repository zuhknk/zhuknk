<template>
  <section class="input-panel">
    <div class="panel-card">
      <div class="panel-header">
        <h2 class="panel-title">输入 App Store 链接</h2>
        <button class="mode-toggle" @click="showFile = !showFile" :disabled="store.isRunning">
          {{ showFile ? '← 链接输入' : '📁 文件导入' }}
        </button>
      </div>

      <!-- URL 模式 -->
      <div v-if="!showFile">
        <p class="panel-desc">
          粘贴美国 App Store 应用链接，系统将自动采集评论并进行语义分析
        </p>

        <div class="input-row">
          <div class="input-wrapper">
            <span class="input-icon">🔗</span>
            <input
              v-model="appUrl"
              type="url"
              class="input-field"
              placeholder="https://apps.apple.com/us/app/xxx/id123456789"
              :disabled="store.isRunning"
              @keyup.enter="handleAnalyzeUrl"
            />
          </div>
          <button
            class="btn-analyze"
            :disabled="!appUrl.trim() || store.isRunning"
            @click="handleAnalyzeUrl"
          >
            <span v-if="store.isRunning" class="spinner"></span>
            <span v-else>开始分析</span>
          </button>
        </div>

        <div class="example-hint">
          <span>示例：</span>
          <button class="btn-example" @click="setExample('839285684')">Workout for Women</button>
          <button class="btn-example" @click="setExample('284815942')">Google</button>
          <span class="hint-divider">|</span>
          <label class="sort-label">排序：</label>
          <select v-model="sortBy" class="sort-select" :disabled="store.isRunning">
            <option value="mostrecent">最新</option>
            <option value="mosthelpful">最有帮助</option>
          </select>
        </div>
      </div>

      <!-- 文件导入模式 -->
      <div v-else>
        <p class="panel-desc">
          上传 JSON 或 CSV 格式的评论数据文件，系统将直接进行分析
        </p>

        <div class="file-upload-area"
          :class="{ dragging }"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".json,.csv"
            class="file-input-hidden"
            @change="handleFileSelect"
          />
          <div v-if="!selectedFile" class="upload-placeholder">
            <span class="upload-icon">📂</span>
            <span>拖拽文件到此处，或点击选择</span>
            <span class="upload-hint">支持 .json / .csv</span>
          </div>
          <div v-else class="upload-selected">
            <span class="upload-icon">📄</span>
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
            <button class="btn-clear" @click.stop="clearFile">✕</button>
          </div>
        </div>

        <button
          class="btn-analyze btn-file"
          :disabled="!selectedFile || store.isRunning"
          @click="handleAnalyzeFile"
        >
          <span v-if="store.isRunning" class="spinner"></span>
          <span v-else>导入并分析</span>
        </button>
      </div>

      <!-- 错误提示 -->
      <div v-if="store.error" class="error-banner">
        <span class="error-icon">⚠</span>
        <span>{{ store.error }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'

const store = useAnalysisStore()
const appUrl = ref('')
const showFile = ref(false)
const sortBy = ref('mostrecent')
const selectedFile = ref(null)
const fileInput = ref(null)
const dragging = ref(false)

function setExample(appId) {
  appUrl.value = `https://apps.apple.com/us/app/id${appId}`
}

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) selectedFile.value = file
}

function handleDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files?.[0]
  if (file) selectedFile.value = file
}

function clearFile() {
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function handleAnalyzeUrl() {
  if (!appUrl.value.trim() || store.isRunning) return
  store.startAnalysis()
  await runSSE({ app_url: appUrl.value.trim(), sort_by: sortBy.value })
}

async function handleAnalyzeFile() {
  if (!selectedFile.value || store.isRunning) return
  store.startAnalysis()

  try {
    const text = await selectedFile.value.text()
    const isJson = selectedFile.value.name.endsWith('.json')
    const payload = {
      app_url: '',
      file_data: text,
      file_format: isJson ? 'json' : 'csv',
    }
    await runSSE(payload)
  } catch (err) {
    store.setError('文件读取失败: ' + err.message)
  }
}

async function runSSE(payload) {
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.stage === 'done') {
              store.updateProgress(data)
              store.finishAnalysis()
            } else if (data.stage === 'error') {
              store.setError(data.message)
            } else {
              store.updateProgress(data)
            }
          } catch (e) { /* skip */ }
        }
      }
    }
  } catch (err) {
    store.setError(err.message || '网络请求失败')
  }
}
</script>

<style scoped>
.input-panel { margin-bottom: var(--space-xl); }
.panel-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-lg); box-shadow: var(--shadow-md); }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-xs); }
.panel-title { color: var(--text-primary); font-size: var(--font-size-lg); }
.mode-toggle { background: none; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); padding: 4px 12px; color: var(--text-secondary); font-size: var(--font-size-sm); font-family: var(--font-family); cursor: pointer; transition: all var(--transition-fast); }
.mode-toggle:hover { border-color: var(--color-primary); color: var(--color-primary); }
.panel-desc { color: var(--text-secondary); font-size: var(--font-size-sm); margin-bottom: var(--space-lg); }

.input-row { display: flex; gap: var(--space-md); }
.input-wrapper { flex: 1; position: relative; display: flex; align-items: center; }
.input-icon { position: absolute; left: 12px; font-size: 1rem; pointer-events: none; }
.input-field { width: 100%; padding: 10px 12px 10px 36px; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: var(--border-radius); color: var(--text-primary); font-size: var(--font-size-base); font-family: var(--font-mono); outline: none; transition: border-color var(--transition-fast); }
.input-field:focus { border-color: var(--border-active); box-shadow: 0 0 0 3px var(--color-primary-glow); }
.input-field:disabled { opacity: 0.5; cursor: not-allowed; }
.input-field::placeholder { color: var(--text-muted); font-family: var(--font-family); }

.btn-analyze { display: flex; align-items: center; justify-content: center; gap: var(--space-sm); min-width: 120px; padding: 10px 24px; background: var(--color-primary); border: none; border-radius: var(--border-radius); color: var(--bg-primary); font-size: var(--font-size-base); font-weight: 600; font-family: var(--font-family); cursor: pointer; transition: all var(--transition-fast); }
.btn-analyze:hover:not(:disabled) { background: var(--color-primary-dark); box-shadow: var(--shadow-glow); }
.btn-analyze:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-file { margin-top: var(--space-md); width: 100%; }
.spinner { width: 16px; height: 16px; border: 2px solid transparent; border-top-color: var(--bg-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }

/* File Upload */
.file-upload-area { border: 2px dashed var(--border-color); border-radius: var(--border-radius); padding: var(--space-xl); text-align: center; cursor: pointer; transition: all var(--transition-fast); }
.file-upload-area:hover, .file-upload-area.dragging { border-color: var(--border-active); background: var(--color-primary-glow); }
.file-input-hidden { display: none; }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; gap: var(--space-sm); color: var(--text-muted); font-size: var(--font-size-sm); }
.upload-icon { font-size: 2rem; }
.upload-hint { font-size: 0.75rem; }
.upload-selected { display: flex; align-items: center; gap: var(--space-md); color: var(--text-primary); font-size: var(--font-size-sm); }
.file-name { color: var(--color-primary); font-weight: 600; }
.file-size { color: var(--text-muted); font-size: 0.8rem; }
.btn-clear { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 1rem; padding: 4px; }
.btn-clear:hover { color: var(--color-error); }

.example-hint { margin-top: var(--space-md); display: flex; align-items: center; gap: var(--space-sm); font-size: var(--font-size-sm); color: var(--text-muted); }
.btn-example { background: none; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); padding: 2px 10px; color: var(--text-secondary); font-size: var(--font-size-sm); font-family: var(--font-family); cursor: pointer; transition: all var(--transition-fast); }
.btn-example:hover { border-color: var(--color-primary); color: var(--color-primary); }
.hint-divider { color: var(--border-color); }
.sort-label { color: var(--text-muted); }
.sort-select { padding: 2px 8px; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); color: var(--text-secondary); font-size: var(--font-size-sm); font-family: var(--font-family); cursor: pointer; outline: none; }
.sort-select:focus { border-color: var(--border-active); }

.error-banner { margin-top: var(--space-md); display: flex; align-items: center; gap: var(--space-sm); padding: var(--space-sm) var(--space-md); background: rgba(255,82,82,0.1); border: 1px solid rgba(255,82,82,0.3); border-radius: var(--border-radius); color: var(--color-error); font-size: var(--font-size-sm); }
.error-icon { font-size: 1rem; flex-shrink: 0; }
</style>