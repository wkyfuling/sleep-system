<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
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

async function loadAlerts() {
  loading.value = true
  try {
    const res = await notificationApi.alerts()
    alerts.value = res.results
  } finally {
    loading.value = false
  }
}

// 发布公告弹窗
const broadcastVisible = ref(false)
const sending = ref(false)
const form = reactive({ title: '', content: '', include_parents: false })

async function sendBroadcast() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  sending.value = true
  try {
    const res = await notificationApi.broadcast(form)
    ElMessage.success(`公告已发送，共 ${res.sent} 人收到`)
    broadcastVisible.value = false
    form.title = ''
    form.content = ''
    form.include_parents = false
  } finally {
    sending.value = false
  }
}

onMounted(loadAlerts)
</script>

<template>
  <div>
    <!-- 预警列表 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div style="display:flex; align-items:center; justify-content:space-between">
          <b>⚠️ 睡眠预警中心</b>
          <div style="display:flex; gap:8px">
            <el-button size="small" @click="loadAlerts">刷新</el-button>
            <el-button type="primary" size="small" @click="broadcastVisible = true">
              📢 发布班级公告
            </el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="alerts" stripe>
        <el-table-column label="学生" width="120" prop="student_name" />
        <el-table-column label="日期" width="110" prop="date" />
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
        暂无预警记录 👏
      </div>
    </el-card>

    <!-- 发布公告弹窗 -->
    <el-dialog v-model="broadcastVisible" title="发布班级公告" width="500px">
      <el-form label-width="90px">
        <el-form-item label="公告标题">
          <el-input v-model="form.title" placeholder="输入公告标题" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="公告内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            placeholder="输入公告内容"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="同时通知">
          <el-checkbox v-model="form.include_parents">同时发送给家长</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="broadcastVisible = false">取消</el-button>
        <el-button type="primary" :loading="sending" @click="sendBroadcast">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>
