<script setup>
import { onMounted, ref } from 'vue'
import { sleepApi } from '@/api/sleep'

const loading = ref(false)
const rankData = ref([])
const myRank = ref(null)
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const res = await sleepApi.ranking()
    rankData.value = res.ranking
    myRank.value = res.my_rank
    total.value = res.total
  } catch (e) {
    // 未加入班级时 400
  } finally {
    loading.value = false
  }
}

function medalIcon(rank) {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return rank
}

function rowClass({ row }) {
  return row.is_me ? 'my-row' : ''
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <b>🏆 班级睡眠排行榜</b>
        <span class="sub-text">近 30 天平均质量分</span>
      </div>
    </template>

    <!-- 我的排名卡片 -->
    <el-alert
      v-if="myRank && !loading"
      :title="`你的排名：第 ${myRank.rank} 名 / 共 ${total} 人　平均质量分：${myRank.avg_quality}　打卡次数：${myRank.checked_count} 天`"
      type="success"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-table
      v-loading="loading"
      :data="rankData"
      :row-class-name="rowClass"
      stripe
    >
      <el-table-column label="名次" width="80" align="center">
        <template #default="{ row }">
          <span style="font-size: 18px">{{ medalIcon(row.rank) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="姓名" min-width="120">
        <template #default="{ row }">
          {{ row.name }}
          <el-tag v-if="row.is_me" size="small" type="primary" style="margin-left: 4px">我</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="平均质量分" width="130" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="row.avg_quality"
            :color="row.avg_quality >= 85 ? '#67c23a' : row.avg_quality >= 70 ? '#e6a23c' : '#f56c6c'"
            :stroke-width="8"
            style="width: 90px; display: inline-block"
          />
          <span style="margin-left: 6px; font-weight: 600">{{ row.avg_quality }}</span>
        </template>
      </el-table-column>

      <el-table-column label="打卡天数" width="100" align="center">
        <template #default="{ row }">
          {{ row.checked_count }} 天
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && rankData.length === 0" style="text-align:center; color:#c0c4cc; padding:40px 0">
      未加入班级或班级暂无数据 😴
    </div>

    <el-alert
      type="info"
      :closable="false"
      title="排行榜只显示你自己的真实姓名，其他同学均匿名显示"
      style="margin-top: 12px"
    />
  </el-card>
</template>

<style scoped>
.sub-text { font-size: 13px; color: #909399; }
:deep(.my-row) { background-color: #f0f9eb !important; font-weight: 600; }
</style>
