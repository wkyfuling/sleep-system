<script setup>
import RoleLayout from './RoleLayout.vue'

const menu = [
  { path: '/student', title: '我的首页', icon: 'House' },
  { path: '/student/checkin', title: '今日打卡', icon: 'Clock' },
  { path: '/student/history', title: '历史记录', icon: 'Calendar' },
  { path: '/student/heatmap', title: '睡眠热力图', icon: 'Grid' },
  { path: '/student/ranking', title: '班级排行', icon: 'TrendCharts' },
  { path: '/student/ai', title: 'AI 智能建议', icon: 'MagicStick' },
  { path: '/student/achievements', title: '成就徽章', icon: 'Trophy' },
  { path: '/student/messages', title: '消息中心', icon: 'ChatDotRound' },
  { path: '/student/profile', title: '个人中心', icon: 'User' },
]
</script>

<template>
  <RoleLayout :menu="menu" title="学生端" accent="#667eea" messages-path="/student/messages" />
</template>
