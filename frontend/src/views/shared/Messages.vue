<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { notificationApi } from '@/api/notification'
import { useNotificationStore } from '@/stores/notification'
import { useUserStore } from '@/stores/user'

const notifStore = useNotificationStore()
const userStore = useUserStore()
const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const recipients = ref([])
const sending = ref(false)
const composeVisible = ref(false)

const form = reactive({
  receiver_id: null,
  title: '',
  content: '',
})

const typeMap = {
  system_alert: { label: '系统预警', type: 'danger' },
  teacher_msg:  { label: '老师留言', type: 'primary' },
  parent_msg:   { label: '家长留言', type: 'success' },
  student_msg:  { label: '学生留言', type: '' },
  announcement: { label: '班级公告', type: 'warning' },
}

const messageType = computed(() => {
  if (userStore.role === 'teacher') return 'teacher_msg'
  if (userStore.role === 'parent') return 'parent_msg'
  if (userStore.role === 'student') return 'student_msg'
  return 'system_alert'
})

async function load() {
  loading.value = true
  try {
    const res = await notificationApi.list({ page: page.value })
    items.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

async function loadRecipients() {
  const res = await notificationApi.recipients()
  recipients.value = res.results || []
}

async function handleRead(item) {
  if (item.is_read) return
  await notificationApi.markRead(item.id)
  item.is_read = true
  notifStore.decrement()
}

async function handleReadAll() {
  await notificationApi.markAllRead()
  items.value.forEach(i => { i.is_read = true })
  notifStore.reset()
  ElMessage.success('已全部标为已读')
}

function openCompose() {
  if (!recipients.value.length) {
    loadRecipients()
  }
  composeVisible.value = true
}

async function sendMessage() {
  if (!form.receiver_id || !form.title.trim() || !form.content.trim()) {
    ElMessage.warning('请选择收件人并填写标题、内容')
    return
  }
  sending.value = true
  try {
    await notificationApi.send({
      receiver_id: form.receiver_id,
      title: form.title.trim(),
      content: form.content.trim(),
      type: messageType.value,
    })
    ElMessage.success('消息已发送')
    composeVisible.value = false
    form.receiver_id = null
    form.title = ''
    form.content = ''
  } finally {
    sending.value = false
  }
}

function fmtTime(iso) {
  return dayjs(iso).format('MM-DD HH:mm')
}

onMounted(() => {
  load()
  loadRecipients()
})
</script>

<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <h1>消息中心</h1>
        <p>用于老师、学生、家长之间的合规沟通；学生之间、家长之间不开放私信。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="openCompose">写消息</el-button>
        <el-button size="large" @click="handleReadAll">全部已读</el-button>
      </div>
    </section>

    <el-card shadow="never" class="panel">
      <template #header>
        <div class="toolbar-line">
          <b>收件箱</b>
          <div class="toolbar-actions">
            <el-button size="small" @click="load">刷新</el-button>
            <el-button size="small" @click="handleReadAll">全部已读</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="items" stripe @row-click="handleRead">
        <el-table-column width="36">
          <template #default="{ row }">
            <span v-if="!row.is_read" class="unread-dot" />
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="typeMap[row.type]?.type" size="small">
              {{ typeMap[row.type]?.label || row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="180">
          <template #default="{ row }">
            <span :class="row.is_read ? 'read' : 'unread'">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="发件人" width="110">
          <template #default="{ row }">{{ row.sender_name || '系统' }}</template>
        </el-table-column>
        <el-table-column label="时间" width="120">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="内容" min-width="260">
          <template #default="{ row }">
            <el-tooltip :content="row.content" placement="top">
              <span class="content-preview">
                {{ row.content.length > 52 ? row.content.slice(0, 52) + '…' : row.content }}
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !items.length" description="暂无消息" />

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="load"
      />
    </el-card>

    <el-dialog v-model="composeVisible" title="发送消息" width="560px">
      <el-form label-width="88px">
        <el-form-item label="收件人">
          <el-select v-model="form.receiver_id" filterable placeholder="选择可联系对象" style="width:100%">
            <el-option
              v-for="r in recipients"
              :key="r.id"
              :label="`${r.name}（${r.relation}）`"
              :value="r.id"
            >
              <span>{{ r.name }}</span>
              <span class="recipient-meta">{{ r.role_display }} · {{ r.relation }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="6" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="composeVisible = false">取消</el-button>
        <el-button type="primary" :loading="sending" @click="sendMessage">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.unread { font-weight: 600; color: #303133; }
.read { color: #909399; }
.content-preview { color: #606266; cursor: default; }
:deep(.el-table__row) { cursor: pointer; }
.unread-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
}
.recipient-meta {
  float: right;
  color: #909399;
  font-size: 12px;
}
</style>
