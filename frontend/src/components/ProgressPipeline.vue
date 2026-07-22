<template>
  <section v-if="showPipeline" class="progress-pipeline">
    <!-- 阶段管道 -->
    <div class="pipeline-card">
      <h3 class="pipeline-title">分析进度</h3>
      <div class="pipeline-stages">
        <div v-for="s in stages" :key="s.key" class="stage-node" :class="stageClass(s.key)">
          <div class="stage-dot">
            <span v-if="s.key === store.stage && store.isRunning" class="dot-pulse"></span>
            <span v-else-if="isCompleted(s.key)">✓</span>
            <span v-else>{{ s.icon }}</span>
          </div>
          <div class="stage-info">
            <span class="stage-label">{{ s.label }}</span>
          </div>
        </div>
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: store.progress + '%' }"></div>
        </div>
        <span class="progress-text">{{ store.progress }}%</span>
      </div>
      <div class="pipeline-message">{{ store.message }}</div>
    </div>

    <!-- 结果面板 -->
    <div v-if="store.hasResults" class="results-section">
      <!-- 概览统计 -->
      <div class="stats-card">
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value">{{ store.totalReviews }}</span>
            <span class="stat-label">原始评论</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ store.cleanedReviews }}</span>
            <span class="stat-label">有效评论</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ store.findings.length }}</span>
            <span class="stat-label">分析发现</span>
          </div>
          <div class="stat-item" @click="store.activeTab = 'requirements'">
            <span class="stat-value">{{ store.requirements.length }}</span>
            <span class="stat-label">PRD 需求</span>
          </div>
        </div>
      </div>

      <!-- Tab 导航 -->
      <div class="tab-bar">
        <button
          v-for="tab in store.tabItems"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: store.activeTab === tab.key }"
          @click="store.activeTab = tab.key"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
        <div class="tab-spacer"></div>
        <button class="btn-export" @click="store.exportResults()">📥 导出 JSON</button>
      </div>

      <!-- Tab 内容 -->
      <div class="tab-content">
        <ReviewTable v-if="store.activeTab === 'reviews'" />
        <FindingsPanel v-else-if="store.activeTab === 'findings'" />
        <RequirementsPanel v-else-if="store.activeTab === 'requirements'" />
        <TestCasesPanel v-else-if="store.activeTab === 'testcases'" />
      </div>

      <!-- 校验报告 -->
      <details v-if="store.validationReport" class="validation-detail">
        <summary>
          校验报告
          <span v-if="store.validationReport.validation_passed" class="val-pass">✓ 通过</span>
          <span v-else class="val-fail">✗ 发现问题</span>
        </summary>
        <div class="val-body">
          <div v-if="store.validationReport.issues?.length" class="val-issues">
            <div v-for="(issue, i) in store.validationReport.issues" :key="i" class="val-issue" :class="'val-' + issue.severity">
              <strong>[{{ issue.severity }}]</strong> {{ issue.description }}
              <div v-if="issue.suggestion" class="val-suggestion">→ {{ issue.suggestion }}</div>
            </div>
          </div>
          <div v-if="store.validationReport.traceability" class="val-trace">
            <h4>可追溯性矩阵</h4>
            <div class="trace-grid">
              <span>需求有发现支撑: {{ store.validationReport.traceability.requirements_with_findings }}/{{ store.validationReport.traceability.total_requirements }}</span>
              <span>用例有需求支撑: {{ store.validationReport.traceability.test_cases_with_requirements }}/{{ store.validationReport.traceability.total_test_cases }}</span>
            </div>
          </div>
        </div>
      </details>

      <!-- 注意事项 -->
      <div v-if="store.dataLimitations.length || store.warnings.length" class="notes-card">
        <ul>
          <li v-for="(lim, i) in store.dataLimitations" :key="'lim-'+i">⚠ {{ lim }}</li>
          <li v-for="(warn, i) in store.warnings" :key="'warn-'+i">⚡ {{ warn }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'
import ReviewTable from './ReviewTable.vue'
import FindingsPanel from './FindingsPanel.vue'
import RequirementsPanel from './RequirementsPanel.vue'
import TestCasesPanel from './TestCasesPanel.vue'

const store = useAnalysisStore()

const stages = [
  { key: 'parsing',    label: '解析输入',   icon: '🔍' },
  { key: 'collecting', label: '采集评论',   icon: '📥' },
  { key: 'cleaning',   label: '清洗数据',   icon: '🧹' },
  { key: 'analyzing',  label: '语义分析',   icon: '🧠' },
  { key: 'evidence',   label: '证据验证',   icon: '🔬' },
  { key: 'prd',        label: '生成 PRD',   icon: '📋' },
  { key: 'testcase',   label: '测试用例',   icon: '✅' },
  { key: 'validating', label: '最终校验',   icon: '🔐' },
]

const stageOrder = stages.map(s => s.key)

function stageIndex(key) { return stageOrder.indexOf(key) }

function isCompleted(key) {
  const ci = stageIndex(store.stage)
  const ki = stageIndex(key)
  return ci > ki || store.stage === 'done'
}

function stageClass(key) {
  const ci = stageIndex(store.stage)
  const ki = stageIndex(key)
  if (store.stage === 'error') return ki < ci ? 'stage-done' : 'stage-pending'
  if (key === store.stage) return 'stage-active'
  if (ki < ci) return 'stage-done'
  return 'stage-pending'
}

const showPipeline = computed(() => store.stage !== 'idle')
</script>

<style scoped>
.progress-pipeline { animation: fadeIn var(--transition-base) ease; }

/* ---- Pipeline ---- */
.pipeline-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-lg); box-shadow: var(--shadow-md); }
.pipeline-title { font-size: var(--font-size-lg); color: var(--text-primary); margin-bottom: var(--space-lg); }
.pipeline-stages { display: flex; flex-wrap: wrap; gap: var(--space-sm); margin-bottom: var(--space-lg); }
.stage-node { display: flex; align-items: center; gap: var(--space-sm); padding: var(--space-sm) var(--space-md); border-radius: var(--border-radius); background: var(--bg-input); border: 1px solid var(--border-color); transition: all var(--transition-fast); flex: 1; min-width: 100px; }
.stage-dot { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; background: var(--bg-secondary); border: 2px solid var(--border-color); flex-shrink: 0; }
.stage-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--text-secondary); }
.stage-active { border-color: var(--border-active); background: var(--color-primary-glow); }
.stage-active .stage-dot { border-color: var(--color-primary); background: rgba(0,212,255,0.15); }
.stage-active .stage-label { color: var(--color-primary); }
.dot-pulse { width: 10px; height: 10px; background: var(--color-primary); border-radius: 50%; animation: pulse 1.5s infinite; }
.stage-done { border-color: rgba(0,230,118,0.3); background: rgba(0,230,118,0.05); }
.stage-done .stage-dot { border-color: var(--color-success); background: rgba(0,230,118,0.15); color: var(--color-success); }
.stage-done .stage-label { color: var(--color-success); }
.stage-pending { opacity: 0.4; }

