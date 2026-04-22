import request from './request'

const AI_TIMEOUT_MS = 90000
const ASSISTANT_TIMEOUT_MS = 60000

export const aiApi = {
  getAdvice: () => request.post('/ai/advice/', {}, { timeout: AI_TIMEOUT_MS }),
  history: () => request.get('/ai/advice/history/'),
  classDiagnosis: () => request.post('/teacher/ai/class-diagnosis/', {}, { timeout: AI_TIMEOUT_MS }),
  chat: (payload) => request.post('/ai/chat/', payload, { timeout: ASSISTANT_TIMEOUT_MS }),
}
