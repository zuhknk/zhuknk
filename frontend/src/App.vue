<template>
  <div class="app-container">
    <header class="app-header">
      <h1 class="app-title">
        <span class="title-accent">LaienTech</span> App Review Analyzer
      </h1>
      <p class="app-subtitle">AI 驱动的应用评论智能分析平台</p>
    </header>
    <main class="app-main">
      <InputPanel />
      <ProgressPipeline />
    </main>
  </div>
</template>

<script setup>
import InputPanel from './components/InputPanel.vue'
import ProgressPipeline from './components/ProgressPipeline.vue'
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-family);
}
.app-header {
  text-align: center;
  padding: 32px 20px 16px;
  border-bottom: 1px solid var(--border-color);
}
.app-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.title-accent {
  color: var(--color-primary);
}
.app-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 8px 0 0;
}
.app-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 20px;
}
</style>
