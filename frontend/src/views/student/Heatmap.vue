<script setup>
import { onMounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { sleepApi } from '@/api/sleep'

const year = ref(dayjs().year())
const loading = ref(false)
let chartInstance = null

const statusColor = {
  normal:   '#67c23a',
  warning:  '#e6a23c',
  abnormal: '#f56c6c',
  severe:   '#c0392b',
  missed:   '#dfe6e9',
}

const statusLabel = {
  normal: '健康', warning: '一般', abnormal: '异常', severe: '严重', missed: '未打卡',
}

async function load() {
  loading.value = true
  try {
    const res = await sleepApi.heatmap(year.value)
    await nextTick()
    renderChart(res.data)
  } finally {
    loading.value = false
  }
}

function renderChart(data) {
  const el = document.getElementById('heatmap-chart')
  if (!el) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(el)

  // 构建全年日期数据
  const startDate = dayjs(`${year.value}-01-01`)
  const endDate = dayjs(`${year.value}-12-31`)
  const dataMap = {}
  data.forEach(d => { dataMap[d.date] = d })

  const calData = []
  let cur = startDate
  while (cur.isBefore(endDate) || cur.isSame(endDate, 'day')) {
    const key = cur.format('YYYY-MM-DD')
    const r = dataMap[key]
    calData.push([key, r ? r.value : 0, r ? r.status : ''])
    cur = cur.add(1, 'day')
  }

  chartInstance.setOption({
    tooltip: {
      formatter: (p) => {
        const [date, score, st] = p.data
        if (!st) return `${date}<br/>无记录`
        return `${date}<br/>质量分：${score}<br/>状态：${statusLabel[st] || st}`
      },
    },
    visualMap: {
      show: false,
      min: 0,
      max: 100,
      inRange: { color: ['#ebedf0', '#67c23a'] },
    },
    calendar: {
      top: 60,
      left: 50,
      right: 20,
      cellSize: [16, 16],
      range: year.value,
      itemStyle: { borderWidth: 2, borderColor: '#fff' },
      yearLabel: { show: false },
      dayLabel: { firstDay: 1, nameMap: ['日', '一', '二', '三', '四', '五', '六'] },
      monthLabel: { nameMap: 'CN' },
    },
    series: [{
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: calData,
    }],
  })
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <b>🌡️ 睡眠热力图</b>
        <div style="display:flex; gap:8px; align-items:center">
          <el-button size="small" :disabled="year <= 2020" @click="year--; load()">‹</el-button>
          <span style="font-weight:600; font-size:16px">{{ year }}</span>
          <el-button size="small" :disabled="year >= new Date().getFullYear()" @click="year++; load()">›</el-button>
        </div>
      </div>
    </template>

    <div v-loading="loading">
      <div id="heatmap-chart" style="height: 200px; width: 100%" />
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="legend-label">睡眠状态：</span>
      <span v-for="(color, key) in statusColor" :key="key" class="legend-item">
        <span class="legend-dot" :style="{ background: color }" />
        {{ statusLabel[key] }}
      </span>
    </div>

    <el-alert
      type="info"
      :closable="false"
      title="颜色越深表示睡眠质量越好（绿色=健康），灰色表示当天未打卡"
      style="margin-top: 12px"
    />
  </el-card>
</template>

<style scoped>
.legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #606266;
}
.legend-label { font-weight: 500; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-dot { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
</style>
