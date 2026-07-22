<template>
  <div class="requirements-panel">
    <div v-if="store.requirements.length === 0" class="empty-state">暂无需求</div>
    <div v-for="req in store.requirements" :key="req.req_id" class="req-card">
      <div class="req-header">
        <span class="req-id">{{ req.req_id }}</span>
        <span :class="'priority-badge priority-' + req.priority">{{ req.priority }}</span>
        <span v-if="req.is_assumption" class="assumption-badge">假设</span>
      </div>
      <h4 class="req-title">{{ req.title }}</h4>
      <p class="req-desc">{{ req.description }}</p>
      <div class="req-user-story">
        <strong>用户故事:</strong> {{ req.user_story }}
      </div>
      <div v-if="req.acceptance_criteria.length" class="req-ac">
        <strong>验收标准:</strong>
        <ul>
          <li v-for="(ac, i) in req.acceptance_criteria" :key="i">{{ ac }}</li>
        </ul>
      </div>
      <div class="req-meta">
        <span>版本: {{ req.version }}</span>
        <span>关联发现: {{ req.related_finding_ids.length }} 个</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAnalysisStore } from '../stores/analysis.js'
const store = useAnalysisStore()
</script>

<style scoped>
.requirements-panel { display: flex; flex-direction: column; gap: 12px; }
.empty-state { text-align: center; color: var(--text-muted); padding: 60px 20px; }
.req-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px;
}
.req-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.req-id { font-size: 12px; color: var(--text-muted); font-family: var(--font-family-mono); }
.priority-badge, .assumption-badge {
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
}
.priority-P0 { background: rgba(255, 82, 82, 0.15); color: var(--color-error); }
.priority-P1 { background: rgba(255, 171, 0, 0.15); color: var(--color-warning); }
.priority-P2 { background: rgba(68, 138, 255, 0.15); color: var(--color-info); }
.assumption-badge { background: rgba(100, 116, 139, 0.15); color: var(--text-muted); }
.req-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 6px; }
.req-desc { font-size: 13px; color: var(--text-secondary); margin: 0 0 8px; line-height: 1.5; }
.req-user-story { font-size: 13px; color: var(--color-primary); margin-bottom: 8px; padding: 8px; background: rgba(0, 212, 255, 0.05); border-radius: 4px; }
.req-ac { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
.req-ac ul { margin: 4px 0 0; padding-left: 16px; }
.req-meta { font-size: 12px; color: var(--text-muted); display: flex; gap: 16px; }
</style>
