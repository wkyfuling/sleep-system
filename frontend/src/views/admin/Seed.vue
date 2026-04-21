<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const seeding = ref(false)
const result = ref(null)

const logLines = computed(() => {
  if (!result.value?.log) return []
  return result.value.log.split('\n').filter(Boolean)
})

async function seedDemo() {
  try {
    await ElMessageBox.confirm(
      '将生成 1 名老师、30 名学生、30 名家长、365 天睡眠记录、10 篇科普文章。已有数据不会删除，确认继续？',
      '生成演示数据',
      { confirmButtonText: '生成', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  seeding.value = true
  try {
    result.value = await request.post('/auth/admin/seed-demo/')
    ElMessage.success('演示数据生成完成')
  } finally {
    seeding.value = false
  }
}
</script>

<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <h1>演示数据中心</h1>
        <p>一键生成比赛演示所需的班级、账号、睡眠记录、典型案例和科普文章。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" size="large" :loading="seeding" @click="seedDemo">
          生成演示数据
        </el-button>
      </div>
    </section>

    <div class="metric-grid">
      <div class="metric-tile">
        <div class="metric-title">老师账号</div>
        <div class="metric-main">1</div>
        <div class="metric-foot">teacher01 / teacher123</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">学生账号</div>
        <div class="metric-main">30</div>
        <div class="metric-foot">student01-30 / student123</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">家长账号</div>
        <div class="metric-main">30</div>
        <div class="metric-foot">parent01-30 / parent123</div>
      </div>
      <div class="metric-tile">
        <div class="metric-title">典型案例</div>
        <div class="metric-main">3</div>
        <div class="metric-foot">严重熬夜、完美作息、周期异常</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-card shadow="never" class="panel">
          <template #header><b>演示账号</b></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="管理员">admin / admin123</el-descriptions-item>
            <el-descriptions-item label="老师">teacher01 / teacher123</el-descriptions-item>
            <el-descriptions-item label="学生">student01 至 student30 / student123</el-descriptions-item>
            <el-descriptions-item label="家长">parent01 至 parent30 / parent123</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card shadow="never" class="panel">
          <template #header><b>种子内容</b></template>
          <el-timeline>
            <el-timeline-item color="#409eff" timestamp="班级结构">高三(1)班，默认 30 名学生</el-timeline-item>
            <el-timeline-item color="#67c23a" timestamp="健康案例">student02 长期健康作息</el-timeline-item>
            <el-timeline-item color="#f56c6c" timestamp="预警案例">student01 长期严重熬夜</el-timeline-item>
            <el-timeline-item color="#e6a23c" timestamp="周期案例">student03 正常与异常周期交替</el-timeline-item>
            <el-timeline-item color="#909399" timestamp="科普内容">预置 10 篇睡眠健康文章</el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="result" shadow="never" class="panel">
      <template #header><b>生成日志</b></template>
      <pre class="log-box">{{ logLines.join('\n') }}</pre>
    </el-card>
  </div>
</template>

<style scoped>
.log-box {
  margin: 0;
  max-height: 320px;
  overflow: auto;
  padding: 14px;
  border-radius: 8px;
  background: #111827;
  color: #d1d5db;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>
