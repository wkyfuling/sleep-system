<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/api/request'

const router = useRouter()
const backendStatus = ref({ state: 'checking', detail: '' })

async function ping() {
  backendStatus.value = { state: 'checking', detail: '正在连接后端...' }
  try {
    const data = await request.get('/healthz/')
    backendStatus.value = { state: 'ok', detail: JSON.stringify(data) }
  } catch (e) {
    backendStatus.value = { state: 'error', detail: e.message }
  }
}

onMounted(ping)
</script>

<template>
  <div class="welcome">
    <div class="card">
      <div class="logo">🌙</div>
      <h1>学生睡眠管理系统</h1>
      <p class="subtitle">学生自管 · 老师监督 · 家长关注</p>

      <div class="status" :class="backendStatus.state">
        <el-icon v-if="backendStatus.state === 'ok'"><CircleCheckFilled /></el-icon>
        <el-icon v-else-if="backendStatus.state === 'error'"><CircleCloseFilled /></el-icon>
        <el-icon v-else class="rotating"><Loading /></el-icon>
        <span v-if="backendStatus.state === 'ok'">后端连接正常</span>
        <span v-else-if="backendStatus.state === 'error'">后端未连接：{{ backendStatus.detail }}</span>
        <span v-else>{{ backendStatus.detail }}</span>
      </div>

      <div class="actions">
        <el-button type="primary" size="large" @click="router.push('/login')">进入系统</el-button>
        <el-button size="large" @click="ping">重新检测</el-button>
      </div>

      <div class="footer">M1 脚手架 · 后续里程碑：数据模型 → 认证 → 打卡 → 统计 → 通知 → AI → 报表</div>
    </div>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-gradient);
  padding: 20px;
}
.card {
  background: #fff;
  border-radius: 16px;
  padding: 48px 56px;
  max-width: 520px;
  width: 100%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
.logo { font-size: 56px; margin-bottom: 12px; }
h1 { margin: 0 0 8px; font-size: 26px; color: #303133; }
.subtitle { color: #909399; margin: 0 0 32px; }
.status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 24px;
}
.status.ok { background: #f0f9eb; color: #67c23a; }
.status.error { background: #fef0f0; color: #f56c6c; }
.status.checking { background: #f4f4f5; color: #909399; }
.rotating { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.actions { display: flex; gap: 12px; justify-content: center; margin-bottom: 24px; }
.footer { color: #c0c4cc; font-size: 12px; line-height: 1.6; }
</style>
