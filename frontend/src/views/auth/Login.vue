<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const roleHome = {
  student: '/student',
  teacher: '/teacher',
  parent: '/parent',
  admin: '/admin',
}

async function handleLogin() {
  const ok = await formRef.value?.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    await userStore.login(form)
    ElMessage.success(`欢迎回来，${userStore.user.username}`)
    const target = roleHome[userStore.role] || '/'
    router.push(target)
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
        <h1>学生睡眠管理系统</h1>
        <p class="subtitle">登录进入你的账号</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="'User'"
            autofocus
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            placeholder="请输入密码"
            type="password"
            size="large"
            :prefix-icon="'Lock'"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width:100%"
          @click="handleLogin"
        >
          登 录
        </el-button>
      </el-form>

      <div class="footer">
        还没有账号？
        <el-link type="primary" @click="router.push('/register')">立即注册</el-link>
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
  padding: 44px 48px;
  max-width: 440px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.header { text-align: center; margin-bottom: 28px; }
.logo { font-size: 48px; margin-bottom: 8px; }
h1 { margin: 0 0 6px; font-size: 22px; color: #303133; }
.subtitle { margin: 0; color: #909399; font-size: 14px; }
.footer { text-align: center; margin-top: 20px; font-size: 14px; color: #909399; }
</style>
