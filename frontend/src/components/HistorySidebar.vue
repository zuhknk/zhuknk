<template>
  <Teleport to="body">
    <Transition name="sidebar">
      <div v-if="visible" class="sidebar-overlay" @click.self="$emit('close')">
        <div class="sidebar">
          <div class="sidebar-header">
            <h2 class="sidebar-title">历史记录</h2>
            <button class="btn-close" @click="$emit('close')">&times;</button>
          </div>
          <div class="sidebar-content">
            <div v-if="loading" class="loading">加载中...</div>
            <div v-else-if="history.length === 0" class="empty">暂无历史记录</div>
            <div v-else class="history-list">
              <div
                v-for="item in history"
                :key="item.id"
                class="history-item"
                @click="loadItem(item)"
              >
                <div class="item-header">
                  <span class="item-app">{{ item.app_name || item.source_url || '未命名分析' }}</span>
                  <span class="item-badge" :class="'badge-' + item.source_type">{{ item.source_type }}</span>
                </div>
                <div class="item-meta">
                  <span>{{ item.reviews_count }} 评论</span>
                  <span>{{ item.findings_count }} 发现</span>
                  <span v-if="item.avg_rating">评分 {{ item.avg_rating.toFixed(1) }}</span>
                </div>
                <div class="item-time">{{ formatTime(item.created_at) }}</div>
                <button class="btn-delete" @click.stop="deleteItem(item.id)" title="删除">&#x1F5D1;</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close', 'loaded'])
const store = useAnalysisStore()

const history = ref([])
const loading = ref(false)

async function fetchHistory() {
  loading.value = true
  try {
    const res = await fetch('/api/history')
    const data = await res.json()
    history.value = data.history || []
  } catch (e) {
    console.error('Failed to fetch history:', e)
  } finally {
    loading.value = false
  }
}

function loadItem(item) {
  if (item.result) {
    store.reviews = item.result.reviews || []
    store.findings = item.result.findings || []
    store.requirements = item.result.requirements || []
    store.testCases = item.result.test_cases || []
    store.validationReport = item.result.validation_report || null
    store.analysisGoal = item.result.analysis_goal || ''
    store.dataLimitations = item.result.data_limitations || []
    store.warnings = item.result.warnings || []
    store.stage = 'done'
    store.progress = 100
    store.activeTab = 'charts'
    emit('loaded')
    emit('close')
  }
}

async function deleteItem(id) {
  try {
    await fetch(`/api/history/${id}`, { method: 'DELETE' })
    history.value = history.value.filter(h => h.id !== id)
  } catch (e) {
    console.error('Failed to delete:', e)
  }
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

watch(() => props.visible, (v) => { if (v) fetchHistory() })
onMounted(() => { if (props.visible) fetchHistory() })
</script>

<style scoped>
.sidebar-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}
.sidebar {
  width: 380px;
  max-width: 90vw;
  background: var(--bg-card);
  border-left: 1px solid var(--border-color);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}
.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.btn-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
  padding: 0 4px;
}
.btn-close:hover { color: var(--text-primary); }
.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.loading, .empty {
  text-align: center;
  color: var(--text-muted);
  padding: 40px 20px;
}
.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-item {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.2s;
  position: relative;
}
.history-item:hover { border-color: var(--color-primary); }
.item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.item-app {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 250px;
}
.item-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}
.badge-apple { background: rgba(0, 212, 255, 0.15); color: var(--color-primary); }
.badge-google { background: rgba(0, 230, 118, 0.15); color: var(--color-success); }
.badge-file { background: rgba(255, 171, 0, 0.15); color: var(--color-warning); }
.badge-unknown { background: rgba(100, 116, 139, 0.15); color: var(--text-muted); }
.item-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.item-time { font-size: 11px; color: var(--text-muted); }
.btn-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  opacity: 0.4;
  transition: opacity 0.2s;
}
.btn-delete:hover { opacity: 1; }

/* Transition */
.sidebar-enter-active, .sidebar-leave-active { transition: opacity 0.25s; }
.sidebar-enter-from, .sidebar-leave-to { opacity: 0; }
</style>
