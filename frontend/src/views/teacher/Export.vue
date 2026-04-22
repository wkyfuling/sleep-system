<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import request from '@/api/request'

const loadingType = ref('')
const selectedDate = ref(dayjs().format('YYYY-MM-DD'))
const selectedYear = ref(dayjs().year())
const selectedMonth = ref(dayjs().month() + 1)
const students = ref([])
const selectedStudentId = ref(null)
const selectedSemester = ref(1)
const classrooms = ref([])
const selectedClassroomId = ref(null)

async function getErrorMessage(e) {
  const data = e?.response?.data
  if (data instanceof Blob) {
    const text = await data.text().catch(() => '')
    if (text) {
      try {
        const json = JSON.parse(text)
        return json.detail || json.error || text
      } catch {
        return text
      }
    }
  }
  return data?.detail || data?.error || e?.message || '未知错误'
}

async function downloadFile(url, filename) {
  try {
    const res = await request.get(url, { responseType: 'blob' })
    const blob = new Blob([res], { type: res.type || 'application/octet-stream' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success(`${filename} 下载成功`)
  } catch (e) {
    ElMessage.error(`导出失败：${await getErrorMessage(e)}`)
  }
}

async function exportClassMonth() {
  loadingType.value = 'month'
  const classroomParam = selectedClassroomId.value ? `&classroom_id=${selectedClassroomId.value}` : ''
  await downloadFile(
    `/sleep/export/class-month/?year=${selectedYear.value}&month=${selectedMonth.value}${classroomParam}`,
    `班级月报_${selectedYear.value}${String(selectedMonth.value).padStart(2,'0')}.xlsx`
  )
  loadingType.value = ''
}

async function exportDayOverview() {
  loadingType.value = 'day'
  const classroomParam = selectedClassroomId.value ? `&classroom_id=${selectedClassroomId.value}` : ''
  await downloadFile(
    `/sleep/export/day-overview/?date=${selectedDate.value}${classroomParam}`,
    `日报_${selectedDate.value}.xlsx`
  )
  loadingType.value = ''
}

async function loadStudents() {
  const params = selectedClassroomId.value ? { classroom_id: selectedClassroomId.value } : {}
  const res = await request.get('/auth/teacher/students/', { params })
  students.value = res.results || []
  selectedStudentId.value = students.value[0]?.student_id || null
}

async function loadClassrooms() {
  const res = await request.get('/auth/teacher/class-overview/')
  classrooms.value = res.classrooms || []
  selectedClassroomId.value = classrooms.value[0]?.classroom_id || null
}

async function exportStudentPdf() {
  if (!selectedStudentId.value) {
    ElMessage.warning('请选择学生')
    return
  }
  loadingType.value = 'pdf'
  await downloadFile(
    `/sleep/export/student-pdf/?student_id=${selectedStudentId.value}&year=${selectedYear.value}&semester=${selectedSemester.value}`,
    `个人学期睡眠报告_${selectedYear.value}_S${selectedSemester.value}.pdf`
  )
  loadingType.value = ''
}

async function init() {
  await loadClassrooms()
  await loadStudents()
}

onMounted(init)
</script>

<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <h1>报表导出中心</h1>
        <p>支持班级月报、单日概览和个人学期报告，覆盖比赛演示中的三类导出场景。</p>
      </div>
    </section>

    <el-card shadow="never" class="panel">
      <template #header><b>📊 报表导出</b></template>

      <el-row :gutter="20">
        <el-col :span="24" v-if="classrooms.length > 1">
          <el-form-item label="导出班级" label-width="80px">
            <el-select v-model="selectedClassroomId" style="width: 220px" @change="loadStudents">
              <el-option
                v-for="c in classrooms"
                :key="c.classroom_id"
                :label="c.classroom_name"
                :value="c.classroom_id"
              />
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 班级月报 -->
        <el-col :span="8">
          <div class="export-card">
            <div class="export-icon">📅</div>
            <div class="export-title">班级月报 Excel</div>
            <div class="export-desc">包含全班每日打卡质量分，支持颜色标注状态</div>
            <div class="export-controls">
              <el-select v-model="selectedYear" style="width: 100px">
                <el-option v-for="y in [2024,2025,2026]" :key="y" :label="`${y}年`" :value="y" />
              </el-select>
              <el-select v-model="selectedMonth" style="width: 80px">
                <el-option v-for="m in 12" :key="m" :label="`${m}月`" :value="m" />
              </el-select>
            </div>
            <el-button
              type="primary"
              :loading="loadingType === 'month'"
              @click="exportClassMonth"
              style="width: 100%; margin-top: 12px"
            >
              下载 Excel
            </el-button>
          </div>
        </el-col>

        <!-- 单日概览 -->
        <el-col :span="8">
          <div class="export-card">
            <div class="export-icon">📋</div>
            <div class="export-title">单日班级概览 Excel</div>
            <div class="export-desc">某一天全班的入睡/起床/时长/状态明细</div>
            <div class="export-controls">
              <el-date-picker
                v-model="selectedDate"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                style="width: 160px"
              />
            </div>
            <el-button
              type="success"
              :loading="loadingType === 'day'"
              @click="exportDayOverview"
              style="width: 100%; margin-top: 12px"
            >
              下载 Excel
            </el-button>
          </div>
        </el-col>

        <!-- 个人 PDF -->
        <el-col :span="8">
          <div class="export-card">
            <div class="export-icon">📄</div>
            <div class="export-title">个人学期报 PDF</div>
            <div class="export-desc">生成单个学生的学期睡眠质量报告，适合家校沟通</div>
            <div class="export-controls vertical">
              <el-select v-model="selectedStudentId" filterable placeholder="选择学生" style="width: 180px">
                <el-option
                  v-for="s in students"
                  :key="s.student_id"
                  :label="`${s.real_name} ${s.student_no}`"
                  :value="s.student_id"
                />
              </el-select>
              <div class="inline-controls">
                <el-select v-model="selectedYear" style="width: 100px">
                  <el-option v-for="y in [2024,2025,2026]" :key="y" :label="`${y}年`" :value="y" />
                </el-select>
                <el-select v-model="selectedSemester" style="width: 100px">
                  <el-option label="上学期" :value="1" />
                  <el-option label="下学期" :value="2" />
                </el-select>
              </div>
            </div>
            <el-button
              type="warning"
              :loading="loadingType === 'pdf'"
              @click="exportStudentPdf"
              style="width: 100%; margin-top: 12px"
            >
              下载 PDF
            </el-button>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<style scoped>
.export-card {
  min-height: 286px;
  text-align: center;
  padding: 18px;
  border: 1px solid #e8edf5;
  border-radius: 8px;
  background: #fff;
}
.export-icon { font-size: 40px; margin-bottom: 8px; }
.export-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.export-desc { font-size: 13px; color: #909399; margin-bottom: 12px; min-height: 36px; }
.export-controls { display: flex; gap: 8px; justify-content: center; }
.vertical { flex-direction: column; align-items: center; }
.inline-controls { display: flex; gap: 8px; }
</style>
