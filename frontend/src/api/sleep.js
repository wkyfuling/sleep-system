import request from './request'

export const sleepApi = {
  // 学生端 — 打卡记录
  createRecord: (payload) => request.post('/sleep/records/', payload),
  listRecords: (params) => request.get('/sleep/records/', { params }),
  getRecord: (id) => request.get(`/sleep/records/${id}/`),
  updateRecord: (id, payload) => request.patch(`/sleep/records/${id}/`, payload),

  // 学生端 — 统计
  weekStats: () => request.get('/sleep/statistics/week/'),
  heatmap: (year) => request.get('/sleep/heatmap/', { params: { year } }),
  ranking: () => request.get('/sleep/ranking/'),

  // 老师端（审计代改）
  teacherEdit: (id, payload) => request.patch(`/sleep/teacher/records/${id}/`, payload),
}
