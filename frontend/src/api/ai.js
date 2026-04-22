import request from './request'

const AI_TIMEOUT_MS = 70000

export const aiApi = {
  getAdvice: () => request.post('/ai/advice/', {}, { timeout: AI_TIMEOUT_MS }),
  history: () => request.get('/ai/advice/history/'),
  classDiagnosis: () => request.post('/teacher/ai/class-diagnosis/', {}, { timeout: AI_TIMEOUT_MS }),
}
