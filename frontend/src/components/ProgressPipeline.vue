<template>
  <div v-if="store.isRunning || store.isDone" class="pipeline-container">
    <!-- 进度管道 -->
    <div class="pipeline-bar">
      <div class="pipeline-stages">
        <div
          v-for="s in stages"
          :key="s.key"
          :class="['stage', { active: s.active, done: s.done, current: s.current }]"
        >
          <div class="stage-dot">
            <span v-if="s.done">&#x2713;</span>
            <span v-else-if="s.current" class="spinner"></span>
            <span v-else>{{ s.index }}</span>
          </div>
          <span class="stage-label">{{ s.label }}</span>
        </div>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: store.progress + '%' }"></div>
      </div>
      <p class="status-message">{{ store.statusMessage }}</p>
    </div>

    <!-- 结果展示 -->
    <div v-if="store.isDone" class="results-section">
      <!-- 统计概览 -->
      <div class="stats-overview">
        <div class="stat-card">
          <span class="stat-value">{{ store.reviews.length }}</span>
          <span class="stat-label">有效评论</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ store.findings.length }}</span>
          <span class="stat-label">分析发现</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ store.requirements.length }}</span>
          <span class="stat-label">需求项</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ store.testCases.length }}</span>
          <span class="stat-label">测试用例</span>
        </div>
      </div>

      <!-- 数据限制 & 警告 -->
      <div v-if="store.warnings.length" class="warnings-box">
        <strong>⚠ 警告：</strong>
        <ul>
          <li v-for="w in store.warnings" :key="w">{{ w }}</li>
        </ul>
      </div>

      <!-- Tab 切换 -->
      <div class="result-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-btn', { active: store.activeTab === tab.key }]"
          @click="store.activeTab = tab.key"
        >
          {{ tab.label }}
          <span class="tab-count">{{ tab.count }}</span>
        </button>
        <button class="btn-export" @click="toggleExportMenu">导出</button>
        <div v-if="showExportMenu" class="export-menu">
          <button @click="doExport('json')">JSON</button>
          <button @click="doExport('pdf')">PDF</button>
          <button @click="doExport('docx')">Word</button>
          <button @click="doExport('xlsx')">Excel</button>
        </div>
      </div>

      <!-- Tab 内容 -->
      <div class="tab-content">
        <ChartsPanel v-if="store.activeTab === 'charts'" />
        <ReviewTable v-else-if="store.activeTab === 'reviews'" />
        <FindingsPanel v-else-if="store.activeTab === 'findings'" />
        <RequirementsPanel v-else-if="store.activeTab === 'requirements'" />
        <TestCasesPanel v-else-if="store.activeTab === 'testcases'" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'
import ReviewTable from './ReviewTable.vue'
import FindingsPanel from './FindingsPanel.vue'
import RequirementsPanel from './RequirementsPanel.vue'
import TestCasesPanel from './TestCasesPanel.vue'
import ChartsPanel from './ChartsPanel.vue'

const store = useAnalysisStore()

const showExportMenu = ref(false)

function toggleExportMenu() {
  showExportMenu.value = !showExportMenu.value
}

async function doExport(format) {
  showExportMenu.value = false
  const data = {
    reviews: store.reviews,
    findings: store.findings,
    requirements: store.requirements,
    test_cases: store.testCases,
    validation_report: store.validationReport,
    analysis_goal: store.analysisGoal,
  }

  if (format === 'json') {
    store.exportJSON()
    return
  }

  try {
    const response = await fetch(`/api/export/${format}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const ext = format === 'docx' ? 'docx' : format
    a.download = `app-review-analysis.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Export failed:', e)
  }
}

const stageOrder = ['parsing', 'collecting', 'cleaning', 'analyzing', 'evidence', 'prd', 'testcase', 'validating']
const stageLabels = {
  parsing: '解析', collecting: '采集', cleaning: '清洗', analyzing: '分析',
  evidence: '证据', prd: 'PRD', testcase: '用例', validating: '校验',
}

const stages = computed(() => {
  const currentIdx = stageOrder.indexOf(store.stage)
  return stageOrder.map((key, i) => ({
    key,
    index: i + 1,
    label: stageLabels[key],
    active: i <= currentIdx || store.isDone,
    done: i < currentIdx || store.isDone,
    current: i === currentIdx && !store.isDone,
  }))
})

const tabs = computed(() => [
  { key: 'charts', label: '可视化', count: '' },
  { key: 'reviews', label: '评论', count: store.reviews.length },
  { key: 'findings', label: '分析发现', count: store.findings.length },
  { key: 'requirements', label: '需求', count: store.requirements.length },
  { key: 'testcases', label: '测试用例', count: store.testCases.length },
])
</script>

<style scoped>
.pipeline-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 24px;
}
.pipeline-stages {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  opacity: 0.4;
  transition: opacity 0.3s;
}
.stage.active { opacity: 1; }
.stage-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-input);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-muted);
}
.stage.done .stage-dot {
  background: var(--color-success);
  border-color: var(--color-success);
  color: #fff;
}
.stage.current .stage-dot {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.stage-label {
  font-size: 11px;
  color: var(--text-secondary);
}
.progress-track {
  height: 4px;
  background: var(--bg-input);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s;
}
.status-message {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  margin: 0;
}
.results-section {
  margin-top: 24px;
}
.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px;
  text-align: center;
}
.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: var(--color-primary);
}
.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.warnings-box {
  background: rgba(255, 171, 0, 0.1);
  border: 1px solid var(--color-warning);
  border-radius: var(--border-radius);
  padding: 12px 16px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--color-warning);
}
.warnings-box ul {
  margin: 8px 0 0;
  padding-left: 20px;
}
.result-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 16px;
  padding-bottom: 0;
  position: relative;
}
.result-tabs .tab-btn {
  padding: 10px 20px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s;
}
.result-tabs .tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}
.tab-count {
  display: inline-block;
  background: var(--bg-input);
  color: var(--text-muted);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 6px;
}
.btn-export {
  margin-left: auto;
  padding: 8px 20px;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--border-radius);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-export:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-md);
  z-index: 10;
  min-width: 120px;
}
.export-menu button {
  display: block;
  width: 100%;
  padding: 8px 16px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s;
}
.export-menu button:hover {
  background: var(--bg-input);
  color: var(--color-primary);
}
.tab-content {
  min-height: 200px;
}
</style>
