<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const notifStore = useNotificationStore()

const props = defineProps({
  menu: { type: Array, required: true },   // [{ path, title, icon }]
  title: { type: String, default: '睡眠管理系统' },
  accent: { type: String, default: '#667eea' },
  messagesPath: { type: String, default: '' },  // e.g. '/student/messages'
})

const activePath = computed(() => route.path)
const pageTitle = computed(() => route.meta.title || '工作台')
const displayName = computed(() => {
  const u = userStore.user
  if (!u) return ''
  const p = u.profile
  return p?.real_name || u.username
})

onMounted(() => notifStore.startPolling())
onUnmounted(() => notifStore.stopPolling())

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    notifStore.reset()
    userStore.logout()
    router.push('/login')
  } catch { /* cancelled */ }
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="236px" class="aside" :style="{ '--accent': accent }">
      <div class="brand">
        <span class="logo"><Moon /></span>
        <div>
          <span class="brand-text">{{ title }}</span>
          <span class="brand-sub">SleepCare</span>
        </div>
      </div>

      <el-menu
        :default-active="activePath"
        router
        class="menu"
        background-color="transparent"
        text-color="#ffffffcc"
        active-text-color="#ffffff"
      >
        <el-menu-item
          v-for="item in menu"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="crumbs">
          <el-icon><Sunny /></el-icon>
          <span>{{ userStore.user?.role_display }}端</span>
          <span class="slash">/</span>
          <strong>{{ pageTitle }}</strong>
        </div>
        <div class="user-box">
          <!-- 通知铃铛 -->
          <el-badge
            v-if="messagesPath"
            :value="notifStore.unreadCount || ''"
            :hidden="!notifStore.unreadCount"
            type="danger"
            style="cursor: pointer; margin-right: 8px"
            @click="router.push(messagesPath)"
          >
            <el-icon :size="20"><Bell /></el-icon>
          </el-badge>
          <span class="name">{{ displayName }}</span>
          <el-dropdown trigger="click">
            <el-avatar :size="32" style="cursor:pointer">
              {{ displayName?.[0] || 'U' }}
            </el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout { height: 100vh; background: #f3f6fb; }
.aside {
  color: #fff;
  display: flex; flex-direction: column;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--accent), #111827 12%), var(--accent)),
    radial-gradient(circle at 18% 8%, rgba(255,255,255,.24), transparent 28%);
  box-shadow: 2px 0 18px rgba(31,41,55,0.12);
}
.brand {
  padding: 22px 18px;
  display: flex; align-items: center; gap: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
}
.logo {
  width: 38px; height: 38px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.18);
  font-size: 20px;
}
.brand-text { display: block; font-size: 17px; font-weight: 700; line-height: 1.2; }
.brand-sub { display: block; margin-top: 3px; color: rgba(255,255,255,.68); font-size: 12px; }
.menu { border-right: none; padding: 10px 10px 0; }
.menu :deep(.el-menu-item) { border-radius: 8px; height: 44px; margin-bottom: 4px; }
.menu :deep(.el-menu-item.is-active) { background: rgba(255,255,255,0.16) !important; }
.menu :deep(.el-menu-item:hover) { background: rgba(255,255,255,0.08) !important; }

.header {
  height: 64px;
  background: rgba(255,255,255,.96);
  border-bottom: 1px solid #e9edf5;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  backdrop-filter: blur(10px);
}
.crumbs { display: flex; align-items: center; gap: 8px; color: #606266; }
.slash { color: #c0c4cc; }
.crumbs strong { color: #1f2937; font-size: 16px; }
.user-box { display: flex; align-items: center; gap: 12px; }
.name { color: #303133; font-size: 14px; }

.main {
  background:
    linear-gradient(180deg, #f8fbff 0%, #f3f6fb 42%, #f3f6fb 100%);
  padding: 22px;
  overflow-y: auto;
}
</style>
