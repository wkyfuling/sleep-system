<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()

const open = ref(false)
const loading = ref(false)
const input = ref('')
const scrollRef = ref(null)
let messageId = 1

const role = computed(() => userStore.user?.role || 'student')
const roleLabel = computed(() => userStore.user?.role_display || '用户')
const pageTitle = computed(() => route.meta.title || '工作台')

const starterText = computed(() => {
  const name = userStore.user?.profile?.real_name || userStore.user?.username || ''
  const prefix = name ? `${name}，` : ''
  return `${prefix}我是 SleepCare AI 助手。你可以问我睡眠趋势、风险解读、沟通建议或当前页面的数据含义。`
})

const messages = ref([
  { id: messageId++, role: 'assistant', content: starterText.value, isMock: false },
])

const suggestionsByRole = {
  student: [
    '解释我的睡眠质量分',
    '帮我分析近 7 天趋势',
    '给我今晚的作息建议',
    '为什么我会被标记为异常',
  ],
  teacher: [
    '解读班级近 7 夜风险',
    '帮我生成家长沟通话术',
    '给出班级睡眠治理建议',
    '如何处理连续异常学生',
  ],
  parent: [
    '解释孩子最近睡眠变化',
    '给我一段沟通建议',
    '今晚应该怎么帮孩子调整',
    '哪些情况需要重点关注',
  ],
  admin: [
    '概括当前系统运行情况',
    '帮我写一条睡眠科普通知',
    '解释今日提交和异常数据',
    '给比赛演示准备一段介绍',
  ],
}

const suggestions = computed(() => suggestionsByRole[role.value] || suggestionsByRole.student)

watch(starterText, (text) => {
  if (messages.value.length === 1 && messages.value[0].role === 'assistant') {
    messages.value[0].content = text
  }
})

