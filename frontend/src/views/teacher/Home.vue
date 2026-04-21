<script setup>
import { computed, onMounted, nextTick, ref } from 'vue'
import * as echarts from 'echarts'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const router = useRouter()
const userStore = useUserStore()
const profile = computed(() => userStore.user?.profile)
const loading = ref(false)
const overview = ref(null)
const diagnosisLoading = ref(false)
const diagnosisVisible = ref(false)
const diagnosis = ref(null)
let chartInstance = null

function copyCode(code) {
  navigator.clipboard.writeText(code).catch(() => {})
  ElMessage.success(`已复制邀请码 ${code}`)
}

async function loadOverview() {
  loading.value = true
  try {
    const res = await request.get('/auth/teacher/class-overview/')
    overview.value = res.classrooms?.[0] || null
    await nextTick()
    renderChart()
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('teacher-pie')
  if (!el || !overview.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(el)

  const o = overview.value
  const checked = o.today_checked
  const unchecked = o.total_students - checked

  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      label: { formatter: '{b}: {c}人' },
      data: [
        { name: '已打卡', value: checked, itemStyle: { color: '#67c23a' } },
        { name: '未打卡', value: unchecked, itemStyle: { color: '#f0f0f0' } },
      ],
    }],
  })
}

const shortcuts = [
  { icon: '👥', label: '学生列表', path: '/teacher/students' },
  { icon: '⚠️', label: '预警中心', path: '/teacher/alerts' },
  { icon: '📢', label: '发布通知', path: '/teacher/notifications' },
  { icon: '📊', label: '报表导出', path: '/teacher/export' },
]

async function runDiagnosis() {
  diagnosisLoading.value = true
  try {
    diagnosis.value = await request.post('/teacher/ai/class-diagnosis/')
    diagnosisVisible.value = true
  } finally {
    diagnosisLoading.value = false
  }
}

onMounted(loadOverview)
</script>

<template>
  <div class="page-shell" v-loading="loading">
    <section class="page-hero">
      <div>
        <h1>班级睡眠治理工作台</h1>
        <p>聚合全班打卡率、质量分、严重异常和班级邀请码，便于老师快速发现风险并触达学生家长。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" size="large" :loading="diagnosisLoading" @click="runDiagnosis">
          生成班级 AI 诊断
        </el-button>
        <el-button size="large" @click="router.push('/teacher/export')">导出报表</el-button>
      </div>
    </section>

    <!-- 班级卡片 -->
    <div class="metric-grid" v-if="overview">
      <div class="metric-tile">
        <div class="metric-title">班级总人数</div>
        <div class="metric-main">{{ overview.total_students }}</div>
        <div class="metric-foot">{{ overview.classroom_name }}</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">今日打卡率</div>
        <div class="metric-main green">{{ overview.checkin_rate }}%</div>
        <div class="metric-foot">已打卡 {{ overview.today_checked }} 人</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">近 7 天平均质量</div>
        <div class="metric-main orange">{{ overview.avg_quality_7d }}</div>
        <div class="metric-foot">按有效打卡计算</div>
      </div>
      <div class="metric-tile" :class="{ warn: overview.severe_count > 0 }">
        <div class="metric-title">近 7 天严重异常</div>
        <div class="metric-main" :class="overview.severe_count > 0 ? 'red' : 'green'">
          {{ overview.severe_count }}
        </div>
        <div class="metric-foot">涉及学生人数</div>
      </div>
    </div>

    <!-- 图表 + 班级信息 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="10">
        <el-card shadow="never" class="panel" style="height: 300px">
          <template #header><b>今日打卡情况</b></template>
          <div id="teacher-pie" style="height: 220px" />
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never" class="panel" style="height: 300px">
          <template #header><b>班级信息</b></template>
          <div v-if="overview">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="班级名称">{{ overview.classroom_name }}</el-descriptions-item>
              <el-descriptions-item label="班级邀请码">
                <el-tag>{{ overview.invite_code }}</el-tag>
                <el-button link type="primary" size="small" @click="copyCode(overview.invite_code)">复制</el-button>
              </el-descriptions-item>
              <el-descriptions-item label="总人数">{{ overview.total_students }} 人</el-descriptions-item>
            </el-descriptions>
          </div>
          <el-empty v-else-if="!loading" description="暂无班级数据，先运行演示数据或在个人中心创建班级" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷入口 -->
    <el-row :gutter="12">
      <el-col :span="6" v-for="s in shortcuts" :key="s.path">
        <el-card shadow="hover" class="shortcut panel" @click="router.push(s.path)">
          <div class="s-icon">{{ s.icon }}</div>
          <div class="s-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-dialog v-model="diagnosisVisible" title="班级整体 AI 诊断" width="680px">
      <div v-if="diagnosis">
        <div class="diagnosis-stats">
          <el-tag>平均质量 {{ diagnosis.stats.avg_quality }}</el-tag>
          <el-tag type="success">平均时长 {{ diagnosis.stats.avg_duration_h }}h</el-tag>
          <el-tag :type="diagnosis.stats.severe_pct > 10 ? 'danger' : 'warning'">
            严重异常 {{ diagnosis.stats.severe_pct }}%
          </el-tag>
          <el-tag :type="diagnosis.is_mock ? 'warning' : 'success'">
            {{ diagnosis.is_mock ? '本地规则兜底' : 'AI 生成' }}
          </el-tag>
        </div>
        <div class="diagnosis-text">{{ diagnosis.advice_text }}</div>
      </div>
    </el-dialog>
  </div>
</template>


<style scoped>
.green { color: #67c23a !important; }
.orange { color: #e6a23c !important; }
.red { color: #f56c6c !important; }
.warn { border-color: #f56c6c; }
.shortcut { text-align: center; cursor: pointer; padding: 8px 0; }
.shortcut:hover { background: #f5f7fa; }
.s-icon { font-size: 28px; margin-bottom: 6px; }
.s-label { font-size: 13px; color: #606266; }
.diagnosis-stats { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.diagnosis-text { white-space: pre-line; line-height: 1.8; color: #374151; }
</style>