.progress-bar-wrap { display: flex; align-items: center; gap: var(--space-md); margin-bottom: var(--space-sm); }
.progress-bar-track { flex: 1; height: 6px; background: var(--bg-input); border-radius: 3px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, var(--color-primary-dark), var(--color-primary)); border-radius: 3px; transition: width 0.3s ease; }
.progress-text { font-size: var(--font-size-sm); color: var(--text-secondary); font-family: var(--font-mono); min-width: 40px; text-align: right; }
.pipeline-message { font-size: var(--font-size-sm); color: var(--text-secondary); margin-top: var(--space-xs); min-height: 20px; }

/* ---- Results ---- */
.results-section { margin-top: var(--space-xl); display: flex; flex-direction: column; gap: var(--space-lg); }

/* Stats */
.stats-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-lg); box-shadow: var(--shadow-md); }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-md); }
.stat-item { display: flex; flex-direction: column; align-items: center; padding: var(--space-md); background: var(--bg-input); border-radius: var(--border-radius); cursor: default; }
.stat-item:last-child { cursor: pointer; }
.stat-item:last-child:hover { background: var(--bg-card-hover); }
.stat-value { font-size: var(--font-size-2xl); font-weight: 700; color: var(--color-primary); font-family: var(--font-mono); }
.stat-label { font-size: var(--font-size-sm); color: var(--text-muted); margin-top: var(--space-xs); }

/* Tabs */
.tab-bar { display: flex; gap: var(--space-xs); align-items: center; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-xs); }
.tab-btn { display: flex; align-items: center; gap: var(--space-xs); padding: 8px 16px; border: none; border-radius: var(--border-radius-sm); background: transparent; color: var(--text-secondary); font-size: var(--font-size-sm); font-family: var(--font-family); cursor: pointer; transition: all var(--transition-fast); }
.tab-btn:hover { color: var(--text-primary); background: var(--bg-input); }
.tab-btn.active { background: var(--color-primary-glow); color: var(--color-primary); }
.tab-spacer { flex: 1; }
.btn-export { padding: 8px 16px; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); background: var(--bg-input); color: var(--text-secondary); font-size: var(--font-size-sm); font-family: var(--font-family); cursor: pointer; transition: all var(--transition-fast); }
.btn-export:hover { border-color: var(--color-primary); color: var(--color-primary); }

.tab-content { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-lg); box-shadow: var(--shadow-md); min-height: 200px; }

/* Validation */
.validation-detail { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-md); }
.validation-detail summary { cursor: pointer; color: var(--text-primary); font-weight: 600; display: flex; align-items: center; gap: var(--space-sm); }
.val-pass { color: var(--color-success); font-size: var(--font-size-sm); }
.val-fail { color: var(--color-error); font-size: var(--font-size-sm); }
.val-body { margin-top: var(--space-md); }
.val-issues { display: flex; flex-direction: column; gap: var(--space-sm); margin-bottom: var(--space-md); }
.val-issue { padding: var(--space-sm); border-radius: var(--border-radius-sm); font-size: var(--font-size-sm); }
.val-error { background: rgba(255,82,82,0.1); border-left: 3px solid var(--color-error); }
.val-warning { background: rgba(255,171,0,0.08); border-left: 3px solid var(--color-warning); }
.val-info { background: rgba(68,138,255,0.08); border-left: 3px solid var(--color-info); }
.val-suggestion { margin-top: 4px; color: var(--text-muted); font-size: 0.8rem; }
.val-trace h4 { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: var(--space-xs); }
.trace-grid { display: flex; flex-direction: column; gap: 4px; font-size: var(--font-size-sm); color: var(--text-muted); }

/* Notes */
.notes-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: var(--space-md); }
.notes-card ul { list-style: none; display: flex; flex-direction: column; gap: var(--space-sm); }
.notes-card li { font-size: var(--font-size-sm); color: var(--text-secondary); }

@media (max-width: 768px) {
  .pipeline-stages { flex-direction: column; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .tab-bar { flex-wrap: wrap; }
}
</style>