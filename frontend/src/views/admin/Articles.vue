<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import request from '@/api/request'

const loading = ref(false)
const articles = ref([])
const total = ref(0)
const page = ref(1)

const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({ title: '', content: '' })
const editId = ref(null)

async function load() {
  loading.value = true
  try {
    const res = await request.get('/articles/', { params: { page: page.value } })
    articles.value = res.results || res
    total.value = res.count || articles.value.length
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editId.value = null
  form.title = ''
  form.content = ''
  dialogVisible.value = true
}

function openEdit(row) {
  editId.value = row.id
  form.title = row.title
  form.content = row.content
  dialogVisible.value = true
}

async function submit() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  submitting.value = true
  try {
    if (editId.value) {
      await request.patch(`/articles/${editId.value}/`, form)
      ElMessage.success('已更新')
    } else {
      await request.post('/articles/', form)
      ElMessage.success('已发布')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function removeArticle(row) {
  try {
    await ElMessageBox.confirm(`确认删除文章《${row.title}》？`, '删除文章', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await request.delete(`/articles/${row.id}/`)
  ElMessage.success('文章已删除')
  load()
}

function fmtDate(iso) {
  return dayjs(iso).format('YYYY-MM-DD')
}

onMounted(load)
</script>

<template>
  <div class="page-shell">
  <section class="page-hero">
    <div>
      <h1>睡眠科普内容库</h1>
      <p>维护面向学生和家长的睡眠健康文章，作为系统 AI 建议之外的知识补充。</p>
    </div>
    <div class="hero-actions">
      <el-button type="primary" size="large" @click="openCreate">发布文章</el-button>
    </div>
  </section>

  <el-card shadow="never" class="panel">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <b>📰 科普文章管理</b>
        <el-button type="primary" size="small" @click="openCreate">＋ 发布文章</el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="articles" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="author_name" label="作者" width="100" />
      <el-table-column prop="views" label="阅读量" width="90" align="center" />
      <el-table-column label="发布时间" width="120">
        <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="removeArticle(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editId ? '编辑文章' : '发布文章'" width="680px">
    <el-form label-width="80px">
      <el-form-item label="标题">
        <el-input v-model="form.title" maxlength="128" show-word-limit />
      </el-form-item>
      <el-form-item label="正文">
        <el-input v-model="form.content" type="textarea" :rows="12" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ editId ? '保存' : '发布' }}
      </el-button>
    </template>
  </el-dialog>
  </div>
</template>
