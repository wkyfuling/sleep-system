<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { notificationApi } from '@/api/notification'

const loading = ref(false)
const sending = ref(false)
const messages = ref([])
const total = ref(0)
const page = ref(1)

const form = reactive({
  title: '',
  content: '',
  include_parents: true,
})

const sentSummary = ref(null)

const latestMessages = computed(() => messages.value.slice(0, 6))

async function loadMessages() {
  loading.value = true
  try {
    const res = await notificationApi.list({ page: page.value })
    messages.value = res.results || []
    total.value = res.count || 0
  } finally {
    loading.value = false
  }
}

async function sendBroadcast() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('请填写通知标题和内容')
    return
  }
  sending.value = true
  try {
    const res = await notificationApi.broadcast({
      title: form.title.trim(),
      content: form.content.trim(),
      include_parents: form.include_parents,
    })
    sentSummary.value = res
    form.title = ''
    form.content = ''
    form.include_parents = true
    ElMessage.success(`通知已发送，共 ${res.sent} 人收到`)
    await loadMessages()
  } finally {
    sending.value = false
  }
}

function fmtTime(iso) {
  return iso ? dayjs(iso).format('MM-DD HH:mm') : '-'
}

onMounted(loadMessages)
</script>

<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <h1>班级通知发布</h1>
        <p>统一向本班学生发布作息提醒、班会通知和睡眠管理要求，可选择同步给家长。</p>
      </div>
      <div class="hero-actions">
        <el-tag effect="dark" type="info">老师 → 学生</el-tag>
        <el-tag effect="dark" type="warning">可同步家长</el-tag>
      </div>
    </section>

    <el-row :gutter="16">
      <el-col :span="15">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="toolbar-line">
              <b>发布班级公告</b>
              <el-switch
                v-model="form.include_parents"
                active-text="同步家长"
                inactive-text="仅学生"
              />
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="通知标题">
              <el-input
                v-model="form.title"
                maxlength="128"
                show-word-limit
                placeholder="例如：本周睡眠打卡提醒"
              />
            </el-form-item>
            <el-form-item label="通知内容">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="9"
                maxlength="2000"
                show-word-limit
                placeholder="输入要发送给学生和家长的具体内容"
              />
            </el-form-item>
          </el-form>

          <div class="submit-row">
            <el-button type="primary" size="large" :loading="sending" @click="sendBroadcast">
              发布通知
            </el-button>
            <el-button size="large" @click="() => { form.title = ''; form.content = '' }">清空</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="9">
        <div class="side-stack">
          <div class="metric-tile">
            <div class="metric-title">最近一次发送</div>
            <div class="metric-main">{{ sentSummary?.sent ?? '—' }}</div>
            <div class="metric-foot">收件人数</div>
          </div>

          <el-card shadow="never" class="panel">
            <template #header><b>通知建议模板</b></template>
            <div class="template-list">
              <button @click="form.title = '今晚 23:30 前准备入睡'; form.content = '请同学们今晚尽量在 23:30 前完成洗漱并放下电子设备，明早起床后及时完成睡眠打卡。'">晚间作息提醒</button>
              <button @click="form.title = '连续未打卡提醒'; form.content = '近期有同学出现连续未打卡情况，请大家起床后及时回顾填写昨晚入睡和今晨起床时间。'">未打卡提醒</button>
              <button @click="form.title = '睡眠健康班会通知'; form.content = '本周班会将进行睡眠健康主题交流，请同学们提前查看自己的近 7 天睡眠记录。'">主题班会通知</button>
            </div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <el-card shadow="never" class="panel" v-loading="loading">
      <template #header>
        <div class="toolbar-line">
          <b>我的收件箱</b>
          <el-button size="small" @click="loadMessages">刷新</el-button>
        </div>
      </template>
      <el-table :data="latestMessages" stripe>
        <el-table-column label="类型" width="110" prop="type" />
        <el-table-column label="标题" min-width="180" prop="title" />
        <el-table-column label="发件人" width="110" prop="sender_name" />
        <el-table-column label="时间" width="120">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="内容" min-width="260">
          <template #default="{ row }">{{ row.content }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !latestMessages.length" description="暂无消息" />
    </el-card>
  </div>
</template>

<style scoped>
.side-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.submit-row {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.template-list {
  display: grid;
  gap: 10px;
}

.template-list button {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f8fafc;
  color: #374151;
  text-align: left;
  cursor: pointer;
}

.template-list button:hover {
  border-color: #409eff;
  color: #1d4ed8;
}
</style>
