import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationApi } from '@/api/notification'

export const useNotificationStore = defineStore('notification', () => {
  const unreadCount = ref(0)
  let _timer = null

  async function fetchUnread() {
    try {
      const res = await notificationApi.unreadCount()
      unreadCount.value = res.count
    } catch (_) {}
  }

  function startPolling(intervalMs = 30000) {
    fetchUnread()
    if (_timer) clearInterval(_timer)
    _timer = setInterval(fetchUnread, intervalMs)
  }

  function stopPolling() {
    if (_timer) { clearInterval(_timer); _timer = null }
  }

  function decrement() {
    if (unreadCount.value > 0) unreadCount.value--
  }

  function reset() {
    unreadCount.value = 0
    stopPolling()
  }

  return { unreadCount, fetchUnread, startPolling, stopPolling, decrement, reset }
})
