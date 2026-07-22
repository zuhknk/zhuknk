<template>
  <div class="review-table-wrap">
    <div class="table-toolbar">
      <div class="filter-group">
        <input v-model="search" class="filter-input" placeholder="搜索评论内容..." />
        <select v-model="ratingFilter" class="filter-select">
          <option value="">全部评分</option>
          <option value="5">★★★★★</option>
          <option value="4">★★★★</option>
          <option value="3">★★★</option>
          <option value="2">★★</option>
          <option value="1">★</option>
        </select>
        <select v-model="sortBy" class="filter-select">
          <option value="date">按日期</option>
          <option value="rating">按评分</option>
          <option value="vote_sum">按有用数</option>
        </select>
        <button class="btn-sort" @click="sortDir = sortDir === 'desc' ? 'asc' : 'desc'">
          {{ sortDir === 'desc' ? '↓' : '↑' }}
        </button>
      </div>
      <span class="table-count">{{ filtered.length }} / {{ store.reviews.length }} 条</span>
    </div>

    <div v-if="!filtered.length" class="empty-state">
      <span>📭</span>
      <p>没有匹配的评论</p>
    </div>

    <div v-else class="table-scroll">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-rating">评分</th>
            <th class="col-title">标题</th>
            <th class="col-content">内容</th>
            <th class="col-version">版本</th>
            <th class="col-date">日期</th>
            <th class="col-votes">有用</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filtered" :key="r.review_id">
            <td class="col-rating">
              <span class="stars">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
            </td>
            <td class="col-title" :title="r.title">{{ r.title || '-' }}</td>
            <td class="col-content" :title="r.content">{{ r.content }}</td>
            <td class="col-version">{{ r.version || '-' }}</td>
            <td class="col-date">{{ formatDate(r.date) }}</td>
            <td class="col-votes">{{ r.vote_sum || 0 }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'

const store = useAnalysisStore()
const search = ref('')
const ratingFilter = ref('')
const sortBy = ref('date')
const sortDir = ref('desc')

const filtered = computed(() => {
  let list = [...store.reviews]
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(r =>
      r.content?.toLowerCase().includes(q) ||
      r.title?.toLowerCase().includes(q)
    )
  }
  if (ratingFilter.value) {
    list = list.filter(r => r.rating === Number(ratingFilter.value))
  }
  list.sort((a, b) => {
    let va, vb
    if (sortBy.value === 'date') {
      va = new Date(a.date || 0).getTime()
      vb = new Date(b.date || 0).getTime()
    } else if (sortBy.value === 'rating') {
      va = a.rating; vb = b.rating
    } else {
      va = a.vote_sum || 0; vb = b.vote_sum || 0
    }
    return sortDir.value === 'desc' ? vb - va : va - vb
  })
  return list
})

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.review-table-wrap { animation: fadeIn var(--transition-base) ease; }

.table-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: var(--space-md); gap: var(--space-md); flex-wrap: wrap;
}
.filter-group { display: flex; gap: var(--space-sm); align-items: center; }
.filter-input, .filter-select {
  padding: 6px 12px; background: var(--bg-input); border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm); color: var(--text-primary); font-size: var(--font-size-sm);
  outline: none;
}
.filter-input:focus, .filter-select:focus { border-color: var(--border-active); }
.filter-input { width: 240px; }
.filter-input::placeholder { color: var(--text-muted); }
.btn-sort {
  padding: 6px 10px; background: var(--bg-input); border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm); color: var(--text-primary); cursor: pointer;
  font-size: var(--font-size-sm);
}
.btn-sort:hover { border-color: var(--border-active); }
.table-count { font-size: var(--font-size-sm); color: var(--text-muted); }

.table-scroll { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.data-table th {
  padding: 10px 12px; text-align: left; border-bottom: 2px solid var(--border-color);
  color: var(--text-secondary); font-weight: 600; white-space: nowrap;
}
.data-table td {
  padding: 8px 12px; border-bottom: 1px solid var(--border-color);
  color: var(--text-primary); max-width: 300px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.data-table tbody tr:hover { background: var(--bg-card-hover); }
.col-rating { width: 100px; }
.col-title { width: 180px; }
.col-content { min-width: 200px; }
.col-version { width: 80px; }
.col-date { width: 100px; }
.col-votes { width: 60px; text-align: center; }
.stars { color: var(--color-warning); font-size: 0.8rem; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; padding: var(--space-2xl);
  color: var(--text-muted); gap: var(--space-sm);
}
.empty-state span { font-size: 2rem; }
</style>