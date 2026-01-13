<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { addFile } from '../store/files'
import { processPdfFile } from '../utils/pdfUtils'
import { savePdfProcessingResult } from '../utils/dbUtils'

const router = useRouter()
const isDragging = ref(false)
const fileName = ref('')
const fileInput = ref(null)
const isProcessing = ref(false)
const processingStatus = ref('')

function navigateToWorkspace(file, pdfFileId) {
  const url = URL.createObjectURL(file)
  const id = addFile({ 
    name: file.name, 
    size: file.size, 
    src: url,
    pdfFileId // 添加PDF文件ID以便在工作区使用
  })
  router.push({ name: 'workspace', query: { id } })
}

async function handleFile(file) {
  if (!file) return
  
  // 检查是否为PDF文件
  if (file.type !== 'application/pdf') {
    alert('请上传PDF文件！')
    return
  }
  
  fileName.value = file.name
  isProcessing.value = true
  processingStatus.value = '正在解析PDF文件...'
  
  try {
    // 处理PDF文件，生成缩略图
    processingStatus.value = '正在生成页面缩略图...'
    const pdfData = await processPdfFile(file, { width: 200 })
    
    // 保存到数据库
    processingStatus.value = '正在保存数据...'
    const pdfFileId = await savePdfProcessingResult(pdfData)
    
    // 导航到工作区
    navigateToWorkspace(file, pdfFileId)
  } catch (error) {
    console.error('PDF处理失败:', error)
    alert('PDF处理失败：' + error.message)
  } finally {
    isProcessing.value = false
    processingStatus.value = ''
  }
}

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave(e) {
  e.preventDefault()
  isDragging.value = false
}

function onDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) handleFile(file)
}

function chooseFile() {
  fileInput.value?.click()
}
</script>

<template>
  <div class="page-container flex items-center justify-center px-6">
    <div class="max-w-2xl w-full">
      <div class="text-center">
        <div class="mx-auto mb-6 h-14 w-14 rounded-2xl bg-indigo-100 flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-7 w-7 text-indigo-600">
            <path d="M12 16a1 1 0 0 1-1-1V8.41l-1.3 1.29a1 1 0 1 1-1.4-1.42l3-3a1 1 0 0 1 1.4 0l3 3a1 1 0 1 1-1.4 1.42L13 8.41V15a1 1 0 0 1-1 1Z"/>
            <path d="M5 19a3 3 0 0 1-3-3V9a3 3 0 0 1 3-3h3a1 1 0 1 1 0 2H5a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1h-3a1 1 0 1 1 0-2h3a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3H5Z"/>
          </svg>
        </div>
        <h1 class="text-3xl font-bold text-gray-900">PDF 文字识别</h1>
        <p class="mt-2 text-gray-600">上传PDF文件，AI自动提取其中的文字内容</p>
        <span class="mt-3 badge badge-info">AI智能识别</span>
        <div class="mt-4 flex gap-4 justify-center">
          <button class="text-sm text-indigo-600 hover:underline font-medium" @click="router.push({name:'files'})">进入文件管理</button>
          <button class="text-sm text-indigo-600 hover:underline font-medium" @click="router.push({name:'settings'})">OCR 配置</button>
        </div>
      </div>

      <div
        class="mt-8 card p-10 text-center transition-colors border-2 border-dashed"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        :class="{ 'opacity-70 cursor-not-allowed': isProcessing, 'drag-over': isDragging }"
      >
        <input ref="fileInput" id="file" type="file" class="hidden" accept="application/pdf" @change="onFileChange" />
        
        <!-- 处理中状态 -->
        <div v-if="isProcessing" class="space-y-4">
          <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-indigo-600 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <p class="text-gray-700 font-medium">{{ processingStatus }}</p>
          <p class="text-sm text-gray-500">请稍候，正在处理您的PDF文件...</p>
        </div>
        
        <!-- 正常状态 -->
        <template v-else>
          <div class="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-6 w-6 text-indigo-600">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <p class="text-gray-700 font-medium">拖拽PDF文件到这里</p>
          <p class="mt-1 text-sm text-gray-500">或点击选择文件</p>
          <div class="mt-6">
            <button class="btn-primary inline-flex items-center gap-2" @click="chooseFile">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
                <path d="M12 16a1 1 0 0 1-1-1V8.41l-1.3 1.29a1 1 0 1 1-1.4-1.42l3-3a1 1 0 0 1 1.4 0l3 3a1 1 0 1 1-1.4 1.42L13 8.41V15a1 1 0 0 1-1 1Z"/>
              </svg>
              选择文件
            </button>
          </div>
          <div v-if="fileName" class="mt-4 text-sm text-gray-600">已选择：{{ fileName }}</div>
        </template>
      </div>
    </div>
  </div>
</template>