function toggleOpen() {
  open.value = !open.value
  if (open.value) scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function compactHistory() {
  return messages.value
    .filter((item) => item.role === 'user' || item.role === 'assistant')
    .slice(-6)
    .map((item) => ({ role: item.role, content: item.content }))
}

async function sendMessage(text = input.value) {
  const content = String(text || '').trim()
  if (!content || loading.value) return

  const history = compactHistory()
  messages.value.push({ id: messageId++, role: 'user', content })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await aiApi.chat({
      message: content,
      history,
      page_context: `${roleLabel.value}端 / ${pageTitle.value}`,
    })
    messages.value.push({
      id: messageId++,
      role: 'assistant',
      content: res.reply,
      isMock: res.is_mock,
    })
  } catch (e) {
    messages.value.push({
      id: messageId++,
      role: 'assistant',
      content: 'AI 助手暂时没有响应，请稍后再试。若连续失败，请检查后端 AI 服务配置。',
      isMock: true,
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function useSuggestion(text) {
  sendMessage(text)
}

function clearChat() {
  messages.value = [{ id: messageId++, role: 'assistant', content: starterText.value, isMock: false }]
  input.value = ''
  ElMessage.success('对话已清空')
}
</script>

<template>
  <teleport to="body">
    <transition name="assistant-panel">
      <section v-if="open" class="assistant-panel" aria-label="SleepCare AI 助手">
        <header class="assistant-header">
          <div class="assistant-brand">
            <span class="assistant-logo"><MagicStick /></span>
            <div>
              <strong>SleepCare AI 助手</strong>
              <span>{{ loading ? '正在响应' : '在线' }}</span>
            </div>
          </div>
          <div class="assistant-actions">
            <el-tooltip content="清空对话" placement="bottom">
              <el-button circle text @click="clearChat">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="关闭" placement="bottom">
              <el-button circle text @click="open = false">
                <el-icon><Close /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </header>

        <main ref="scrollRef" class="assistant-body">
          <div
            v-for="item in messages"
            :key="item.id"
            class="message-row"
            :class="item.role"
          >
            <div class="message-bubble">
              <div class="message-text">{{ item.content }}</div>
              <el-tag v-if="item.role === 'assistant' && item.isMock" size="small" type="warning">
                兜底回复
              </el-tag>
            </div>
          </div>

          <div v-if="loading" class="message-row assistant">
            <div class="message-bubble loading-bubble">
              <span class="typing-dot" />
              <span class="typing-dot" />
              <span class="typing-dot" />
            </div>
          </div>
        </main>

        <section class="assistant-suggestions">
          <span>建议问题</span>
          <div class="suggestion-list">
            <button
              v-for="item in suggestions"
              :key="item"
              type="button"
              :disabled="loading"
              @click="useSuggestion(item)"
            >
              {{ item }}
            </button>
          </div>
        </section>

        <footer class="assistant-input">
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 3 }"
            maxlength="800"
            resize="none"
            placeholder="问 SleepCare AI..."
            @keydown.enter.exact.prevent="sendMessage()"
          />
          <el-tooltip content="发送" placement="top">
            <el-button type="primary" circle :loading="loading" @click="sendMessage()">
              <el-icon><Position /></el-icon>
            </el-button>
          </el-tooltip>
        </footer>
      </section>
    </transition>

    <el-tooltip content="SleepCare AI 助手" placement="left">
      <button type="button" class="assistant-fab" :class="{ active: open }" @click="toggleOpen">
        <el-icon :size="24"><MagicStick /></el-icon>
      </button>
    </el-tooltip>
  </teleport>
</template>

<style scoped>
.assistant-fab {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 3000;
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 16px;
  color: #fff;
  background: #10b981;
  box-shadow: 0 16px 34px rgba(16, 185, 129, 0.32);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.assistant-fab:hover,
.assistant-fab.active {
  transform: translateY(-2px);
  background: #059669;
  box-shadow: 0 18px 38px rgba(5, 150, 105, 0.36);
}

.assistant-panel {
  position: fixed;
  right: 28px;
  bottom: 96px;
  z-index: 2999;
  width: min(430px, calc(100vw - 32px));
  height: min(640px, calc(100vh - 128px));
  min-height: 480px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 24px 68px rgba(15, 23, 42, 0.22);
  display: grid;
  grid-template-rows: 74px 1fr auto auto;
  overflow: hidden;
}

.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #eef0f4;
  background: #fbfdfc;
}

.assistant-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.assistant-logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #10b981;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.assistant-brand strong {
  display: block;
  color: #1f2937;
  font-size: 16px;
  line-height: 1.25;
}

.assistant-brand span:last-child {
  display: block;
  margin-top: 2px;
  color: #6b7280;
  font-size: 12px;
}

.assistant-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.assistant-body {
  padding: 18px 16px 12px;
  overflow-y: auto;
  background: #ffffff;
}

.message-row {
  display: flex;
  margin-bottom: 12px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 86%;
  border-radius: 8px;
  padding: 11px 13px;
  line-height: 1.65;
  font-size: 14px;
  color: #1f2937;
  background: #f4f6f8;
}

.message-row.user .message-bubble {
  background: #10b981;
  color: #fff;
}

.message-text {
  white-space: pre-line;
  word-break: break-word;
}

.message-bubble :deep(.el-tag) {
  margin-top: 8px;
}

.loading-bubble {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 54px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  animation: pulse 1s infinite ease-in-out;
}

.typing-dot:nth-child(2) { animation-delay: 0.15s; }
.typing-dot:nth-child(3) { animation-delay: 0.3s; }

.assistant-suggestions {
  padding: 10px 16px 12px;
  border-top: 1px solid #f0f2f5;
  background: #fbfcfd;
}

.assistant-suggestions > span {
  display: block;
  margin-bottom: 8px;
  color: #6b7280;
  font-size: 12px;
}

.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-list button {
  min-height: 30px;
  max-width: 100%;
  border: 1px solid #dbe2ea;
  border-radius: 8px;
  padding: 5px 10px;
  background: #fff;
  color: #4b5563;
  font-size: 13px;
  cursor: pointer;
}

.suggestion-list button:hover {
  border-color: #10b981;
  color: #047857;
}

.suggestion-list button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.assistant-input {
  display: grid;
  grid-template-columns: 1fr 44px;
  gap: 10px;
  align-items: end;
  padding: 14px 16px 16px;
  border-top: 1px solid #eef0f4;
  background: #fff;
}

.assistant-input :deep(.el-textarea__inner) {
  min-height: 42px !important;
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.5;
}

.assistant-input :deep(.el-button) {
  width: 44px;
  height: 44px;
}

.assistant-panel-enter-active,
.assistant-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.assistant-panel-enter-from,
.assistant-panel-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@keyframes pulse {
  0%, 80%, 100% { opacity: 0.35; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-2px); }
}

@media (max-width: 640px) {
  .assistant-fab {
    right: 18px;
    bottom: 18px;
  }

  .assistant-panel {
    right: 0;
    bottom: 0;
    width: 100vw;
    height: min(78vh, 680px);
    min-height: 440px;
    border-radius: 8px 8px 0 0;
  }
}
</style>
