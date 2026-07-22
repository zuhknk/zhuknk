<template>
  <div class="findings-panel">
    <div v-if="store.findings.length === 0" class="empty-state">暂无分析发现</div>
    <div v-for="f in store.findings" :key="f.finding_id" class="finding-card">
      <div class="finding-header">
        <span class="finding-topic">{{ f.topic }}</span>
        <span :class="'severity-badge severity-' + f.severity">{{ f.severity }}</span>
        <span :class="'sentiment-badge sentiment-' + f.sentiment">{{ f.sentiment }}</span>
        <span :class="'evidence-badge evidence-' + f.evidence_level">{{ f.evidence_level }}</span>
      </div>
      <p class="finding-desc">{{ f.description }}</p>
      <div class="finding-meta">
        <span>支撑评论: {{ f.sample_count }} 条</span>
        <span>置信度: {{ (f.confidence * 100).toFixed(0) }}%</span>
      </div>
      <div v-if="f.excerpts.length" class="finding-excerpts">
        <strong>关键摘录:</strong>
        <ul>
          <li v-for="(excerpt, i) in f.excerpts.slice(0, 5)" :key="i">"{{ excerpt }}"</li>
        </ul>
      </div>
      <div v-if="f.conflicting_feedback.length" class="finding-conflicts">
        <strong>冲突反馈:</strong>
        <ul>
          <li v-for="(cf, i) in f.conflicting_feedback" :key="i">{{ cf }}</li>
        </ul>
      </div>
      <div v-if="f.uncertainty" class="finding-uncertainty">
        <strong>不确定性:</strong> {{ f.uncertainty }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAnalysisStore } from '../stores/analysis.js'
const store = useAnalysisStore()
</script>

<style scoped>
.findings-panel { display: flex; flex-direction: column; gap: 12px; }
.empty-state { text-align: center; color: var(--text-muted); padding: 60px 20px; }
.finding-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px;
}
.finding-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.finding-topic { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.severity-badge, .sentiment-badge, .evidence-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}
.severity-critical { background: rgba(255, 82, 82, 0.15); color: var(--color-error); }
.severity-high { background: rgba(255, 145, 0, 0.15); color: #ff9100; }
.severity-medium { background: rgba(255, 171, 0, 0.15); color: var(--color-warning); }
.severity-low { background: rgba(68, 138, 255, 0.15); color: var(--color-info); }
.sentiment-negative { background: rgba(255, 82, 82, 0.1); color: var(--color-error); }
.sentiment-positive { background: rgba(0, 230, 118, 0.1); color: var(--color-success); }
.sentiment-mixed { background: rgba(255, 171, 0, 0.1); color: var(--color-warning); }
.sentiment-neutral { background: rgba(100, 116, 139, 0.1); color: var(--text-muted); }
.evidence-sufficient { background: rgba(0, 230, 118, 0.1); color: var(--color-success); }
.evidence-limited { background: rgba(255, 171, 0, 0.1); color: var(--color-warning); }
.evidence-insufficient { background: rgba(255, 82, 82, 0.1); color: var(--color-error); }
.finding-desc { font-size: 13px; color: var(--text-secondary); margin: 0 0 8px; line-height: 1.5; }
.finding-meta { font-size: 12px; color: var(--text-muted); display: flex; gap: 16px; margin-bottom: 8px; }
.finding-excerpts, .finding-conflicts, .finding-uncertainty {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 8px;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
}
.finding-excerpts ul, .finding-conflicts ul { margin: 4px 0 0; padding-left: 16px; }
.finding-excerpts li { color: var(--text-muted); font-style: italic; }
</style>
