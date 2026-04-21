<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { sleepApi } from '@/api/sleep'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filter = reactive({
  range: [dayjs().subtract(30, 'day').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')],
})

const statusMap = {
  normal: { label: '健康', type: 'success' },
  warning: { label: '一般', type: 'warning' },
  abnormal: { label: '异常', type: 'danger' },
  severe: { label: '严重', type: 'danger' },
  missed: { label: '未打卡', type: 'info' },
}

const moodLabel = {
  great: '😄 极佳', good: '🙂 良好', normal: '😐 一般',
  tired: '😪 疲惫', bad: '😣 糟糕', '': '—',
}

async function load() {
  loading.value = true
  try {
    const params = {
      from: filter.range?.[0],
      to: filter.range?.[1],
      page: page.value,
    }
    const data = await sleepApi.listRecords(params)
    rows.value = data.results || data
    total.value = data.count ?? rows.value.length
  } finally {
    loading.value = false
  }
}

function fmtTime(iso) {
  if (!iso) return '—'
  return dayjs(iso).format('MM-DD HH:mm')
}

function fmtDuration(mins) {
  if (!mins) return '—'
  return `${Math.floor(mins / 60)}h ${mins % 60}min`
}

// —— 2h 内编辑弹窗 ——
const editVisible = ref(false)
const editing = reactive({
  id: null,
  subjective_score: 3,
  mood_tag: '',
  diary: '',
})

function openEdit(row) {
  editing.id = row.id
  editing.subjective_score = row.subjective_score
  editing.mood_tag = row.mood_tag || ''
  editing.diary = row.diary || ''
  editVisible.value = true
}

async function submitEdit() {
  try {
    await sleepApi.updateRecord(editing.id, {
      subjective_score: editing.subjective_score,
      mood_tag: editing.mood_tag,
      diary: editing.diary,
    })
    ElMessage.success('已更新')
    editVisible.value = false
    load()
  } catch (e) { /* already toasted */ }
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <b>📚 我的睡眠历史</b>
        <div class="filters">
          <el-date-picker
            v-model="filter.range"
            type="daterange"
            value-format="YYYY-MM-DD"
            unlink-panels
            range-separator="→"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 260px"
            @change="() => { page = 1; load() }"
          />
          <el-button @click="() => { page = 1; load() }">查询</el-button>
        </div>
      </div>
    </template>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="date" label="日期" width="110" />
      <el-table-column label="入睡" width="110">
        <template #default="{ row }">{{ fmtTime(row.bedtime) }}</template>
      </el-table-column>
      <el-table-column label="起床" width="110">
        <template #default="{ row }">{{ fmtTime(row.wake_time) }}</template>
      </el-table-column>
      <el-table-column label="时长" width="100">
        <template #default="{ row }">{{ fmtDuration(row.duration_minutes) }}</template>
      </el-table-column>
      <el-table-column prop="subjective_score" label="主观" width="80">
        <template #default="{ row }">
          <span v-if="row.subjective_score">{{ '★'.repeat(row.subjective_score) }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="quality_score" label="质量分" width="80" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type || 'info'">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="心情" width="100">
        <template #default="{ row }">{{ moodLabel[row.mood_tag] }}</template>
      </el-table-column>
      <el-table-column label="日记" min-width="160">
        <template #default="{ row }">
          <el-tooltip v-if="row.diary" :content="row.diary" placement="top">
            <span class="diary">{{ row.diary.length > 16 ? row.diary.slice(0, 16) + '…' : row.diary }}</span>
          </el-tooltip>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.editable"
            size="small"
            type="primary"
            link
            @click="openEdit(row)"
          >
            编辑
          </el-button>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
    </el-table>

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

  <el-dialog v-model="editVisible" title="编辑打卡记录（2h 内生效）" width="480px">
    <el-form label-width="90px">
      <el-form-item label="主观评分">
        <el-rate v-model="editing.subjective_score" :max="5" show-text />
      </el-form-item>
      <el-form-item label="心情">
        <el-select v-model="editing.mood_tag" style="width: 180px">
          <el-option v-for="(v, k) in moodLabel" :key="k" :label="v" :value="k" />
        </el-select>
      </el-form-item>
      <el-form-item label="日记">
        <el-input v-model="editing.diary" type="textarea" :rows="3" maxlength="500" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">取消</el-button>
      <el-button type="primary" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; }
.filters { display: flex; gap: 8px; }
.muted { color: #c0c4cc; }
.diary { color: #606266; cursor: pointer; }
</style>
