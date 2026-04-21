<script setup>
import { computed, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { sleepApi } from '@/api/sleep'
import { authApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 表单默认：昨晚 23:00 入睡 / 今晨 07:00 起床
function defaultBedtime() {
  return dayjs().subtract(1, 'day').hour(23).minute(0).second(0).millisecond(0).toDate()
}
function defaultWake() {
  return dayjs().hour(7).minute(0).second(0).millisecond(0).toDate()
}

const form = reactive({
  backfill_days: 1,
  bedtime: defaultBedtime(),
  wake_time: defaultWake(),
  subjective_score: 3,
  mood_tag: 'good',
  diary: '',
  share_diary_to_teacher: Boolean(userStore.user?.profile?.share_diary_to_teacher),
})

const submitting = ref(false)
const result = ref(null)

const durationText = computed(() => {
  if (!form.bedtime || !form.wake_time) return ''
  const mins = dayjs(form.wake_time).diff(dayjs(form.bedtime), 'minute')
  if (mins <= 0) return '⚠ 起床时间必须晚于入睡时间'
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h}h ${m}min`
})

const statusMap = {
  normal: { label: '健康', color: '#67c23a', emoji: '😊' },
  warning: { label: '一般', color: '#e6a23c', emoji: '😐' },
  abnormal: { label: '异常', color: '#f56c6c', emoji: '😟' },
  severe: { label: '严重', color: '#c45656', emoji: '😫' },
}

const moodOptions = [
  { value: 'great', label: '😄 极佳' },
  { value: 'good', label: '🙂 良好' },
  { value: 'normal', label: '😐 一般' },
  { value: 'tired', label: '😪 疲惫' },
  { value: 'bad', label: '😣 糟糕' },
]

const backfillOptions = [
  { value: 1, label: '昨晚' },
  { value: 2, label: '前晚' },
  { value: 3, label: '大前晚' },
]

function applyBackfill(daysAgo) {
  const sleepDay = dayjs().subtract(daysAgo, 'day').hour(23).minute(0).second(0).millisecond(0)
  const wakeDay = dayjs().subtract(daysAgo - 1, 'day').hour(7).minute(0).second(0).millisecond(0)
  form.bedtime = sleepDay.toDate()
  form.wake_time = wakeDay.toDate()
}

async function submit() {
  if (dayjs(form.wake_time).diff(dayjs(form.bedtime), 'minute') <= 0) {
    ElMessage.error('起床时间必须晚于入睡时间')
    return
  }
  submitting.value = true
  try {
    const payload = {
      bedtime: dayjs(form.bedtime).format('YYYY-MM-DDTHH:mm:ss'),
      wake_time: dayjs(form.wake_time).format('YYYY-MM-DDTHH:mm:ss'),
      subjective_score: form.subjective_score,
      mood_tag: form.mood_tag,
      diary: form.diary,
    }
    const data = await sleepApi.createRecord(payload)
    if (form.share_diary_to_teacher !== Boolean(userStore.user?.profile?.share_diary_to_teacher)) {
      const pref = await authApi.updatePreferences({
        share_diary_to_teacher: form.share_diary_to_teacher,
      })
      userStore.user = pref.user
      localStorage.setItem('user', JSON.stringify(pref.user))
    }
    result.value = data
    ElMessage.success('打卡成功！')
  } catch (e) {
    // request.js 已弹错误消息
  } finally {
    submitting.value = false
  }
}

function reset() {
  form.backfill_days = 1
  form.bedtime = defaultBedtime()
  form.wake_time = defaultWake()
  form.subjective_score = 3
  form.mood_tag = 'good'
  form.diary = ''
  form.share_diary_to_teacher = Boolean(userStore.user?.profile?.share_diary_to_teacher)
  result.value = null
}
</script>

<template>
  <div class="checkin-wrap">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>🌙 今日打卡</b>
          <span class="hint">起床后回顾填写昨晚数据，数据最准确。支持补打最近 3 天。</span>
        </div>
      </template>

      <el-form :model="form" label-width="110px" @submit.prevent="submit">
        <el-form-item label="打卡日期">
          <el-select
            v-model="form.backfill_days"
            style="width: 180px"
            @change="applyBackfill"
          >
            <el-option v-for="item in backfillOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <span class="hint-inline">可补打最近 3 天</span>
        </el-form-item>

        <el-form-item label="昨晚入睡时间">
          <el-date-picker
            v-model="form.bedtime"
            type="datetime"
            placeholder="选择入睡时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :disabled-date="(d) => d > new Date()"
            style="width: 260px"
          />
        </el-form-item>

        <el-form-item label="今晨起床时间">
          <el-date-picker
            v-model="form.wake_time"
            type="datetime"
            placeholder="选择起床时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :disabled-date="(d) => d > new Date()"
            style="width: 260px"
          />
          <span class="duration">睡眠时长：{{ durationText }}</span>
        </el-form-item>

        <el-form-item label="主观感受">
          <el-rate v-model="form.subjective_score" :max="5" show-text />
        </el-form-item>

        <el-form-item label="心情">
          <el-radio-group v-model="form.mood_tag">
            <el-radio-button v-for="m in moodOptions" :key="m.value" :value="m.value">
              {{ m.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="睡眠日记">
          <el-input
            v-model="form.diary"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="记一下今天的感受吧（日记对老师/家长默认不可见）"
          />
        </el-form-item>

        <el-form-item label="隐私设置">
          <el-switch
            v-model="form.share_diary_to_teacher"
            active-text="分享日记给老师"
            inactive-text="仅自己可见"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">提交打卡</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="result" shadow="never" style="margin-top: 16px" class="result-card">
      <template #header>
        <b>📊 本次睡眠评估</b>
      </template>
      <div class="result-row">
        <div class="score-circle" :style="{ borderColor: statusMap[result.status]?.color }">
          <div class="score-number">{{ result.quality_score }}</div>
          <div class="score-sub">/100</div>
        </div>
        <div class="result-meta">
          <div class="meta-item">
            <span class="meta-label">归属日期</span>
            <span class="meta-value">{{ result.date }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">睡眠时长</span>
            <span class="meta-value">
              {{ Math.floor(result.duration_minutes / 60) }}h
              {{ result.duration_minutes % 60 }}min
            </span>
          </div>
          <div class="meta-item">
            <span class="meta-label">状态</span>
            <el-tag
              effect="dark"
              :color="statusMap[result.status]?.color"
              style="border: none"
            >
              {{ statusMap[result.status]?.emoji }} {{ statusMap[result.status]?.label }}
            </el-tag>
          </div>
        </div>
      </div>
      <el-alert
        v-if="result.status === 'severe' || result.status === 'abnormal'"
        :title="result.status === 'severe' ? '睡眠状况需要重视，建议今晚早点休息' : '睡眠质量有提升空间'"
        :type="result.status === 'severe' ? 'error' : 'warning'"
        show-icon
        :closable="false"
        style="margin-top: 14px"
      />
    </el-card>
  </div>
</template>

<style scoped>
.checkin-wrap { max-width: 760px; margin: 0 auto; }
.card-header { display: flex; align-items: center; gap: 12px; }
.hint { color: #909399; font-size: 12px; font-weight: normal; }
.hint-inline { margin-left: 12px; color: #909399; font-size: 12px; }
.duration { margin-left: 16px; color: #409eff; font-weight: 500; }
.result-card { background: linear-gradient(135deg, #fafbfc, #f0f7ff); }
.result-row { display: flex; align-items: center; gap: 32px; padding: 8px 0; }
.score-circle {
  width: 120px; height: 120px; border-radius: 50%;
  border: 6px solid #67c23a;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: #fff; box-shadow: 0 4px 12px rgba(0,0,0,.06);
}
.score-number { font-size: 36px; font-weight: 700; color: #303133; }
.score-sub { font-size: 13px; color: #909399; }
.result-meta { display: flex; flex-direction: column; gap: 12px; }
.meta-item { display: flex; align-items: center; gap: 12px; }
.meta-label { width: 72px; color: #909399; font-size: 13px; }
.meta-value { color: #303133; font-weight: 500; }
</style>
