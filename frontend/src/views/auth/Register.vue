<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const activeRole = ref('student')

const forms = reactive({
  student: {
    username: '', password: '', email: '', phone: '',
    student_no: '', real_name: '', gender: 'M', grade: '',
    classroom_invite_code: '',
  },
  teacher: {
    username: '', password: '', email: '', phone: '',
    teacher_no: '', real_name: '', classroom_name: '',
  },
  parent: {
    username: '', password: '', email: '', phone: '',
    real_name: '', parent_invite_code: '',
  },
})

const rules = {
  username: [{ required: true, min: 3, message: '用户名至少 3 位', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  teacher_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  classroom_invite_code: [{ required: true, message: '请输入班级邀请码', trigger: 'blur' }],
  parent_invite_code: [{ required: true, message: '请输入家长邀请码', trigger: 'blur' }],
}

const formRefs = { student: ref(null), teacher: ref(null), parent: ref(null) }
const currentFormRef = computed(() => formRefs[activeRole.value])

const roleHome = { student: '/student', teacher: '/teacher', parent: '/parent', admin: '/admin' }

async function handleRegister() {
  const ref_ = currentFormRef.value.value
  const ok = await ref_?.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    const payload = { role: activeRole.value, ...forms[activeRole.value] }
    // 邀请码统一转大写
    if (payload.classroom_invite_code) payload.classroom_invite_code = payload.classroom_invite_code.toUpperCase()
    if (payload.parent_invite_code) payload.parent_invite_code = payload.parent_invite_code.toUpperCase()
    await userStore.register(payload)
    ElMessage.success('注册成功，已自动登录')
    router.push(roleHome[userStore.role] || '/')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="card">
      <div class="header">
        <div class="logo">🌙</div>
        <h1>注册账号</h1>
        <p class="subtitle">选择你的身份</p>
      </div>

      <el-tabs v-model="activeRole" class="role-tabs">
        <el-tab-pane label="👨‍🎓 学生" name="student">
          <el-form :ref="formRefs.student" :model="forms.student" :rules="rules" label-position="top">
            <el-form-item label="用户名" prop="username"><el-input v-model="forms.student.username" /></el-form-item>
            <el-form-item label="密码" prop="password"><el-input v-model="forms.student.password" type="password" show-password /></el-form-item>
            <div class="row">
              <el-form-item label="学号" prop="student_no" style="flex:1"><el-input v-model="forms.student.student_no" /></el-form-item>
              <el-form-item label="姓名" prop="real_name" style="flex:1"><el-input v-model="forms.student.real_name" /></el-form-item>
            </div>
            <div class="row">
              <el-form-item label="性别" style="flex:1">
                <el-select v-model="forms.student.gender">
                  <el-option label="男" value="M" />
                  <el-option label="女" value="F" />
                  <el-option label="其他" value="O" />
                </el-select>
              </el-form-item>
              <el-form-item label="年级" style="flex:1"><el-input v-model="forms.student.grade" placeholder="如 高三" /></el-form-item>
            </div>
            <el-form-item label="班级邀请码" prop="classroom_invite_code">
              <el-input
                v-model="forms.student.classroom_invite_code"
                placeholder="6 位字母数字，向班主任索要"
                style="text-transform: uppercase"
                maxlength="8"
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="👨‍🏫 老师" name="teacher">
          <el-form :ref="formRefs.teacher" :model="forms.teacher" :rules="rules" label-position="top">
            <el-form-item label="用户名" prop="username"><el-input v-model="forms.teacher.username" /></el-form-item>
            <el-form-item label="密码" prop="password"><el-input v-model="forms.teacher.password" type="password" show-password /></el-form-item>
            <div class="row">
              <el-form-item label="工号" prop="teacher_no" style="flex:1"><el-input v-model="forms.teacher.teacher_no" /></el-form-item>
              <el-form-item label="姓名" prop="real_name" style="flex:1"><el-input v-model="forms.teacher.real_name" /></el-form-item>
            </div>
            <el-form-item label="班级名称（可选）">
              <el-input v-model="forms.teacher.classroom_name" placeholder="填写后自动创建班级并生成邀请码" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="👨‍👩‍👧 家长" name="parent">
          <el-form :ref="formRefs.parent" :model="forms.parent" :rules="rules" label-position="top">
            <el-form-item label="用户名" prop="username"><el-input v-model="forms.parent.username" /></el-form-item>
            <el-form-item label="密码" prop="password"><el-input v-model="forms.parent.password" type="password" show-password /></el-form-item>
            <el-form-item label="姓名" prop="real_name"><el-input v-model="forms.parent.real_name" /></el-form-item>
            <el-form-item label="家长邀请码" prop="parent_invite_code">
              <el-input
                v-model="forms.parent.parent_invite_code"
                placeholder="6 位字母数字，向孩子索要"
                style="text-transform: uppercase"
                maxlength="8"
              />
            </el-form-item>
            <div class="tip">💡 孩子在登录后可到个人中心生成 24 小时有效的家长邀请码</div>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-button
        type="primary"
        size="large"
        :loading="loading"
        style="width:100%; margin-top: 12px"
        @click="handleRegister"
      >注 册</el-button>

      <div class="footer">
        已有账号？
        <el-link type="primary" @click="router.push('/login')">去登录</el-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 100vh;
  background: var(--brand-gradient);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.card {
  background: #fff;
  border-radius: 16px;
  padding: 36px 40px;
  max-width: 520px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.header { text-align: center; margin-bottom: 12px; }
.logo { font-size: 40px; margin-bottom: 4px; }
h1 { margin: 0 0 4px; font-size: 22px; }
.subtitle { margin: 0; color: #909399; font-size: 14px; }
.role-tabs :deep(.el-tabs__item) { font-size: 15px; }
.row { display: flex; gap: 12px; }
.row .el-form-item { margin-bottom: 18px; }
.tip { color: #909399; font-size: 12px; background: #f5f7fa; padding: 8px 12px; border-radius: 6px; margin-top: -4px; }
.footer { text-align: center; margin-top: 16px; font-size: 14px; color: #909399; }
</style>
