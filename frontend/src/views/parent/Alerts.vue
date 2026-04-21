<script setup>
import { onMounted, ref } from 'vue'
import { notificationApi } from '@/api/notification'

const loading = ref(false)
const alerts = ref([])

const statusMap = {
  severe:   { label: '严重', type: 'danger' },
  abnormal: { label: '异常', type: 'warning' },
}

function fmtDuration(mins) {
  if (!mins) return '—'
  return `${Math.floor(mins / 60)}h ${mins % 60}min`
}

async function load() {
  loading.value = true
  try {
    const res = await notificationApi.alerts()
    alerts.value = res.results
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <b>⚠️ 孩子睡眠预警</b>
    </template>

    <el-table v-loading="loading" :data="alerts" stripe>
      <el-table-column label="日期" width="120" prop="date" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" effect="dark">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="质量分" width="90" prop="quality_score" align="center" />
      <el-table-column label="睡眠时长" width="110">
        <template #default="{ row }">{{ fmtDuration(row.duration_minutes) }}</template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && alerts.length === 0" style="text-align:center; color:#c0c4cc; padding:40px 0">
      最近无睡眠预警 👏
    </div>
  </el-card>
</template>
