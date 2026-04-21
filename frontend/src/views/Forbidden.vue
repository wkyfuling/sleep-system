<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
const router = useRouter()
const userStore = useUserStore()

const roleHome = { student: '/student', teacher: '/teacher', parent: '/parent', admin: '/admin' }
</script>

<template>
  <el-result icon="warning" title="403" sub-title="你没有访问该页面的权限">
    <template #extra>
      <el-button type="primary" @click="router.push(roleHome[userStore.role] || '/')">回到首页</el-button>
      <el-button @click="userStore.logout(); router.push('/login')">切换账号</el-button>
    </template>
  </el-result>
</template>
