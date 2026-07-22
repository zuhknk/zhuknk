import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAnalysisStore = defineStore('analysis', () => {
  // ---- State ----
  const stage = ref('idle')
  const progress = ref(0)
  const message = ref('')
  const error = ref(null)
  const isRunning = ref(false)

  const appId = ref('')
  const appName = ref('')
  const totalReviews = ref(0)
  const cleanedReviews = ref(0)

  const activeTab = ref('reviews') // reviews | findings | requirements | testcases
  const progressEvents = ref([])
  const reviews = ref([])
  const findings = ref([])
  const requirements = ref([])
  const testCases = ref([])
  const validationReport = ref(null)
  const dataLimitations = ref([])
  const warnings = ref([])

  // ---- Computed ----
  const stageLabel = computed(() => {
    const labels = {
      idle: '就绪', parsing: '解析输入', collecting: '采集评论',
      cleaning: '清洗数据', analyzing: '语义分析', evidence: '证据验证',
      prd: '生成 PRD', testcase: '生成测试用例', validating: '最终校验',
      done: '完成', error: '错误',
    }
    return labels[stage.value] || stage.value
  })

  const hasResults = computed(() => stage.value === 'done')

  const tabItems = computed(() => [
    { key: 'reviews', label: `评论 (${reviews.value.length})`, icon: '💬' },
    { key: 'findings', label: `发现 (${findings.value.length})`, icon: '🔍' },
    { key: 'requirements', label: `需求 (${requirements.value.length})`, icon: '📋' },
    { key: 'testcases', label: `用例 (${testCases.value.length})`, icon: '✅' },
  ])

  // ---- Actions ----
  function startAnalysis() {
    stage.value = 'parsing'
    progress.value = 0
    message.value = ''
    error.value = null
    isRunning.value = true
    activeTab.value = 'reviews'
    progressEvents.value = []
    reviews.value = []
    findings.value = []
    requirements.value = []
    testCases.value = []
    validationReport.value = null
    dataLimitations.value = []
    warnings.value = []
  }

  function updateProgress(data) {
    stage.value = data.stage || stage.value
    progress.value = data.progress ?? progress.value
    message.value = data.message || message.value

    progressEvents.value.push({
      stage: data.stage, progress: data.progress,
      message: data.message, timestamp: data.timestamp || new Date().toISOString(),
    })

    if (data.data) {
      if (data.data.total_reviews != null) totalReviews.value = data.data.total_reviews
      if (data.data.cleaned_reviews != null) cleanedReviews.value = data.data.cleaned_reviews
      if (data.data.reviews) reviews.value = data.data.reviews
      if (data.data.findings) findings.value = data.data.findings
      if (data.data.requirements) requirements.value = data.data.requirements
      if (data.data.test_cases) testCases.value = data.data.test_cases
      if (data.data.validation_report) validationReport.value = data.data.validation_report
      if (data.data.data_limitations) dataLimitations.value = data.data.data_limitations
      if (data.data.warnings) warnings.value = data.data.warnings
      if (data.data.app_id) appId.value = data.data.app_id
      if (data.data.app_name) appName.value = data.data.app_name
    }
  }

  function finishAnalysis() {
    stage.value = 'done'
    progress.value = 100
    isRunning.value = false
  }

  function setError(msg) {
    stage.value = 'error'
    error.value = msg
    isRunning.value = false
  }

  function reset() {
    stage.value = 'idle'; progress.value = 0; message.value = ''
    error.value = null; isRunning.value = false
    appId.value = ''; appName.value = ''; activeTab.value = 'reviews'
    totalReviews.value = 0; cleanedReviews.value = 0
    progressEvents.value = []; reviews.value = []; findings.value = []
    requirements.value = []; testCases.value = []
    validationReport.value = null; dataLimitations.value = []; warnings.value = []
  }

  function exportResults() {
    const data = {
      app_id: appId.value,
      app_name: appName.value,
      total_reviews: totalReviews.value,
      cleaned_reviews: cleanedReviews.value,
      reviews: reviews.value,
      findings: findings.value,
      requirements: requirements.value,
      test_cases: testCases.value,
      validation_report: validationReport.value,
      data_limitations: dataLimitations.value,
      warnings: warnings.value,
      exported_at: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `review-analysis-${appId.value || 'export'}-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    // state
    stage, progress, message, error, isRunning,
    appId, appName, totalReviews, cleanedReviews, activeTab,
    progressEvents, reviews, findings, requirements, testCases,
    validationReport, dataLimitations, warnings,
    // computed
    stageLabel, hasResults, tabItems,
    // actions
    startAnalysis, updateProgress, finishAnalysis, setError, reset, exportResults,
  }
})