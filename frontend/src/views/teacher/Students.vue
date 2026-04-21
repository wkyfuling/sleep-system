<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const loading = ref(false)
const students = ref([])
const total = ref(0)
const statusFilter = ref('')

const statusMap = {
  normal:   { label: '健康', type: 'success' },
  warning:  { label: '一般', type: 'warning' },
  abnormal: { label: '异常', type: 'danger' },
  severe:   { label: '严重', type: 'danger' },
  missed:   { label: '未打卡', type: 'info' },
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await request.get('/auth/teacher/students/', { params })
    students.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

// 查看学生详情
const detailVisible = ref(false)
const selectedStudent = ref(null)
const trendData = ref([])
const trendLoading = ref(false)
const pdfLoading = ref(false)
const pdfYear = ref(new Date().getFullYear())
const pdfSemester = ref(1)

async function viewTrend(student) {
  selectedStudent.value = student
  detailVisible.value = true
  trendLoading.value = true
  try {
    const res = await request.get(`/auth/teacher/students/${student.student_id}/trend/`)
    trendData.value = res.records
  } finally {
    trendLoading.value = false
  }
}

function fmtDuration(mins) {
  if (!mins) return '—'
  return `${Math.floor(mins / 60)}h ${mins % 60}m`
}

async function downloadStudentPdf() {
  if (!selectedStudent.value) return
  pdfLoading.value = true
  try {
    const res = await request.get('/sleep/export/student-pdf/', {
      params: {
        student_id: selectedStudent.value.student_id,
        year: pdfYear.value,
        semester: pdfSemester.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res], { type: 'application/pdf' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${selectedStudent.value.real_name}_${pdfYear.value}_第${pdfSemester.value}学期睡眠报告.pdf`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('个人学期报告已下载')
  } finally {
    pdfLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-shell">
  <section class="page-hero">
    <div>
      <h1>学生睡眠档案</h1>
      <p>按风险等级和近 7 天异常情况筛查学生，查看个人趋势并导出学期睡眠报告。</p>
    </div>
    <div class="hero-actions">
      <el-button type="primary" size="large" @click="load">刷新列表</el-button>
    </div>
  </section>

  <el-card shadow="never" class="panel">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <b>👥 学生列表</b>
        <div style="display:flex; gap:8px">
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:130px" @change="() => load()">
            <el-option label="严重异常(近7天)" value="severe" />
            <el-option label="重点关注" value="focus" />
          </el-select>
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
    </template>

    <el-table v-loading="loading" :data="students" stripe>
      <el-table-column prop="student_no" label="学号" width="110" />
      <el-table-column prop="real_name" label="姓名" width="100" />
      <el-table-column prop="classroom" label="班级" width="120" />
      <el-table-column label="风险等级" width="110">
        <template #default="{ row }">
          <el-tag :type="row.risk_level === 'focus' ? 'danger' : 'success'" size="small">
            {{ row.risk_level === 'focus' ? '重点关注' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.latest_status]?.type" size="small">
            {{ statusMap[row.latest_status]?.label || '—' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="7天均分" width="90" prop="avg_quality_7d" align="center" />
      <el-table-column label="7天严重" width="90" prop="severe_count_7d" align="center">
        <template #default="{ row }">
          <span :style="row.severe_count_7d > 0 ? 'color:#f56c6c; font-weight:600' : ''">
            {{ row.severe_count_7d }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="viewTrend(row)">查看趋势</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 趋势详情弹窗 -->
  <el-dialog v-model="detailVisible" :title="`${selectedStudent?.real_name}（${selectedStudent?.student_no}）近30天睡眠`" width="700px">
    <div class="dialog-toolbar">
      <div class="toolbar-actions">
        <el-select v-model="pdfYear" style="width: 110px">
          <el-option v-for="y in [2024, 2025, 2026]" :key="y" :label="`${y}年`" :value="y" />
        </el-select>
        <el-select v-model="pdfSemester" style="width: 120px">
          <el-option label="第一学期" :value="1" />
          <el-option label="第二学期" :value="2" />
        </el-select>
      </div>
      <el-button type="primary" :loading="pdfLoading" @click="downloadStudentPdf">
        导出个人 PDF
      </el-button>
    </div>
    <el-table v-loading="trendLoading" :data="trendData" max-height="400" stripe size="small">
      <el-table-column prop="date" label="日期" width="100" />
      <el-table-column label="入睡" width="80" prop="bedtime" />
      <el-table-column label="起床" width="80" prop="wake_time" />
      <el-table-column label="时长" width="90">
        <template #default="{ row }">{{ fmtDuration(row.duration_minutes) }}</template>
      </el-table-column>
      <el-table-column prop="quality_score" label="质量分" width="80" align="center" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
  </div>
</template>

<style scoped>
.dialog-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
</style>
