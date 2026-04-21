# 学生睡眠管理系统 API 文档

基础地址：`http://127.0.0.1:8000/api`

认证方式：登录后在请求头携带 `Authorization: Bearer <access_token>`。

## 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register/` | 按 `role` 注册学生、老师、家长 |
| POST | `/auth/login/` | 登录并返回 JWT |
| POST | `/auth/refresh/` | 刷新 access token |
| GET | `/auth/me/` | 当前用户信息 |
| PATCH | `/auth/profile/preferences/` | 更新邮件预警、学生日记分享偏好 |
| POST | `/auth/generate-parent-code/` | 学生生成家长邀请码 |

## 学生

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/sleep/records/` | 打卡/补卡，后端自动计算归属日期和评分 |
| PATCH | `/sleep/records/{id}/` | 学生 2 小时内自改 |
| GET | `/sleep/records/?from=&to=` | 睡眠记录列表 |
| GET | `/sleep/statistics/week/` | 近 7 天统计 |
| GET | `/sleep/heatmap/?year=` | 年度热力图数据 |
| GET | `/sleep/ranking/` | 班级匿名排行 |
| POST | `/ai/advice/` | 学生手动触发 AI 建议，每天 3 次 |
| GET | `/ai/advice/history/` | 最近 30 条 AI 建议 |
| GET | `/achievements/me/` | 我的成就徽章 |

## 老师

设计文档路径已提供兼容别名；旧模块路径仍可用。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/teacher/classroom/` | 创建班级并生成邀请码 |
| GET | `/teacher/class/overview/` | 班级概览 |
| GET | `/teacher/students/?status=` | 学生列表 |
| GET | `/teacher/students/{id}/trend/` | 学生近 30 天趋势 |
| PATCH | `/teacher/records/{id}/` | 老师代改记录，必须填 `modified_reason` |
| GET | `/teacher/alerts/` | 本班异常预警 |
| POST | `/teacher/notifications/` | 班级公告群发 |
| GET | `/notifications/recipients/` | 获取当前老师可联系的学生/家长 |
| GET | `/teacher/export/month_excel/` | 班级月报 Excel |
| GET | `/teacher/export/day_overview_excel/` | 单日班级概览 Excel |
| GET | `/teacher/export/semester_pdf/` | 个人学期 PDF |
| POST | `/teacher/ai/class-diagnosis/` | 班级整体 AI 诊断 |

## 家长

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/parent/child/overview/` | 孩子近 30 天摘要 |
| GET | `/parent/alerts/` | 孩子异常记录 |
| GET/POST | `/parent/messages/` | 消息收件箱/发消息 |
| GET | `/notifications/recipients/` | 获取当前家长可联系的孩子/老师 |

## 通用消息

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/notifications/` | 当前用户收件箱 |
| POST | `/notifications/send/` | 点对点发消息，后端校验角色边界 |
| GET | `/notifications/recipients/` | 当前用户可联系对象 |
| POST | `/notifications/{id}/read/` | 单条已读 |
| POST | `/notifications/read-all/` | 全部已读 |
| GET | `/notifications/unread-count/` | 未读数 |

## 管理员

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/admin/users/` | 用户列表/创建用户 |
| GET/PATCH/DELETE | `/admin/users/{id}/` | 用户详情/修改/删除 |
| GET/POST/PATCH/DELETE | `/admin/articles/` | 科普文章管理 |
| POST | `/admin/seed-demo-data/` | 一键生成演示数据 |
| GET | `/admin/global-stats/` | 全局统计 |
