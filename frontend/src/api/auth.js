import request from './request'

export const authApi = {
  login: (payload) => request.post('/auth/login/', payload),
  register: (payload) => request.post('/auth/register/', payload),
  me: () => request.get('/auth/me/'),
  refresh: (refresh) => request.post('/auth/refresh/', { refresh }),
  generateParentCode: () => request.post('/auth/generate-parent-code/'),
  updatePreferences: (payload) => request.patch('/auth/profile/preferences/', payload),
}
