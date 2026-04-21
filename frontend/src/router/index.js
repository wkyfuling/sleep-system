import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/', redirect: (to) => {
      const u = JSON.parse(localStorage.getItem('user') || 'null')
      if (!u) return '/login'
      return { student: '/student', teacher: '/teacher', parent: '/parent', admin: '/admin' }[u.role] || '/login'
    },
  },

  {
    path: '/login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { public: true },
  },
  {
    path: '/403',
    component: () => import('@/views/Forbidden.vue'),
    meta: { public: true },
  },

  // 学生端
  {
    path: '/student',
    component: () => import('@/layouts/StudentLayout.vue'),
    meta: { roles: ['student'] },
    children: [
      { path: '', component: () => import('@/views/student/Home.vue') },
      { path: 'checkin', component: () => import('@/views/student/CheckIn.vue'), meta: { title: '今日打卡' } },
      { path: 'history', component: () => import('@/views/student/History.vue'), meta: { title: '历史记录' } },
      { path: 'heatmap', component: () => import('@/views/student/Heatmap.vue'), meta: { title: '睡眠热力图' } },
      { path: 'ranking', component: () => import('@/views/student/Ranking.vue'), meta: { title: '班级排行' } },
      { path: 'ai', component: () => import('@/views/student/AiAdvice.vue'), meta: { title: 'AI 建议' } },
      { path: 'achievements', component: () => import('@/views/student/Achievements.vue'), meta: { title: '成就徽章' } },
      { path: 'messages', component: () => import('@/views/shared/Messages.vue'), meta: { title: '消息中心' } },
      { path: 'profile', component: () => import('@/views/shared/Profile.vue'), meta: { title: '个人中心' } },
    ],
  },

  // 老师端
  {
    path: '/teacher',
    component: () => import('@/layouts/TeacherLayout.vue'),
    meta: { roles: ['teacher'] },
    children: [
      { path: '', component: () => import('@/views/teacher/Home.vue') },
      { path: 'students', component: () => import('@/views/teacher/Students.vue'), meta: { title: '学生列表' } },
      { path: 'alerts', component: () => import('@/views/teacher/Alerts.vue'), meta: { title: '预警中心' } },
      { path: 'notifications', component: () => import('@/views/teacher/Notifications.vue'), meta: { title: '发布通知' } },
      { path: 'export', component: () => import('@/views/teacher/Export.vue'), meta: { title: '报表导出' } },
      { path: 'messages', component: () => import('@/views/shared/Messages.vue'), meta: { title: '消息中心' } },
      { path: 'profile', component: () => import('@/views/shared/Profile.vue'), meta: { title: '个人中心' } },
    ],
  },

  // 家长端
  {
    path: '/parent',
    component: () => import('@/layouts/ParentLayout.vue'),
    meta: { roles: ['parent'] },
    children: [
      { path: '', component: () => import('@/views/parent/Home.vue') },
      { path: 'alerts', component: () => import('@/views/parent/Alerts.vue'), meta: { title: '预警通知' } },
      { path: 'messages', component: () => import('@/views/shared/Messages.vue'), meta: { title: '消息中心' } },
      { path: 'profile', component: () => import('@/views/shared/Profile.vue'), meta: { title: '个人中心' } },
    ],
  },

  // 管理员
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { roles: ['admin'] },
    children: [
      { path: '', component: () => import('@/views/admin/Home.vue') },
      { path: 'users', component: () => import('@/views/admin/Users.vue'), meta: { title: '用户管理' } },
      { path: 'articles', component: () => import('@/views/admin/Articles.vue'), meta: { title: '科普文章' } },
      { path: 'seed', component: () => import('@/views/admin/Seed.vue'), meta: { title: '演示数据' } },
    ],
  },

  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/NotFound.vue'),
    meta: { public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) return true

  const store = useUserStore()
  if (!store.isLoggedIn) return { path: '/login', query: { next: to.fullPath } }

  const required = to.meta.roles
  if (required && !required.includes(store.role)) return '/403'

  return true
})

export default router
