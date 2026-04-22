<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const stats = ref(null)
const loading = ref(false)
const seeding = ref(false)

async function loadStats() {
  loading.value = true
  try {
    stats.value = await request.get('/auth/admin/global-stats/')
  } finally {
    loading.value = false
  }
}

const statCards = [
  { icon: '👥', key: 'total_users', label: '总用户数' },
  { icon: '🎓', key: 'student_count', label: '学生数' },
  { icon: '👨‍🏫', key: 'teacher_count', label: '老师数' },
  { icon: '🏫', key: 'classroom_count', label: '班级数' },
  { icon: '✅', key: 'today_checkins', label: '今日打卡' },
  { icon: '⚠️', key: 'severe_today', label: '今日严重异常' },
]

async function seedDemo() {
  try {
    await ElMessageBox.confirm(
      '将向数据库生成 1 名老师 + 30 名学生 + 30 名家长 + 365 天记录。已有数据不会删除，确认继续？',
      '一键生成演示数据',
      { confirmButtonText: '生成', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  seeding.value = true
  try {
    await request.post('/auth/admin/seed-demo/', {}, { timeout: 120000 })
    ElMessage.success('演示数据生成成功！')
    loadStats()
  } catch (e) {
    const msg = e?.code === 'ECONNABORTED'
      ? '生成时间较长，请稍后刷新查看数据'
      : (e?.response?.data?.error || e?.response?.data?.detail || '未知错误')
    ElMessage.error('生成失败: ' + msg)
  } finally {
    seeding.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <h1>系统运营总览</h1>
        <p>查看全局用户、班级、今日打卡和严重异常数据，并快速进入演示数据与内容管理。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" size="large" :loading="seeding" @click="seedDemo">生成演示数据</el-button>
        <el-button size="large" @click="$router.push('/admin/users')">用户管理</el-button>
      </div>
    </section>

    <!-- 统计卡片 -->
    <el-row :gutter="16" v-loading="loading">
      <el-col :span="4" v-for="item in statCards" :key="item.label">
        <el-card shadow="never" class="stat-card panel">
          <div class="stat-icon">{{ item.icon }}</div>
          <div class="stat-value">{{ stats ? stats[item.key] : '—' }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作区 -->
    <el-card shadow="never" class="panel">
      <template #header><b>⚙️ 系统管理</b></template>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-button
            type="primary"
            size="large"
            :loading="seeding"
            @click="seedDemo"
            style="width: 100%"
          >
            🌱 一键生成演示数据
          </el-button>
          <div class="btn-desc">生成 30 名学生 + 365 天睡眠历史（含 3 个典型案例）</div>
        </el-col>
        <el-col :span="8">
          <el-button size="large" @click="$router.push('/admin/users')" style="width: 100%">
            👥 用户管理
          </el-button>
          <div class="btn-desc">查看所有用户，可按角色筛选</div>
        </el-col>
        <el-col :span="8">
          <el-button size="large" @click="$router.push('/admin/articles')" style="width: 100%">
            📰 科普文章管理
          </el-button>
          <div class="btn-desc">发布、编辑睡眠科普文章</div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>


<style scoped>
.stat-card { text-align: center; padding: 8px; }
.stat-icon { font-size: 28px; margin-bottom: 4px; }
.stat-value { font-size: 28px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
.btn-desc { font-size: 12px; color: #909399; margin-top: 6px; text-align: center; }
</style>
