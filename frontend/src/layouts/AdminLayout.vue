<script setup>
import RoleLayout from './RoleLayout.vue'

const menu = [
  { path: '/admin', title: '全局统计', icon: 'DataAnalysis' },
  { path: '/admin/users', title: '用户管理', icon: 'UserFilled' },
  { path: '/admin/articles', title: '科普文章', icon: 'Document' },
  { path: '/admin/seed', title: '演示数据', icon: 'DataLine' },
]
</script>

<template>
  <RoleLayout :menu="menu" title="管理员" accent="#303133" />
</template>
