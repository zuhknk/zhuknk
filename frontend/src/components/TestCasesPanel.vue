<template>
  <div class="testcases-panel">
    <div v-if="store.testCases.length === 0" class="empty-state">暂无测试用例</div>
    <div v-for="tc in store.testCases" :key="tc.case_id" class="tc-card">
      <div class="tc-header">
        <span class="tc-id">{{ tc.case_id }}</span>
        <span class="tc-req-id">需求: {{ tc.req_id }}</span>
        <span :class="'priority-badge priority-' + tc.priority">{{ tc.priority }}</span>
      </div>
      <h4 class="tc-title">{{ tc.title }}</h4>
      <div v-if="tc.preconditions.length" class="tc-section">
        <strong>前置条件:</strong>
        <ul>
          <li v-for="(p, i) in tc.preconditions" :key="i">{{ p }}</li>
        </ul>
      </div>
      <div v-if="tc.steps.length" class="tc-section">
        <strong>测试步骤:</strong>
        <ol>
          <li v-for="(s, i) in tc.steps" :key="i">{{ s }}</li>
        </ol>
      </div>
      <div v-if="tc.expected_result" class="tc-section">
        <strong>预期结果:</strong>
        <p class="tc-expected">{{ tc.expected_result }}</p>
      </div>
      <div v-if="tc.source_review_ids && tc.source_review_ids.length" class="tc-section tc-trace">
        <strong>追溯评论:</strong>
        <span class="trace-count">{{ tc.source_review_ids.length }} 条</span>
        <div class="trace-ids">
          <span v-for="(rid, i) in tc.source_review_ids.slice(0, 5)" :key="i" class="trace-badge">{{ rid }}</span>
          <span v-if="tc.source_review_ids.length > 5" class="trace-more">+{{ tc.source_review_ids.length - 5 }} 条</span>
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
.testcases-panel { display: flex; flex-direction: column; gap: 12px; }
.empty-state { text-align: center; color: var(--text-muted); padding: 60px 20px; }
.tc-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px;
}
.tc-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.tc-id { font-size: 12px; color: var(--text-muted); font-family: var(--font-family-mono); }
.tc-req-id { font-size: 12px; color: var(--text-secondary); }
.priority-badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.priority-P0 { background: rgba(255, 82, 82, 0.15); color: var(--color-error); }
.priority-P1 { background: rgba(255, 171, 0, 0.15); color: var(--color-warning); }
.priority-P2 { background: rgba(68, 138, 255, 0.15); color: var(--color-info); }
.tc-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 8px; }
.tc-section { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.tc-section ul, .tc-section ol { margin: 4px 0 0; padding-left: 20px; }
.tc-expected { color: var(--color-success); margin: 4px 0 0; }
.tc-trace {
  background: rgba(0, 212, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: var(--border-radius-sm);
  padding: 10px 12px;
}
.tc-trace strong { color: var(--accent); }
.trace-count {
  display: inline-block;
  font-size: 11px;
  background: rgba(0, 212, 255, 0.1);
  color: var(--accent);
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: 8px;
}
.trace-ids {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.trace-badge {
  font-size: 11px;
  font-family: var(--font-family-mono);
  background: var(--bg-secondary);
  color: var(--text-muted);
  padding: 2px 8px;
  border-radius: 3px;
}
.trace-more {
  font-size: 11px;
  color: var(--text-muted);
  padding: 2px 4px;
}
</style>
