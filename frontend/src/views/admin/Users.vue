<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const loading = ref(false)
const users = ref([])
const total = ref(0)
const page = ref(1)
const roleFilter = ref('')
const search = ref('')
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)

const form = reactive({
  username: '',
  password: '',
  role: 'student',
  email: '',
  phone: '',
  email_alert_enabled: false,
  is_active: true,
})

const roleMap = {
  student: { label: '学生', type: '' },
  teacher: { label: '老师', type: 'success' },
  parent: { label: '家长', type: 'warning' },
  admin: { label: '管理员', type: 'danger' },
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value }
    if (roleFilter.value) params.role = roleFilter.value
    if (search.value) params.search = search.value
    const res = await request.get('/auth/admin/users/', { params })
    users.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    username: '',
    password: '',
    role: 'student',
    email: '',
    phone: '',
    email_alert_enabled: false,
    is_active: true,
  })
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    role: row.role,
    email: row.email || '',
    phone: row.phone || '',
    email_alert_enabled: Boolean(row.email_alert_enabled),
    is_active: Boolean(row.is_active),
  })
  dialogVisible.value = true
}

async function submitUser() {
  if (!form.username.trim()) {
    ElMessage.warning('用户名必填')
    return
  }
  if (!editingId.value && !form.password) {
    ElMessage.warning('新用户需要初始密码')
    return
  }
  submitting.value = true
  try {
    const payload = { ...form, username: form.username.trim() }
    if (editingId.value && !payload.password) delete payload.password
    if (editingId.value) {
      await request.patch(`/auth/admin/users/${editingId.value}/`, payload)
      ElMessage.success('用户已更新')
    } else {
      await request.post('/auth/admin/users/', payload)
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function deleteUser(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户 ${row.username}？该操作不可恢复。`, '删除用户', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await request.delete(`/auth/admin/users/${row.id}/`)
  ElMessage.success('用户已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div class="page-shell">
  <section class="page-hero">
    <div>
      <h1>系统用户管理</h1>
      <p>集中查看、创建、编辑和删除四类账号，支撑单班级三角色协同演示。</p>
    </div>
    <div class="hero-actions">
      <el-button type="primary" size="large" @click="openCreate">新建用户</el-button>
    </div>
  </section>

  <el-card shadow="never" class="panel">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <b>👥 用户管理</b>
        <div style="display:flex; gap:8px">
          <el-select v-model="roleFilter" placeholder="角色筛选" clearable style="width:120px" @change="() => { page=1; load() }">
            <el-option v-for="(v,k) in roleMap" :key="k" :label="v.label" :value="k" />
          </el-select>
          <el-input v-model="search" placeholder="搜索用户名" style="width:160px" clearable @input="() => { page=1; load() }" />
          <el-button type="primary" @click="openCreate">新建</el-button>
        </div>
      </div>
    </template>

    <el-table v-loading="loading" :data="users" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="roleMap[row.role]?.type">{{ roleMap[row.role]?.label || row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="真实姓名" min-width="120">
        <template #default="{ row }">{{ row.profile?.real_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="邮箱" min-width="200">
        <template #default="{ row }">{{ row.email || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="deleteUser(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 20"
      v-model:current-page="page"
      :page-size="20"
      :total="total"
      layout="prev, pager, next"
      style="margin-top: 12px; justify-content: flex-end"
      @current-change="load"
    />
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新建用户'" width="560px">
    <el-form label-width="100px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item :label="editingId ? '重置密码' : '初始密码'">
        <el-input v-model="form.password" type="password" show-password :placeholder="editingId ? '留空则不修改' : '至少 6 位'" />
      </el-form-item>
      <el-form-item label="角色">
        <el-select v-model="form.role" style="width:100%">
          <el-option v-for="(v,k) in roleMap" :key="k" :label="v.label" :value="k" />
        </el-select>
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="邮件预警">
        <el-switch v-model="form.email_alert_enabled" />
      </el-form-item>
      <el-form-item label="账号状态">
        <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitUser">
        {{ editingId ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
  </div>
</template>
