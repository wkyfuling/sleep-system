<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'

const router = useRouter()
const userStore = useUserStore()
const profile = computed(() => userStore.user?.profile)
const loading = ref(false)
const childStats = ref(null)
const childInfo = computed(() => childStats.value?.child || profile.value?.child)

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

async function loadChildStats() {
  if (!profile.value?.child) return
  loading.value = true
  try {
    childStats.value = await request.get('/parent/child/overview/')
  } finally {
    loading.value = false
  }
}

const shortcuts = [
  { icon: '⚠️', label: '预警通知', path: '/parent/alerts' },
  { icon: '💬', label: '消息中心', path: '/parent/messages' },
  { icon: '👤', label: '个人中心', path: '/parent/profile' },
]

onMounted(loadChildStats)
</script>

<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <h1>{{ childInfo?.real_name || '孩子' }}的睡眠关注台</h1>
        <p>查看孩子近 30 天睡眠表现、异常记录和风险状态，便于家校协同关注作息。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="router.push('/parent/messages')">联系老师/孩子</el-button>
        <el-button size="large" @click="router.push('/parent/alerts')">查看预警</el-button>
      </div>
    </section>

    <!-- 孩子信息卡 -->
    <el-card shadow="never" class="panel">
      <template #header>
        <b>👶 我的孩子概览</b>
      </template>
      <div v-if="childInfo">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="孩子姓名">{{ childInfo.real_name }}</el-descriptions-item>
          <el-descriptions-item label="学号">{{ childInfo.student_no }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ childInfo.classroom_name || childInfo.classroom || '—' }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ childInfo.grade || '—' }}</el-descriptions-item>
          <el-descriptions-item label="目标睡眠">{{ childInfo.target_sleep_hours }} 小时</el-descriptions-item>
          <el-descriptions-item label="风险状态">
            <el-tag :type="childInfo.risk_level === 'focus' ? 'danger' : 'success'">
              {{ childInfo.risk_level === 'focus' ? '重点关注' : '正常' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <el-empty v-else description="尚未绑定孩子，请联系孩子获取邀请码" />
    </el-card>

    <div class="metric-grid" v-if="childStats?.summary_30d">
      <div class="metric-tile">
        <div class="metric-title">30 天打卡</div>
        <div class="metric-main">{{ childStats.summary_30d.checked_days }}</div>
        <div class="metric-foot">有效记录天数</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">平均质量分</div>
        <div class="metric-main">{{ childStats.summary_30d.avg_quality }}</div>
        <div class="metric-foot">近 30 天</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">平均睡眠时长</div>
        <div class="metric-main">{{ fmtDuration(childStats.summary_30d.avg_duration) }}</div>
        <div class="metric-foot">目标 {{ childInfo?.target_sleep_hours || 8 }} 小时</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">异常次数</div>
        <div class="metric-main">{{ childStats.summary_30d.alert_count }}</div>
        <div class="metric-foot">严重/异常记录</div>
      </div>
    </div>

    <!-- 近期异常 -->
    <el-card shadow="never" class="panel" v-loading="loading">
      <template #header>
        <div style="display:flex; align-items:center; justify-content:space-between">
          <b>⚠️ 近期睡眠异常</b>
          <el-button link type="primary" @click="router.push('/parent/alerts')">查看全部 →</el-button>
        </div>
      </template>
      <div v-if="childStats?.recent_alerts?.length">
        <el-timeline>
          <el-timeline-item
            v-for="alert in childStats.recent_alerts"
            :key="alert.id"
            :color="statusMap[alert.status]?.color"
            :timestamp="alert.date"
          >
            <span>{{ statusMap[alert.status]?.label }}
              &nbsp;质量分 {{ alert.quality_score }}
              &nbsp;时长 {{ fmtDuration(alert.duration_minutes) }}
            </span>
          </el-timeline-item>
        </el-timeline>
      </div>
      <div v-else-if="!loading" style="text-align:center; color:#c0c4cc; padding: 20px 0">
        最近无睡眠异常记录 👏
      </div>
    </el-card>

    <!-- 快捷入口 -->
    <el-row :gutter="12">
      <el-col :span="8" v-for="s in shortcuts" :key="s.path">
        <el-card shadow="hover" class="shortcut panel" @click="router.push(s.path)">
          <div class="s-icon">{{ s.icon }}</div>
          <div class="s-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>


<style scoped>
.shortcut { text-align: center; cursor: pointer; padding: 12px 0; }
.shortcut:hover { background: #f5f7fa; }
.s-icon { font-size: 28px; margin-bottom: 6px; }
.s-label { font-size: 13px; color: #606266; }
</style>
