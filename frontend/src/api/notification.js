import request from './request'

export const notificationApi = {
  list: (params) => request.get('/notifications/', { params }),
  unreadCount: () => request.get('/notifications/unread-count/'),
  markRead: (id) => request.post(`/notifications/${id}/read/`),
  markAllRead: () => request.post('/notifications/read-all/'),
  send: (payload) => request.post('/notifications/send/', payload),
  recipients: () => request.get('/notifications/recipients/'),
  broadcast: (payload) => request.post('/notifications/broadcast/', payload),
  alerts: () => request.get('/notifications/alerts/'),
}
