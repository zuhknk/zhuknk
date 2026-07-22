<template>
  <div class="review-table-container">
    <div class="table-toolbar">
      <input
        v-model="store.reviewFilter.search"
        type="text"
        class="search-input"
        placeholder="搜索评论内容、标题、作者..."
      />
      <select v-model="store.reviewFilter.rating" class="filter-select">
        <option value="0">全部评分</option>
        <option value="5">★★★★★</option>
        <option value="4">★★★★</option>
        <option value="3">★★★</option>
        <option value="2">★★</option>
        <option value="1">★</option>
      </select>
      <select v-model="store.reviewFilter.sort" class="filter-select">
        <option value="date-desc">最新优先</option>
        <option value="date-asc">最早优先</option>
        <option value="rating-desc">评分最高</option>
        <option value="rating-asc">评分最低</option>
      </select>
    </div>

    <div class="table-wrapper">
      <table class="review-table">
        <thead>
          <tr>
            <th class="col-rating">评分</th>
            <th class="col-title">标题</th>
            <th class="col-content">内容</th>
            <th class="col-author">作者</th>
            <th class="col-version">版本</th>
            <th class="col-date">日期</th>
            <th class="col-lang">语言</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in store.filteredReviews" :key="r.review_id">
            <td class="col-rating">
              <span :class="'rating-stars rating-' + r.rating">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
            </td>
            <td class="col-title" :title="r.title">{{ r.title || '-' }}</td>
            <td class="col-content" :title="r.content">{{ r.content.length > 100 ? r.content.slice(0, 100) + '...' : r.content }}</td>
            <td class="col-author">{{ r.author }}</td>
            <td class="col-version">{{ r.version }}</td>
            <td class="col-date">{{ r.date ? r.date.slice(0, 10) : '-' }}</td>
            <td class="col-lang"><span class="lang-badge">{{ r.language }}</span></td>
          </tr>
          <tr v-if="store.filteredReviews.length === 0">
            <td colspan="7" class="empty-row">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="table-footer">
      共 {{ store.filteredReviews.length }} 条评论
    </div>
  </div>
</template>

<script setup>
import { useAnalysisStore } from '../stores/analysis.js'
const store = useAnalysisStore()
</script>

<style scoped>
.review-table-container { font-size: 13px; }
.table-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.search-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
.search-input:focus { border-color: var(--color-primary); }
.filter-select {
  padding: 8px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}
.table-wrapper {
  overflow-x: auto;
  max-height: 500px;
  overflow-y: auto;
}
.review-table {
  width: 100%;
  border-collapse: collapse;
}
.review-table th {
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  padding: 10px 12px;
  text-align: left;
  font-size: 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}
.review-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.review-table tr:hover td { background: rgba(0, 212, 255, 0.03); }
.rating-stars { font-size: 12px; letter-spacing: 1px; }
.rating-5 { color: var(--color-success); }
.rating-4 { color: #69f0ae; }
.rating-3 { color: var(--color-warning); }
.rating-2 { color: #ff9100; }
.rating-1 { color: var(--color-error); }
.lang-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--bg-input);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-muted);
}
.empty-row { text-align: center; color: var(--text-muted); padding: 40px; }
.table-footer { font-size: 12px; color: var(--text-muted); margin-top: 8px; text-align: right; }
</style>
