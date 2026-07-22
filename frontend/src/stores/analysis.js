import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAnalysisStore = defineStore('analysis', () => {
  // ===== 状态 =====
  const stage = ref('idle')       // idle → parsing → collecting → cleaning → analyzing → evidence → prd → testcase → validating → done
  const progress = ref(0)
  const statusMessage = ref('')
  const error = ref('')
  const activeTab = ref('reviews')  // reviews | findings | requirements | testcases

  // 结果数据
  const reviews = ref([])
  const findings = ref([])
  const requirements = ref([])
  const testCases = ref([])
  const validationReport = ref(null)
  const cleaningStats = ref(null)
  const dataLimitations = ref([])
  const warnings = ref([])
  const analysisGoal = ref('')

  // 搜索/筛选
  const reviewFilter = ref({ search: '', rating: 0, sort: 'date-desc' })

  // ===== 计算属性 =====
  const isRunning = computed(() => stage.value !== 'idle' && stage.value !== 'done')
  const isDone = computed(() => stage.value === 'done')
  const hasError = computed(() => !!error.value)

  const filteredReviews = computed(() => {
    let result = [...reviews.value]
    const { search, rating, sort } = reviewFilter.value

    if (search) {
      const q = search.toLowerCase()
      result = result.filter(r =>
        r.title?.toLowerCase().includes(q) ||
        r.content?.toLowerCase().includes(q) ||
        r.author?.toLowerCase().includes(q)
      )
    }
    if (rating > 0) {
      result = result.filter(r => r.rating === rating)
    }
    // 排序
    if (sort === 'date-desc') result.sort((a, b) => (b.date || '').localeCompare(a.date || ''))
    else if (sort === 'date-asc') result.sort((a, b) => (a.date || '').localeCompare(b.date || ''))
    else if (sort === 'rating-desc') result.sort((a, b) => b.rating - a.rating)
    else if (sort === 'rating-asc') result.sort((a, b) => a.rating - b.rating)

    return result
  })

  // ===== 方法 =====
  function reset() {
    stage.value = 'idle'
    progress.value = 0
    statusMessage.value = ''
    error.value = ''
    activeTab.value = 'reviews'
    reviews.value = []
    findings.value = []
    requirements.value = []
    testCases.value = []
    validationReport.value = null
    cleaningStats.value = null
    dataLimitations.value = []
    warnings.value = []
    analysisGoal.value = ''
    reviewFilter.value = { search: '', rating: 0, sort: 'date-desc' }
  }

  function setError(msg) {
    error.value = msg
    stage.value = 'idle'
  }

  function handleSSEEvent(event, data) {
    switch (event) {
      case 'parsing':
      case 'collecting':
      case 'cleaning':
      case 'analyzing':
      case 'evidence':
      case 'prd':
      case 'testcase':
      case 'validating':
        stage.value = event
        progress.value = data.progress || 0
        statusMessage.value = data.message || ''
        if (data.stats) cleaningStats.value = data.stats
        break
      case 'done':
        stage.value = 'done'
        progress.value = 100
        reviews.value = data.reviews || []
        findings.value = data.findings || []
        requirements.value = data.requirements || []
        testCases.value = data.test_cases || []
        validationReport.value = data.validation_report || null
        dataLimitations.value = data.data_limitations || []
        warnings.value = data.warnings || []
        analysisGoal.value = data.analysis_goal || ''
        activeTab.value = 'findings'
        break
      case 'error':
        setError(data.message || '分析过程发生错误')
        break
    }
  }

  async function runAnalysis(payload) {
    reset()
    stage.value = 'parsing'
    progress.value = 5
    statusMessage.value = '正在连接分析服务...'

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status} ${response.statusText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            // 事件类型行，暂存
            const eventType = line.slice(7).trim()
            buffer = 'event:' + eventType + '\n' + buffer
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              // 从 buffer 中提取事件类型
              const eventMatch = buffer.match(/event:(\w+)/)
              const eventType = eventMatch ? eventMatch[1] : 'unknown'
              handleSSEEvent(eventType, data)
            } catch (e) {
              console.warn('SSE 解析失败:', line, e)
            }
          }
        }
      }
    } catch (e) {
      setError(e.message || '网络请求失败')
    }
  }

  function exportJSON() {
    const data = {
      reviews: reviews.value,
      findings: findings.value,
      requirements: requirements.value,
      test_cases: testCases.value,
      validation_report: validationReport.value,
      analysis_goal: analysisGoal.value,
      exported_at: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `app-review-analysis-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    stage, progress, statusMessage, error, activeTab,
    reviews, findings, requirements, testCases, validationReport,
    cleaningStats, dataLimitations, warnings, analysisGoal,
    reviewFilter, filteredReviews,
    isRunning, isDone, hasError,
    reset, setError, handleSSEEvent, runAnalysis, exportJSON,
  }
})
