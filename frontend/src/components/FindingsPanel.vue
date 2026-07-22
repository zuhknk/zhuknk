<template>
  <div class="findings-panel">
    <div v-if="!store.findings.length" class="empty-state">
      <span>🔍</span><p>暂无分析发现</p>
    </div>

    <div v-for="f in store.findings" :key="f.finding_id" class="finding-card" :class="'sev-' + f.severity">
      <div class="finding-header">
        <div class="finding-top">
          <span class="finding-topic">{{ f.topic }}</span>
          <div class="badges">
            <span class="badge" :class="'badge-' + f.severity">{{ f.severity }}</span>
            <span class="badge" :class="'badge-' + f.sentiment">{{ f.sentiment }}</span>
            <span class="badge badge-source">{{ f.source }}</span>
          </div>
        </div>
        <p class="finding-desc">{{ f.description }}</p>
      </div>

      <div class="finding-body">
        <div class="meta-row">
          <span class="meta-item">📊 样本量: <strong>{{ f.sample_count }}</strong></span>
          <span class="meta-item">🎯 置信度: <strong>{{ (f.confidence * 100).toFixed(0) }}%</strong></span>
          <span class="meta-item">📋 证据: <strong>{{ f.evidence_level }}</strong></span>
        </div>

        <div v-if="f.uncertainty" class="uncertainty">
          ⚠ {{ f.uncertainty }}
        </div>

        <div v-if="f.excerpts?.length" class="excerpts-section">
          <h4>用户原声</h4>
          <blockquote v-for="(ex, i) in f.excerpts.slice(0, 5)" :key="i" class="excerpt">
            "{{ ex }}"
          </blockquote>
        </div>

        <div v-if="f.conflicting_feedback?.length" class="conflicts">
          <h4>⚡ 冲突反馈</h4>
          <p v-for="(cf, i) in f.conflicting_feedback" :key="i">{{ cf }}</p>
        </div>

        <details v-if="f.review_ids?.length" class="review-ids-detail">
          <summary>关联评论 ({{ f.review_ids.length }} 条)</summary>
          <div class="id-list">
            <code v-for="id in f.review_ids.slice(0, 30)" :key="id">{{ id }}</code>
            <span v-if="f.review_ids.length > 30">...等 {{ f.review_ids.length - 30 }} 条</span>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAnalysisStore } from '../stores/analysis.js'
const store = useAnalysisStore()
</script>

<style scoped>
.findings-panel { display: flex; flex-direction: column; gap: var(--space-md); animation: fadeIn var(--transition-base) ease; }

.finding-card {
  background: var(--bg-input); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); overflow: hidden;
}
.finding-card.sev-critical { border-left: 3px solid var(--color-error); }
.finding-card.sev-high { border-left: 3px solid var(--color-warning); }
.finding-card.sev-medium { border-left: 3px solid var(--color-info); }
.finding-card.sev-low { border-left: 3px solid var(--text-muted); }

.finding-header { padding: var(--space-md); }
.finding-top { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-md); margin-bottom: var(--space-sm); }
.finding-topic { font-weight: 700; font-size: var(--font-size-base); color: var(--text-primary); }
.badges { display: flex; gap: var(--space-xs); flex-shrink: 0; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
.badge-critical { background: rgba(255,82,82,0.2); color: var(--color-error); }
.badge-high { background: rgba(255,171,0,0.2); color: var(--color-warning); }
.badge-medium { background: rgba(68,138,255,0.2); color: var(--color-info); }
.badge-low { background: rgba(148,163,184,0.2); color: var(--text-muted); }
.badge-positive { background: rgba(0,230,118,0.2); color: var(--color-success); }
.badge-negative { background: rgba(255,82,82,0.2); color: var(--color-error); }
.badge-neutral { background: rgba(148,163,184,0.2); color: var(--text-secondary); }
.badge-mixed { background: rgba(255,171,0,0.2); color: var(--color-warning); }
.badge-source { background: rgba(0,212,255,0.15); color: var(--color-primary); }
.finding-desc { color: var(--text-secondary); font-size: var(--font-size-sm); line-height: 1.5; }

.finding-body { padding: 0 var(--space-md) var(--space-md); }
.meta-row { display: flex; gap: var(--space-lg); margin-bottom: var(--space-sm); flex-wrap: wrap; }
.meta-item { font-size: var(--font-size-sm); color: var(--text-muted); }
.meta-item strong { color: var(--text-primary); }

.uncertainty { padding: var(--space-sm); background: rgba(255,171,0,0.08); border-radius: var(--border-radius-sm); font-size: var(--font-size-sm); color: var(--color-warning); margin-bottom: var(--space-sm); }

.excerpts-section { margin-top: var(--space-sm); }
.excerpts-section h4 { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: var(--space-xs); }
.excerpt { margin: 0; padding: var(--space-xs) var(--space-sm); border-left: 2px solid var(--border-color); background: rgba(0,0,0,0.2); font-size: 0.8rem; color: var(--text-muted); font-style: italic; margin-bottom: 2px; }

.conflicts { margin-top: var(--space-sm); }
.conflicts h4 { font-size: var(--font-size-sm); color: var(--color-warning); margin-bottom: var(--space-xs); }
.conflicts p { font-size: 0.8rem; color: var(--text-muted); margin: 0; }

.review-ids-detail { margin-top: var(--space-sm); }
.review-ids-detail summary { font-size: var(--font-size-sm); color: var(--text-muted); cursor: pointer; }
.review-ids-detail summary:hover { color: var(--color-primary); }
.id-list { display: flex; flex-wrap: wrap; gap: 4px; margin-top: var(--space-xs); }
.id-list code { font-size: 0.7rem; padding: 1px 6px; }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: var(--space-2xl); color: var(--text-muted); gap: var(--space-sm); }
.empty-state span { font-size: 2rem; }
</style>