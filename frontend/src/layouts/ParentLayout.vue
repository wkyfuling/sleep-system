<script setup>
import RoleLayout from './RoleLayout.vue'

const menu = [
  { path: '/parent', title: '孩子概览', icon: 'House' },
  { path: '/parent/alerts', title: '预警通知', icon: 'Warning' },
  { path: '/parent/messages', title: '消息中心', icon: 'ChatDotRound' },
  { path: '/parent/profile', title: '个人中心', icon: 'User' },
]
</script>

<template>
  <RoleLayout :menu="menu" title="家长端" accent="#67c23a" messages-path="/parent/messages" />
</template>
