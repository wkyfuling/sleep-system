import request from './request'

export const aiApi = {
  getAdvice: () => request.post('/ai/advice/'),
  history: () => request.get('/ai/advice/history/'),
  classDiagnosis: () => request.post('/ai/class-diagnosis/'),
}
