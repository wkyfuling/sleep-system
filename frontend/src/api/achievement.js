import request from './request'

export const achievementApi = {
  myAchievements: () => request.get('/achievements/me/'),
}
