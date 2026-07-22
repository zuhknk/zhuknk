<template>
  <div class="testcases-panel">
    <div v-if="!store.testCases.length" class="empty-state">
      <span>✅</span><p>暂无测试用例</p>
    </div>

    <div v-for="tc in store.testCases" :key="tc.case_id" class="tc-card">
      <div class="tc-header">
        <div class="tc-top">
          <span class="tc-id">{{ tc.case_id }}</span>
          <span class="tc-title">{{ tc.title }}</span>
          <div class="tc-flags">
            <span class="badge" :class="'badge-' + (tc.priority || 'p1').toLowerCase()">{{ tc.priority }}</span>
            <span v-if="tc.req_id" class="tc-req-ref">← {{ tc.req_id }}</span>
          </div>
        </div>
      </div>

      <div class="tc-body">
        <div v-if="tc.preconditions?.length" class="tc-section">
          <h4>前置条件</h4>
          <ul>
            <li v-for="(p, i) in tc.preconditions" :key="i">{{ p }}</li>
          </ul>
        </div>

        <div v-if="tc.steps?.length" class="tc-section">
          <h4>测试步骤</h4>
          <ol>
            <li v-for="(s, i) in tc.steps" :key="i">{{ s }}</li>
          </ol>
        </div>

        <div v-if="tc.expected_result" class="tc-section">
          <h4>预期结果</h4>
          <p class="expected">{{ tc.expected_result }}</p>
        </div>

        <div v-if="tc.source_review_ids?.length" class="tc-meta">
          来源评论: {{ tc.source_review_ids.length }} 条
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAnalysisStore } from '../stores/analysis.js'
const store = useAnalysisStore()
</script>

<style scoped>
.testcases-panel { display: flex; flex-direction: column; gap: var(--space-md); animation: fadeIn var(--transition-base) ease; }

.tc-card { background: var(--bg-input); border: 1px solid var(--border-color); border-radius: var(--border-radius); overflow: hidden; }
.tc-header { padding: var(--space-md); border-bottom: 1px solid var(--border-color); }
.tc-top { display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; }
.tc-id { font-family: var(--font-mono); font-size: 0.8rem; color: var(--color-success); background: rgba(0,230,118,0.1); padding: 2px 8px; border-radius: var(--border-radius-sm); }
.tc-title { font-weight: 700; font-size: var(--font-size-base); color: var(--text-primary); flex: 1; }
.tc-flags { display: flex; align-items: center; gap: var(--space-sm); }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }
.badge-p0 { background: rgba(255,82,82,0.2); color: var(--color-error); }
.badge-p1 { background: rgba(255,171,0,0.2); color: var(--color-warning); }
.badge-p2 { background: rgba(68,138,255,0.2); color: var(--color-info); }
.tc-req-ref { font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); }

.tc-body { padding: var(--space-md); }
.tc-section { margin-bottom: var(--space-md); }
.tc-section h4 { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: var(--space-xs); }
.tc-section ul, .tc-section ol { padding-left: 20px; }
.tc-section li { font-size: var(--font-size-sm); color: var(--text-primary); margin-bottom: 2px; }
.expected { color: var(--color-success); font-size: var(--font-size-sm); font-weight: 600; background: rgba(0,230,118,0.05); padding: var(--space-sm); border-radius: var(--border-radius-sm); }
.tc-meta { font-size: 0.75rem; color: var(--text-muted); margin-top: var(--space-sm); }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: var(--space-2xl); color: var(--text-muted); gap: var(--space-sm); }
.empty-state span { font-size: 2rem; }
</style>