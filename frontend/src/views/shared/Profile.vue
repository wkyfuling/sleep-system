<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import request from '@/api/request'
import { authApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const saving = ref(false)
const generating = ref(false)
const creatingClass = ref(false)
const parentCode = ref(null)

const user = computed(() => userStore.user || {})
const profile = computed(() => user.value.profile || {})
const role = computed(() => user.value.role)

const form = reactive({
  email: '',
  phone: '',
  email_alert_enabled: false,
  share_diary_to_teacher: false,
})

const classroomForm = reactive({ name: '' })

watch(
  () => userStore.user,
  (u) => {
    form.email = u?.email || ''
    form.phone = u?.phone || ''
    form.email_alert_enabled = Boolean(u?.email_alert_enabled)
    form.share_diary_to_teacher = Boolean(u?.profile?.share_diary_to_teacher)
  },
  { immediate: true },
)

const roleLabel = computed(() => ({
  student: '学生',
  teacher: '老师',
  parent: '家长',
  admin: '管理员',
}[role.value] || '用户'))

const displayName = computed(() => profile.value.real_name || user.value.username || '用户')

const studentRows = computed(() => {
  if (role.value !== 'student') return []
  const p = profile.value
  return [
    ['真实姓名', p.real_name || '-'],
    ['学号', p.student_no || '-'],
    ['性别', { M: '男', F: '女', O: '其他' }[p.gender] || '-'],
    ['年级', p.grade || '-'],
    ['班级', p.classroom?.name || '未加入班级'],
    ['目标睡眠', `${p.target_sleep_hours || 8} 小时`],
    ['目标入睡', p.target_bedtime || '23:00'],
    ['风险状态', p.risk_level === 'focus' ? '重点关注' : '正常'],
  ]
})

const teacherRows = computed(() => {
  if (role.value !== 'teacher') return []
  const p = profile.value
  return [
    ['真实姓名', p.real_name || '-'],
    ['工号', p.teacher_no || '-'],
    ['管理班级数', `${p.classrooms?.length || 0} 个`],
  ]
})

const parentRows = computed(() => {
  if (role.value !== 'parent') return []
  const p = profile.value
  const child = p.child
  return [
    ['真实姓名', p.real_name || '-'],
    ['绑定孩子', child?.real_name || '未绑定'],
    ['孩子学号', child?.student_no || '-'],
    ['孩子班级', child?.classroom_name || child?.classroom || '-'],
  ]
})

async function saveProfile() {
  saving.value = true
  try {
    const payload = {
      email: form.email,
      phone: form.phone,
      email_alert_enabled: form.email_alert_enabled,
    }
    if (role.value === 'student') {
      payload.share_diary_to_teacher = form.share_diary_to_teacher
    }
    const res = await authApi.updatePreferences(payload)
    userStore.user = res.user
    localStorage.setItem('user', JSON.stringify(res.user))
    ElMessage.success('个人设置已保存')
  } finally {
    saving.value = false
  }
}

async function generateParentCode() {
  generating.value = true
  try {
    parentCode.value = await authApi.generateParentCode()
    ElMessage.success('家长邀请码已生成')
  } finally {
    generating.value = false
  }
}

async function createClassroom() {
  const name = classroomForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入班级名称')
    return
  }
  creatingClass.value = true
  try {
    await request.post('/teacher/classroom/', { name })
    classroomForm.name = ''
    await userStore.fetchMe()
    ElMessage.success('班级已创建')
  } finally {
    creatingClass.value = false
  }
}

function fmtTime(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}
</script>

<template>
  <div class="profile-page">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="never" class="identity-card">
          <el-avatar :size="72" class="avatar">{{ displayName[0] }}</el-avatar>
          <div class="name">{{ displayName }}</div>
          <el-tag size="small">{{ roleLabel }}</el-tag>
          <div class="username">@{{ user.username }}</div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="never">
          <template #header><b>账号设置</b></template>
          <el-form label-width="110px">
            <el-form-item label="邮箱">
              <el-input v-model="form.email" placeholder="用于可选邮件预警" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="选填" />
            </el-form-item>
            <el-form-item label="邮件预警">
              <el-switch
                v-model="form.email_alert_enabled"
                active-text="开启"
                inactive-text="关闭"
              />
            </el-form-item>
            <el-form-item v-if="role === 'student'" label="日记分享">
              <el-switch
                v-model="form.share_diary_to_teacher"
                active-text="允许老师查看"
                inactive-text="仅自己可见"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveProfile">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top:16px">
      <template #header><b>档案信息</b></template>

      <el-descriptions v-if="role === 'student'" :column="3" border>
        <el-descriptions-item v-for="[label, value] in studentRows" :key="label" :label="label">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>

      <el-descriptions v-else-if="role === 'teacher'" :column="3" border>
        <el-descriptions-item v-for="[label, value] in teacherRows" :key="label" :label="label">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>

      <el-descriptions v-else-if="role === 'parent'" :column="2" border>
        <el-descriptions-item v-for="[label, value] in parentRows" :key="label" :label="label">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="role === 'student'" shadow="never" style="margin-top:16px">
      <template #header><b>家长绑定邀请码</b></template>
      <div class="action-row">
        <div>
          <div class="action-title">生成 24 小时有效的邀请码</div>
          <div class="action-sub">家长注册时输入该邀请码，即可绑定当前学生。</div>
        </div>
        <el-button type="primary" :loading="generating" @click="generateParentCode">
          生成邀请码
        </el-button>
      </div>
      <el-alert
        v-if="parentCode"
        type="success"
        :closable="false"
        style="margin-top:12px"
      >
        <template #title>
          邀请码：<b class="code">{{ parentCode.code }}</b>
          ，有效期至 {{ fmtTime(parentCode.expires_at) }}
        </template>
      </el-alert>
    </el-card>

    <el-card v-if="role === 'teacher'" shadow="never" style="margin-top:16px">
      <template #header><b>我的班级</b></template>

      <el-table :data="profile.classrooms || []" stripe style="margin-bottom: 14px">
        <el-table-column prop="name" label="班级名称" />
        <el-table-column prop="invite_code" label="班级邀请码" width="160">
          <template #default="{ row }">
            <el-tag>{{ row.invite_code }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="create-class">
        <el-input v-model="classroomForm.name" placeholder="新班级名称，如 高三(5)班" />
        <el-button type="primary" :loading="creatingClass" @click="createClassroom">
          创建班级
        </el-button>
      </div>
    </el-card>

    <el-card v-if="role === 'parent'" shadow="never" style="margin-top:16px">
      <template #header><b>孩子绑定说明</b></template>
      <el-alert
        type="info"
        :closable="false"
        title="家长账号通过学生生成的邀请码绑定孩子。若当前孩子信息有误，请让孩子重新生成邀请码后注册新的家长账号。"
      />
    </el-card>
  </div>
</template>

<style scoped>
.profile-page { max-width: 1120px; }
.identity-card { text-align: center; min-height: 230px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.avatar { background: #667eea; font-size: 28px; margin-bottom: 12px; }
.name { font-size: 20px; font-weight: 700; color: #303133; margin-bottom: 8px; }
.username { color: #909399; font-size: 13px; margin-top: 8px; }
.action-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.action-title { font-weight: 600; color: #303133; margin-bottom: 4px; }
.action-sub { color: #909399; font-size: 13px; }
.code { letter-spacing: 2px; font-size: 18px; color: #409eff; }
.create-class { display: flex; gap: 10px; max-width: 520px; }
</style>
