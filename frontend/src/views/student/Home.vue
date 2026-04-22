<script setup>
import { computed, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { sleepApi } from '@/api/sleep'

const router = useRouter()
const userStore = useUserStore()
const profile = computed(() => userStore.user?.profile)

const loading = ref(false)
const stats = ref(null)
let chartInstance = null

const statusMap = {
  normal:   { label: '健康', color: '#67c23a' },
  warning:  { label: '一般', color: '#e6a23c' },
  abnormal: { label: '异常', color: '#f56c6c' },
  severe:   { label: '严重', color: '#c0392b' },
  missed:   { label: '未打卡', color: '#909399' },
}

function fmtDuration(mins) {
  if (!mins) return '—'
  return `${Math.floor(mins / 60)}h ${mins % 60}min`
}

async function loadStats() {
  loading.value = true
  try {
    stats.value = await sleepApi.weekStats()
    renderChart()
  } catch (e) {
    // 未打过卡也正常
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('week-chart')
  if (!el || !stats.value?.days) return

  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(el)

  const days = stats.value.days
  const dates = days.map(d => d.date.slice(5)) // MM-DD
  const scores = days.map(d => d.quality_score)
  const colors = days.map(d => statusMap[d.status]?.color || '#909399')

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const d = days[params[0].dataIndex]
        return `${d.date}<br/>质量分：${d.quality_score}<br/>时长：${fmtDuration(d.duration_minutes)}<br/>入睡：${d.bedtime || '—'} 起床：${d.wake_time || '—'}`
      },
    },
    grid: { left: 30, right: 10, top: 20, bottom: 24 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', min: 0, max: 100, splitNumber: 4 },
    series: [{
      type: 'bar',
      data: scores.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
      barMaxWidth: 40,
      label: { show: true, position: 'top', fontSize: 11 },
    }],
  })
}

const shortcuts = [
  { icon: '✏️', label: '晨间打卡', path: '/student/checkin' },
  { icon: '📚', label: '历史记录', path: '/student/history' },
  { icon: '🌡️', label: '睡眠热力图', path: '/student/heatmap' },
  { icon: '🏆', label: '班级排行', path: '/student/ranking' },
]

onMounted(loadStats)
</script>

<template>
  <div class="page-shell dashboard">
    <section class="page-hero">
      <div>
        <h1>{{ profile?.real_name || '同学' }}的睡眠自管台</h1>
        <p>回顾昨晚睡眠、查看近 7 天趋势、获取 AI 建议，并通过持续打卡养成稳定作息。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="router.push('/student/checkin')">晨间打卡</el-button>
        <el-button size="large" @click="router.push('/student/ai')">AI 建议</el-button>
      </div>
    </section>

    <!-- 顶部个人信息卡 -->
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never" class="info-card panel">
          <div class="welcome-row">
            <div>
              <div class="welcome-name">
                👋 你好，{{ profile?.real_name }}
                <el-tag size="small" style="margin-left: 8px">{{ profile?.grade || '学生' }}</el-tag>
              </div>
              <div class="sub-text">{{ profile?.classroom?.name || '暂未加入班级' }}・学号 {{ profile?.student_no }}</div>
            </div>
            <el-button type="primary" @click="router.push('/student/checkin')">
              ＋ 晨间打卡
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="streak-card panel">
          <div class="streak-inner" v-if="stats">
            <div class="streak-num">{{ stats.streak }}</div>
            <div class="streak-label">连续打卡天数 🔥</div>
            <el-tag :type="stats.today_checked ? 'success' : 'info'" size="small">
              昨夜：{{ stats.today_checked ? '已打卡' : '未打卡' }}
            </el-tag>
          </div>
          <div v-else class="streak-inner">
            <div class="streak-num">—</div>
            <div class="streak-label">加载中…</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 近 7 天概览 -->
    <div class="metric-grid" v-if="stats">
      <div class="metric-tile">
        <div class="metric-title">近 7 夜平均质量分</div>
        <div class="metric-main">{{ stats.avg_quality }}</div>
        <div class="metric-foot">满分 100 分</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">近 7 天平均时长</div>
        <div class="metric-main">{{ fmtDuration(stats.avg_duration) }}</div>
        <div class="metric-foot">目标 {{ profile?.target_sleep_hours || 8 }} 小时</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">昨夜睡眠状态</div>
        <div class="metric-main">
          <el-tag :color="statusMap[stats.today_status]?.color" style="color:#fff; border:0">
            {{ statusMap[stats.today_status]?.label }}
          </el-tag>
        </div>
        <div class="metric-foot">起床后回顾打卡</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">连续打卡</div>
        <div class="metric-main">{{ stats.streak }} 天</div>
        <div class="metric-foot">{{ stats.today_checked ? '昨夜已完成' : '昨夜未完成' }}</div>
      </div>
    </div>

    <!-- 7 天柱状图 -->
    <el-card shadow="never" class="panel" v-loading="loading">
      <template #header>
        <span>📊 近 7 夜睡眠质量分</span>
        <el-button link style="float:right" @click="router.push('/student/history')">查看历史 →</el-button>
      </template>
      <div id="week-chart" style="height: 220px" />
      <div v-if="!stats && !loading" class="no-data">还没有打卡记录，快去打卡吧 🌙</div>
    </el-card>

    <!-- 快捷入口 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="6" v-for="item in shortcuts" :key="item.path">
        <el-card shadow="hover" class="shortcut-card panel" @click="router.push(item.path)">
          <div class="shortcut-icon">{{ item.icon }}</div>
          <div class="shortcut-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard { padding: 4px 0; }
.info-card, .streak-card { height: 100%; }

.welcome-row { display: flex; justify-content: space-between; align-items: center; }
.welcome-name { font-size: 18px; font-weight: 600; }
.sub-text { font-size: 13px; color: #909399; margin-top: 4px; }

.streak-inner { text-align: center; padding: 8px 0; }
.streak-num { font-size: 42px; font-weight: 700; color: #e6a23c; line-height: 1; }
.streak-label { font-size: 13px; color: #606266; margin: 4px 0 8px; }

.shortcut-card { text-align: center; cursor: pointer; padding: 12px 0; }
.shortcut-card:hover { background: #f5f7fa; }
.shortcut-icon { font-size: 28px; margin-bottom: 6px; }
.shortcut-label { font-size: 13px; color: #606266; }

.no-data { text-align: center; color: #c0c4cc; padding: 40px 0; }
</style>
