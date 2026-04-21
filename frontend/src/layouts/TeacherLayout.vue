<script setup>
import RoleLayout from './RoleLayout.vue'

const menu = [
  { path: '/teacher', title: '班级概览', icon: 'House' },
  { path: '/teacher/students', title: '学生列表', icon: 'UserFilled' },
  { path: '/teacher/alerts', title: '预警中心', icon: 'Warning' },
  { path: '/teacher/notifications', title: '发布通知', icon: 'Bell' },
  { path: '/teacher/export', title: '报表导出', icon: 'Download' },
  { path: '/teacher/messages', title: '消息中心', icon: 'ChatDotRound' },
  { path: '/teacher/profile', title: '个人中心', icon: 'User' },
]
</script>

<template>
  <RoleLayout :menu="menu" title="老师端" accent="#409eff" messages-path="/teacher/messages" />
</template>
