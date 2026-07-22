<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal">
          <div class="modal-header">
            <h2 class="modal-title">LLM 模型配置</h2>
            <button class="btn-close" @click="$emit('close')">&times;</button>
          </div>

          <div class="modal-body">
            <!-- Provider 选择 -->
            <div class="field">
              <label class="label">选择模型提供商</label>
              <div class="provider-grid">
                <button
                  v-for="p in providers"
                  :key="p.key"
                  :class="['provider-btn', { active: form.provider === p.key }]"
                  @click="selectProvider(p)"
                >
                  <span class="provider-check" v-if="form.provider === p.key">&#10003;</span>
                  <span class="provider-name">{{ p.name }}</span>
                  <span class="provider-hint">{{ p.requires_key ? '需要 API Key' : '本地运行，无需 Key' }}</span>
                </button>
              </div>
            </div>

            <!-- 模型选择 -->
            <div class="field">
              <label class="label">模型</label>
              <select v-model="form.model" class="input">
                <option v-for="m in currentModels" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>

            <!-- API Key -->
            <div v-if="currentProviderInfo.requires_key" class="field">
              <label class="label">
                API Key
                <a class="key-link" :href="keyUrl" target="_blank">获取 Key &rarr;</a>
              </label>
              <div class="key-input-row">
                <input
                  :type="showKey ? 'text' : 'password'"
                  v-model="form.api_key"
                  class="input key-input"
                  :placeholder="apiKeySet ? 'API Key 已保存，留空则不修改' : '输入 API Key'"
                />
                <button type="button" class="btn-toggle" @click="showKey = !showKey">
                  {{ showKey ? '隐藏' : '显示' }}
                </button>
              </div>
              <div v-if="apiKeySet && !form.api_key" class="key-status">Key 已配置，如需修改请输入新 Key</div>
            </div>

            <!-- Base URL -->
            <div class="field">
              <label class="label">Base URL</label>
              <input v-model="form.base_url" class="input" placeholder="留空使用默认地址" />
            </div>

            <!-- 测试结果 -->
            <div v-if="testResult" :class="['result-box', testResult.success ? 'result-ok' : 'result-fail']">
              {{ testResult.success ? '连接成功 (' + testResult.latency_ms + 'ms)' : testResult.error }}
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-cancel" @click="$emit('close')">取消</button>
            <button class="btn-test" @click="testConnection" :disabled="testing">
              {{ testing ? '测试中...' : '测试连接' }}
            </button>
            <button class="btn-save" @click="save" :disabled="saving">
              {{ saving ? '保存中...' : '保存配置' }}
            </button>
          </div>

          <!-- Toast -->
          <Transition name="toast">
            <div v-if="toast" class="toast">{{ toast }}</div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close', 'saved'])

const showKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const toast = ref('')
const providers = ref([])

const form = reactive({
  provider: 'openai',
  model: 'gpt-4o-mini',
  api_key: '',
  base_url: '',
  timeout: 120,
})

const apiKeySet = ref(false)  // 后端已保存的 key 状态

const KEY_URLS = {
  openai: 'https://platform.openai.com/api-keys',
  deepseek: 'https://platform.deepseek.com/api_keys',
  qwen: 'https://dashscope.console.aliyun.com/',
  ollama: '',
}

const currentProviderInfo = computed(() => {
  return providers.value.find(p => p.key === form.provider) || providers.value[0] || {}
})

const currentModels = computed(() => currentProviderInfo.value.models || [])

const keyUrl = computed(() => KEY_URLS[form.provider] || '')

watch(() => props.visible, (v) => {
  if (v) fetchSettings()
})

async function fetchSettings() {
  testResult.value = null
  try {
    const res = await fetch('/api/settings/llm')
    const data = await res.json()
    providers.value = data.providers || []
    const cur = data.current || {}
    form.provider = cur.provider || 'openai'
    form.model = cur.model || 'gpt-4o-mini'
    form.base_url = cur.base_url || ''
    form.timeout = cur.timeout || 120
    apiKeySet.value = cur.api_key_set || false
  } catch (e) {
    console.error('Failed to fetch LLM settings:', e)
  }
}

function selectProvider(p) {
  form.provider = p.key
  form.model = (p.models && p.models[0]) || ''
  form.base_url = p.default_base_url || ''
  form.api_key = ''
  testResult.value = null
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const res = await fetch('/api/settings/llm/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    testResult.value = await res.json()
  } catch (e) {
    testResult.value = { success: false, error: '网络请求失败' }
  } finally {
    testing.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const res = await fetch('/api/settings/llm', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    const data = await res.json()
    if (data.success) {
      showToast('配置已保存')
      emit('saved')
      setTimeout(() => emit('close'), 600)
    } else {
      showToast('保存失败')
    }
  } catch (e) {
    showToast('网络请求失败')
  } finally {
    saving.value = false
  }
}

function showToast(msg) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 2000)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-lg);
  width: 520px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}
.modal-title {
  font-size: 18px;
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
  line-height: 1;
}
.btn-close:hover { color: var(--text-primary); }
.modal-body {
  padding: 24px;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}
.field {
  margin-bottom: 20px;
}
.label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.key-link {
  font-weight: 400;
  font-size: 12px;
  color: var(--color-primary);
  text-decoration: none;
}
.key-link:hover { text-decoration: underline; }
.input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.input:focus {
  border-color: var(--color-primary);
}
select.input {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2394a3b8' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}
.provider-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.provider-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 12px;
  background: var(--bg-input);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}
.provider-btn:hover {
  border-color: var(--text-muted);
}
.provider-btn.active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(0, 212, 255, 0.05);
}
.provider-check {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-primary);
}
.provider-name {
  font-size: 14px;
  font-weight: 600;
}
.provider-hint {
  font-size: 11px;
  opacity: 0.7;
}
.key-input-row {
  display: flex;
  gap: 8px;
}
.key-input {
  flex: 1;
  font-family: var(--font-family-mono);
}
.key-status {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-success);
}
.btn-toggle {
  padding: 0 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--border-radius);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-toggle:hover { color: var(--text-primary); }
.result-box {
  padding: 10px 14px;
  border-radius: var(--border-radius);
  font-size: 13px;
  margin-top: 4px;
  word-break: break-all;
}
.result-ok {
  background: rgba(0, 230, 118, 0.1);
  border: 1px solid var(--color-success);
  color: var(--color-success);
}
.result-fail {
  background: rgba(255, 82, 82, 0.1);
  border: 1px solid var(--color-error);
  color: var(--color-error);
}
.btn-cancel, .btn-test, .btn-save {
  padding: 10px 22px;
  border-radius: var(--border-radius);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}
.btn-cancel:hover { border-color: var(--text-muted); color: var(--text-primary); }
.btn-test {
  background: transparent;
  border: 1px solid var(--color-info);
  color: var(--color-info);
}
.btn-test:hover:not(:disabled) { background: rgba(68, 138, 255, 0.1); }
.btn-save {
  background: var(--color-primary);
  border: none;
  color: var(--bg-primary);
  font-weight: 600;
}
.btn-save:hover:not(:disabled) { filter: brightness(1.1); }
.btn-test:disabled, .btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.toast {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  background: var(--color-success);
  color: #fff;
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 500;
  box-shadow: var(--shadow-md);
  z-index: 10;
}
.toast-enter-active, .toast-leave-active { transition: all 0.3s; }
.toast-enter-from { opacity: 0; transform: translateX(-50%) translateY(10px); }
.toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(-10px); }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
