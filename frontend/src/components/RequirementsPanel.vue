<template>
  <div class="requirements-panel">
    <div v-if="!store.requirements.length" class="empty-state">
      <span>📋</span><p>暂无需求</p>
    </div>

    <div v-for="r in store.requirements" :key="r.req_id" class="req-card">
      <div class="req-header">
        <div class="req-top">
          <span class="req-id">{{ r.req_id }}</span>
          <span class="req-title">{{ r.title }}</span>
          <div class="req-flags">
            <span class="badge" :class="'badge-' + r.priority.toLowerCase()">{{ r.priority }}</span>
            <span v-if="r.is_assumption" class="badge badge-assumption">假设</span>
          </div>
        </div>
        <p class="req-desc">{{ r.description }}</p>
      </div>

      <div class="req-body">
        <div v-if="r.user_story" class="req-section">
          <h4>用户故事</h4>
          <p class="user-story">{{ r.user_story }}</p>
        </div>

        <div v-if="r.acceptance_criteria?.length" class="req-section">
          <h4>验收标准</h4>
          <ul class="ac-list">
            <li v-for="(ac, i) in r.acceptance_criteria" :key="i">{{ ac }}</li>
          </ul>
        </div>

        <div class="req-meta">
          <span v-if="r.related_finding_ids?.length">关联发现: {{ r.related_finding_ids.join(', ') }}</span>
          <span v-if="r.related_review_ids?.length">关联评论: {{ r.related_review_ids.length }} 条</span>
          <span>版本: {{ r.version }}</span>
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
.requirements-panel { display: flex; flex-direction: column; gap: var(--space-md); animation: fadeIn var(--transition-base) ease; }

.req-card { background: var(--bg-input); border: 1px solid var(--border-color); border-radius: var(--border-radius); overflow: hidden; }
.req-header { padding: var(--space-md); border-bottom: 1px solid var(--border-color); }
.req-top { display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; margin-bottom: var(--space-sm); }
.req-id { font-family: var(--font-mono); font-size: 0.8rem; color: var(--color-primary); background: rgba(0,212,255,0.1); padding: 2px 8px; border-radius: var(--border-radius-sm); }
.req-title { font-weight: 700; font-size: var(--font-size-base); color: var(--text-primary); flex: 1; }
.req-flags { display: flex; gap: var(--space-xs); }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }
.badge-p0 { background: rgba(255,82,82,0.2); color: var(--color-error); }
.badge-p1 { background: rgba(255,171,0,0.2); color: var(--color-warning); }
.badge-p2 { background: rgba(68,138,255,0.2); color: var(--color-info); }
.badge-assumption { background: rgba(148,163,184,0.2); color: var(--text-muted); }
.req-desc { color: var(--text-secondary); font-size: var(--font-size-sm); line-height: 1.5; }

.req-body { padding: var(--space-md); }
.req-section { margin-bottom: var(--space-md); }
.req-section h4 { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: var(--space-xs); }
.user-story { font-style: italic; color: var(--text-primary); font-size: var(--font-size-sm); background: rgba(0,212,255,0.05); padding: var(--space-sm); border-radius: var(--border-radius-sm); }
.ac-list { list-style: disc; padding-left: 20px; }
.ac-list li { font-size: var(--font-size-sm); color: var(--text-primary); margin-bottom: 2px; }
.req-meta { display: flex; gap: var(--space-lg); font-size: 0.75rem; color: var(--text-muted); flex-wrap: wrap; }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: var(--space-2xl); color: var(--text-muted); gap: var(--space-sm); }
.empty-state span { font-size: 2rem; }
</style>