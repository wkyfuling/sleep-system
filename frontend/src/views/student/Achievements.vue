<script setup>
import { onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { achievementApi } from '@/api/achievement'

const loading = ref(false)
const data = ref(null)

async function load() {
  loading.value = true
  try {
    data.value = await achievementApi.myAchievements()
  } finally {
    loading.value = false
  }
}

function fmtDate(iso) {
  if (!iso) return ''
  return dayjs(iso).format('YYYY-MM-DD')
}

onMounted(load)
</script>

<template>
  <el-card shadow="never" v-loading="loading">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <b>🏅 成就徽章</b>
        <span v-if="data" style="font-size:13px; color:#909399">
          已解锁 {{ data.unlocked_count }} / {{ data.total }}
        </span>
      </div>
    </template>

    <!-- 进度条 -->
    <el-progress
      v-if="data"
      :percentage="Math.round(data.unlocked_count / data.total * 100)"
      :color="data.unlocked_count === data.total ? '#67c23a' : '#409eff'"
      style="margin-bottom: 20px"
    />

    <el-row v-if="data" :gutter="12">
      <el-col
        v-for="ach in data.achievements"
        :key="ach.code"
        :span="8"
        style="margin-bottom: 12px"
      >
        <el-card
          shadow="never"
          :class="['ach-card', ach.unlocked ? 'unlocked' : 'locked']"
        >
          <div class="ach-icon">{{ ach.icon }}</div>
          <div class="ach-name">{{ ach.name }}</div>
          <div class="ach-desc">{{ ach.description }}</div>
          <div v-if="ach.unlocked" class="ach-date">{{ fmtDate(ach.unlocked_at) }} 解锁</div>
          <div v-else class="ach-locked-tip">未解锁</div>
        </el-card>
      </el-col>
    </el-row>
  </el-card>
</template>

<style scoped>
.ach-card { text-align: center; padding: 4px; transition: all 0.2s; }
.unlocked { border-color: #e6a23c; background: #fffbf0; }
.locked { opacity: 0.45; filter: grayscale(80%); }
.ach-icon { font-size: 36px; margin-bottom: 6px; }
.ach-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.ach-desc { font-size: 12px; color: #909399; margin-bottom: 4px; min-height: 32px; }
.ach-date { font-size: 11px; color: #e6a23c; }
.ach-locked-tip { font-size: 11px; color: #c0c4cc; }
</style>
