<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { aiApi } from '@/api/ai'

const loading = ref(false)
const historyLoading = ref(false)
const currentAdvice = ref(null)
const history = ref([])
const remaining = ref(3)

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await aiApi.history()
    history.value = res.results
  } finally {
    historyLoading.value = false
  }
}

async function fetchAdvice() {
  loading.value = true
  try {
    const res = await aiApi.getAdvice()
    currentAdvice.value = res
    remaining.value = res.remaining_today
    await loadHistory()
    ElMessage.success('AI 建议已生成')
  } catch (e) {
    if (e?.response?.status === 429) {
      ElMessage.warning('今日 AI 建议已达上限（3次），明天再来 😴')
    }
  } finally {
    loading.value = false
  }
}

function fmtTime(iso) {
  return dayjs(iso).format('MM-DD HH:mm')
}

onMounted(loadHistory)
</script>

<template>
  <div>
    <!-- 触发按钮 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <b>🤖 AI 睡眠健康建议</b>
        <el-tag style="float:right" type="info" size="small">今日剩余 {{ remaining }} 次</el-tag>
      </template>

      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="remaining <= 0"
        @click="fetchAdvice"
        style="width: 100%; margin-bottom: 16px"
      >
        {{ loading ? '正在分析你的睡眠数据…' : '✨ 获取今日 AI 建议' }}
      </el-button>

      <!-- 最新建议展示 -->
      <transition name="fade">
        <el-card v-if="currentAdvice" shadow="never" class="advice-card">
          <div class="advice-header">
            <span>{{ currentAdvice.is_mock ? '📋 规则建议' : '🧠 AI 分析' }}</span>
            <el-tag v-if="currentAdvice.is_mock" type="warning" size="small">本地建议</el-tag>
            <el-tag v-else type="success" size="small">AI 生成</el-tag>
          </div>
          <div class="advice-text">{{ currentAdvice.advice_text }}</div>
        </el-card>
      </transition>
    </el-card>

    <!-- 历史记录 -->
    <el-card shadow="never" v-loading="historyLoading">
      <template #header><b>📜 历史建议</b></template>
      <div v-if="history.length === 0" class="empty">暂无历史建议，点击上方按钮生成第一条 🌙</div>
      <div v-for="item in history" :key="item.id" class="history-item">
        <div class="history-meta">
          <el-tag :type="item.is_mock ? 'warning' : 'success'" size="small">
            {{ item.is_mock ? '规则建议' : 'AI 分析' }}
          </el-tag>
          <span class="history-time">{{ fmtTime(item.created_at) }}</span>
        </div>
        <div class="history-text">{{ item.advice_text }}</div>
        <el-divider />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.advice-card { background: #f0f9ff; border: 1px solid #bfdbfe; }
.advice-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; font-weight: 600; }
.advice-text { white-space: pre-line; line-height: 1.8; color: #374151; }
.history-item { margin-bottom: 4px; }
.history-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.history-time { font-size: 12px; color: #9ca3af; }
.history-text { white-space: pre-line; font-size: 14px; color: #606266; line-height: 1.7; }
.empty { text-align: center; color: #c0c4cc; padding: 40px 0; }
.fade-enter-active { transition: opacity 0.4s; }
.fade-enter-from { opacity: 0; }
</style>
