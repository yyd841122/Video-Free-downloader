<script setup>
import { ref } from 'vue'
import { createAiSummaryFromSubtitle } from '../api/client'

const props = defineProps({
  title: {
    type: String,
    default: '',
  },
  url: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['created', 'error'])

const selectedFile = ref(null)
const uploading = ref(false)
const localError = ref('')

const onFileChange = (event) => {
  const [file] = Array.from(event.target.files || [])
  selectedFile.value = file || null
  localError.value = ''
}

const uploadSubtitle = async () => {
  if (!selectedFile.value || uploading.value) {
    return
  }
  localError.value = ''
  uploading.value = true
  try {
    const created = await createAiSummaryFromSubtitle({
      file: selectedFile.value,
      title: props.title,
      url: props.url,
    })
    emit('created', created)
  } catch (err) {
    localError.value = err.message
    emit('error', err.message)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <section class="subtitle-upload" aria-label="上传字幕生成总结">
    <div>
      <h4>上传字幕继续总结</h4>
      <p>如果平台没有开放字幕，可以上传 SRT/VTT 文件继续生成摘要、思维导图和问答。</p>
    </div>
    <div class="subtitle-upload-controls">
      <label class="subtitle-file">
        <input accept=".srt,.vtt,text/vtt" type="file" @change="onFileChange" />
        <span>{{ selectedFile?.name || '选择 SRT/VTT 字幕' }}</span>
      </label>
      <button type="button" :disabled="!selectedFile || uploading" @click="uploadSubtitle">
        {{ uploading ? '上传中' : '上传并总结' }}
      </button>
    </div>
    <p v-if="localError" class="subtitle-upload-error">{{ localError }}</p>
  </section>
</template>

<style scoped>
.subtitle-upload {
  display: grid;
  gap: 14px;
  margin-top: 14px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e8eef7;
  border-radius: 14px;
}

.subtitle-upload h4 {
  margin: 0;
  color: #1b202a;
}

.subtitle-upload p {
  margin: 7px 0 0;
  color: #7f8b9c;
  line-height: 1.6;
}

.subtitle-upload-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.subtitle-file {
  display: grid;
  min-height: 44px;
  align-items: center;
  padding: 0 14px;
  color: #4d5a6c;
  font-weight: 800;
  background: #f8fbff;
  border: 1px dashed #b8cff0;
  border-radius: 12px;
  cursor: pointer;
}

.subtitle-file input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
}

.subtitle-file span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subtitle-upload button {
  min-height: 44px;
  padding: 0 18px;
  color: #ffffff;
  font-weight: 900;
  background: #367cff;
  border: 0;
  border-radius: 999px;
}

.subtitle-upload button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.subtitle-upload-error {
  color: #b4233b;
}

@media (max-width: 560px) {
  .subtitle-upload-controls {
    grid-template-columns: 1fr;
  }

  .subtitle-upload button {
    width: 100%;
  }
}
</style>
