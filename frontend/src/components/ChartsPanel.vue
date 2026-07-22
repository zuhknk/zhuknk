<template>
  <div class="charts-panel">
    <div v-if="store.reviews.length === 0" class="empty-state">暂无可视化数据</div>
    <div v-else class="charts-grid">
      <!-- 评分分布 -->
      <div class="chart-card">
        <h3 class="chart-title">评分分布</h3>
        <div class="chart-container">
          <canvas ref="ratingCanvas"></canvas>
        </div>
        <p class="chart-summary">平均评分 {{ avgRating }} / 5（共 {{ store.reviews.length }} 条）</p>
      </div>

      <!-- 情感分布 -->
      <div class="chart-card">
        <h3 class="chart-title">情感分布</h3>
        <div class="chart-container">
          <canvas ref="sentimentCanvas"></canvas>
        </div>
      </div>

      <!-- 词云 -->
      <div class="chart-card chart-wide">
        <h3 class="chart-title">高频词</h3>
        <div class="word-cloud">
          <span
            v-for="(item, i) in wordCloud"
            :key="i"
            class="cloud-word"
            :style="{ fontSize: item.size + 'px', color: item.color, opacity: item.opacity }"
          >{{ item.word }}</span>
        </div>
      </div>

      <!-- 评分趋势 -->
      <div v-if="hasDateData" class="chart-card chart-wide">
        <h3 class="chart-title">评分趋势</h3>
        <div class="chart-container chart-container-wide">
          <canvas ref="trendCanvas"></canvas>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useAnalysisStore } from '../stores/analysis.js'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const store = useAnalysisStore()

const ratingCanvas = ref(null)
const sentimentCanvas = ref(null)
const trendCanvas = ref(null)

let ratingChart = null
let sentimentChart = null
let trendChart = null

const avgRating = computed(() => {
  if (store.reviews.length === 0) return '0'
  const sum = store.reviews.reduce((s, r) => s + r.rating, 0)
  return (sum / store.reviews.length).toFixed(1)
})

const hasDateData = computed(() => {
  return store.reviews.some(r => r.date && r.date.length > 5)
})

// 词云数据
const stopWords = new Set([
  'the', 'a', 'an', 'is', 'it', 'to', 'and', 'of', 'in', 'for', 'on', 'my', 'i',
  'this', 'that', 'with', 'you', 'do', 'at', 'be', 'not', 'but', 'was', 'are',
  'have', 'has', 'had', 'from', 'or', 'if', 'so', 'no', 'can', 'very', 'just',
  'its', 'me', 'we', 'they', 'what', 'when', 'how', 'all', 'would', 'there',
  'their', 'will', 'been', 'one', 'which', 'than', 'them', 'then', 'these',
  '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一',
  '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
  '看', '好', '自己', '这', '他', '她', '它', '们', '那', '被', '从', '把',
  'app', 'use', 'used', 'using', 'get', 'got', 'go', 'going', 'went',
])

const wordCloud = computed(() => {
  const freq = {}
  store.reviews.forEach(r => {
    const text = (r.title + ' ' + r.content).toLowerCase()
    const words = text.match(/[\u4e00-\u9fa5a-zA-Z]{2,}/g) || []
    words.forEach(w => {
      if (!stopWords.has(w) && w.length >= 2) {
        freq[w] = (freq[w] || 0) + 1
      }
    })
  })

  const sorted = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 50)

  if (sorted.length === 0) return []

  const maxFreq = sorted[0][1]
  const colors = ['#00d4ff', '#00e676', '#ffab00', '#ff5252', '#448aff', '#e040fb']

  return sorted.map(([word, count], i) => ({
    word,
    count,
    size: Math.max(12, Math.round(14 + (count / maxFreq) * 30)),
    color: colors[i % colors.length],
    opacity: 0.6 + (count / maxFreq) * 0.4,
  }))
})

function renderRatingChart() {
  if (!ratingCanvas.value) return
  if (ratingChart) ratingChart.destroy()

  const dist = [0, 0, 0, 0, 0]
  store.reviews.forEach(r => {
    if (r.rating >= 1 && r.rating <= 5) dist[r.rating - 1]++
  })

  ratingChart = new Chart(ratingCanvas.value, {
    type: 'bar',
    data: {
      labels: ['1 星', '2 星', '3 星', '4 星', '5 星'],
      datasets: [{
        data: dist,
        backgroundColor: ['#ff5252', '#ff9100', '#ffab00', '#66bb6a', '#00e676'],
        borderRadius: 4,
        barPercentage: 0.7,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' }, beginAtZero: true },
      },
    },
  })
}

function renderSentimentChart() {
  if (!sentimentCanvas.value || store.findings.length === 0) return
  if (sentimentChart) sentimentChart.destroy()

  const dist = { positive: 0, negative: 0, neutral: 0, mixed: 0 }
  store.findings.forEach(f => {
    if (dist[f.sentiment] !== undefined) dist[f.sentiment] += f.sample_count
  })

  const labels = { positive: '正面', negative: '负面', neutral: '中性', mixed: '混合' }
  const colors = { positive: '#00e676', negative: '#ff5252', neutral: '#64748b', mixed: '#ffab00' }

  const filtered = Object.entries(dist).filter(([, v]) => v > 0)

  sentimentChart = new Chart(sentimentCanvas.value, {
    type: 'doughnut',
    data: {
      labels: filtered.map(([k]) => labels[k]),
      datasets: [{
        data: filtered.map(([, v]) => v),
        backgroundColor: filtered.map(([k]) => colors[k]),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', padding: 12, font: { size: 12 } },
        },
      },
    },
  })
}

function renderTrendChart() {
  if (!trendCanvas.value || !hasDateData.value) return
  if (trendChart) trendChart.destroy()

  // 按日期聚合
  const dateMap = {}
  store.reviews.forEach(r => {
    if (!r.date) return
    const day = r.date.slice(0, 10)
    if (!day) return
    if (!dateMap[day]) dateMap[day] = { sum: 0, count: 0 }
    dateMap[day].sum += r.rating
    dateMap[day].count++
  })

  const sorted = Object.entries(dateMap)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-30) // 最近 30 天

  if (sorted.length < 2) return

  trendChart = new Chart(trendCanvas.value, {
    type: 'line',
    data: {
      labels: sorted.map(([d]) => d),
      datasets: [{
        data: sorted.map(([, v]) => (v.sum / v.count).toFixed(2)),
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0, 212, 255, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: '#00d4ff',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' }, min: 0, max: 5 },
      },
    },
  })
}

function renderAll() {
  nextTick(() => {
    renderRatingChart()
    renderSentimentChart()
    renderTrendChart()
  })
}

onMounted(renderAll)
watch(() => store.reviews, renderAll)
watch(() => store.findings, renderSentimentChart)
</script>

<style scoped>
.charts-panel { padding: 4px 0; }
.empty-state { text-align: center; color: var(--text-muted); padding: 60px 20px; }
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.chart-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px;
}
.chart-wide { grid-column: 1 / -1; }
.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}
.chart-container { height: 200px; position: relative; }
.chart-container-wide { height: 180px; }
.chart-summary {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  margin: 8px 0 0;
}
.word-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
  min-height: 100px;
}
.cloud-word {
  font-weight: 500;
  cursor: default;
  transition: transform 0.2s;
}
.cloud-word:hover { transform: scale(1.1); }
</style>
