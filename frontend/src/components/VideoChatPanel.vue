<script setup>
import { computed, ref } from 'vue'
import { chatWithAiSummary } from '../api/client'

const props = defineProps({
  taskId: {
    type: String,
    required: true,
  },
})

const question = ref('')
const messages = ref([])
const loading = ref(false)
const error = ref('')

const canSend = computed(() => question.value.trim().length > 0 && !loading.value)

const sendQuestion = async () => {
  const text = question.value.trim()
  if (!text || loading.value) {
    return
  }
  error.value = ''
  loading.value = true
  question.value = ''
  const userMessage = { role: 'user', content: text }
  messages.value = [...messages.value, userMessage]
  try {
    const history = messages.value.slice(-8)
    const result = await chatWithAiSummary(props.taskId, {
      question: text,
      history,
    })
    messages.value = [
      ...messages.value,
      {
        role: 'assistant',
        content: result.answer,
        references: result.references || [],
      },
    ]
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="video-chat" aria-label="视频内容 AI 问答">
    <div v-if="messages.length" class="chat-messages" aria-live="polite">
      <article v-for="(message, index) in messages" :key="`${message.role}-${index}-${message.content}`" :class="['chat-message', message.role]">
        <p>{{ message.content }}</p>
        <div v-if="message.references?.length" class="chat-references">
          <time v-for="item in message.references" :key="item">{{ item }}</time>
        </div>
      </article>
    </div>

    <div v-else class="chat-empty">
      可以问：“这个视频最重要的三个观点是什么？”或“哪些时间点适合回看？”
    </div>

    <form class="chat-form" @submit.prevent="sendQuestion">
      <label class="sr-only" for="video-chat-question">向视频提问</label>
      <textarea
        id="video-chat-question"
        v-model="question"
        rows="3"
        placeholder="输入你想追问的视频内容..."
      ></textarea>
      <button type="submit" :disabled="!canSend">{{ loading ? '回答中' : '发送' }}</button>
    </form>

    <p v-if="error" class="chat-error">{{ error }}</p>
  </section>
</template>

<style scoped>
.video-chat {
  padding: 18px 16px 16px;
  background: #ffffff;
  border: 0;
  border-radius: 0;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 420px;
  overflow: auto;
  padding: 0 4px 2px;
}

.chat-message {
  max-width: 88%;
  padding: 12px 14px;
  border-radius: 13px;
}

.chat-message.user {
  align-self: flex-end;
  max-width: 76%;
  color: #ffffff;
  background: #3b82f6;
  border: 1px solid #2f75e8;
  border-top-right-radius: 5px;
  box-shadow: 0 8px 18px rgba(59, 130, 246, 0.2);
}

.chat-message.assistant {
  align-self: flex-start;
  color: #263244;
  background: #f5f7fb;
  border: 1px solid #eef1f6;
  border-top-left-radius: 5px;
}

.chat-message p {
  margin: 0;
  color: inherit;
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
}

.chat-references {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.chat-references time {
  padding: 4px 8px;
  color: #367cff;
  font-size: 12px;
  font-weight: 900;
  background: #ffffff;
  border: 1px solid #dce8ff;
  border-radius: 999px;
}

.chat-empty {
  padding: 18px 16px;
  color: #718096;
  line-height: 1.7;
  background: #f8fbff;
  border: 1px solid #e8eef7;
  border-radius: 12px;
}

.chat-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  margin-top: 14px;
  align-items: end;
}

.chat-form textarea {
  width: 100%;
  min-height: 76px;
  resize: vertical;
  padding: 12px 14px;
  color: #1f2937;
  background: #ffffff;
  border: 1px solid #dce6f5;
  border-radius: 12px;
  outline: none;
  line-height: 1.6;
}

.chat-form textarea:focus {
  border-color: #8cbaff;
  box-shadow: 0 0 0 3px rgba(54, 124, 255, 0.12);
}

.chat-form button {
  min-width: 96px;
  min-height: 44px;
  padding: 0 18px;
  color: #ffffff;
  font-weight: 900;
  background: #367cff;
  border: 0;
  border-radius: 999px;
}

.chat-form button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.chat-error {
  margin: 12px 0 0;
  color: #b4233b;
  line-height: 1.6;
}

@media (max-width: 560px) {
  .video-chat {
    padding: 14px;
  }

  .chat-form {
    grid-template-columns: 1fr;
  }

  .chat-form button {
    width: 100%;
  }
}
</style>
