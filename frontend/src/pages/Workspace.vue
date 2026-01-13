<script setup>
import { onMounted, ref, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
// 导入Quill编辑器
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css';

// 导入PreviewSection组件
import PreviewSection from '../components/PreviewSection.vue';
import Api from '@/api/file'

const route = useRoute()
const fileId = ref(route.query.id || '')
const pdfData = ref(null)
const pages = ref([])
const selectedPage = ref(1)
const selectedPageInfo = ref({ocr_text: ""})
const loading = ref(false)
const error = ref(null)
const ocrAgain = ref(false) // 是否重新OCR
const ocrLoading = ref(false) // OCR加载状态
const ocrProgress = ref(0) // OCR进度 (0-100)
const batchOcrProgress = ref({ current: 0, total: 0 }) // 批量OCR进度
const showShortcutsModal = ref(false) // 显示快捷键帮助弹窗

// 导出功能
async function exportToFile() {
  if (!fileId.value || !pdfData.value) return

  try {
    // 生成文本内容（所有页面的OCR结果）
    let content = `文件名: ${pdfData.value.original_filename}\n`
    content += `导出时间: ${new Date().toLocaleString('zh-CN')}\n`
    content += `总页数: ${pages.value.length}\n`
    content += '\n' + '='.repeat(50) + '\n\n'

    pages.value.forEach((page, index) => {
      content += `--- 第 ${index + 1} 页 ---\n`
      if (page.ocr_text && page.ocr_text.trim()) {
        content += page.ocr_text + '\n'
      } else {
        content += '[无OCR内容]\n'
      }
      content += '\n'
    })

    // 创建 Blob 并下载
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${pdfData.value.original_filename}_ocr.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    // 显示成功提示
    if (window.toastManager) {
      window.toastManager.show({ message: '文件导出成功！', type: 'success', duration: 3000, title: '导出完成' })
    }
  } catch (error) {
    console.error('导出失败:', error)
    if (window.toastManager) {
      window.toastManager.show({ message: '导出失败，请稍后重试', type: 'error', duration: 3000, title: '导出错误' })
    }
  }
}

async function exportToMarkdown() {
  if (!fileId.value || !pdfData.value) return

  try {
    // 生成 Markdown 内容
    let content = `# ${pdfData.value.original_filename}\n\n`
    content += `导出时间: ${new Date().toLocaleString('zh-CN')}\n`
    content += `总页数: ${pages.value.length}\n\n`

    content += '---\n\n'

    pages.value.forEach((page, index) => {
      content += `## 第 ${index + 1} 页\n\n`
      if (page.ocr_text && page.ocr_text.trim()) {
        content += page.ocr_text + '\n\n'
      } else {
        content += '*无OCR内容*\n\n'
      }
    })

    // 创建 Blob 并下载
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${pdfData.value.original_filename}_ocr.md`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    if (window.toastManager) {
      window.toastManager.show({ message: 'Markdown 文件导出成功！', type: 'success', duration: 3000, title: '导出完成' })
    }
  } catch (error) {
    console.error('导出失败:', error)
    if (window.toastManager) {
      window.toastManager.show({ message: '导出失败，请稍后重试', type: 'error', duration: 3000, title: '导出错误' })
    }
  }
}

// 预览组件引用
const previewSectionRef = ref(null)

// 左侧页面列表容器引用
const pagesContainerRef = ref(null)

// 编辑器引用
const editorRef = ref(null)

// 左侧页面列表是否有焦点
const pagesListHasFocus = ref(false)

// Quill编辑器配置
const editorOptions = {
  theme: 'snow',
  placeholder: '请输入内容...',
  modules: {
    toolbar: [
      [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
      ['bold', 'italic', 'underline', 'strike'],
      [{ 'color': [] }, { 'background': [] }],
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      [{ 'indent': '-1'}, { 'indent': '+1' }],
      [{ 'align': [] }],
      ['clean'],
      ['undo', 'redo'] // 添加撤销/重做按钮
    ]
  }
}

// 处理键盘事件
function handleKeyDown(event) {
  // 检查是否按下了Ctrl+S
  if (event.ctrlKey && event.key === 's') {
    // 阻止浏览器默认保存行为
    event.preventDefault()

    // 检查焦点是否在编辑器内
    const editorElement = editorRef.value?.$el
    if (editorElement && editorElement.contains(document.activeElement)) {
      // 调用保存函数
      saveContentToFile()
    }
  }

  // 检查是否按下了Ctrl+? 显示快捷键帮助
  if (event.ctrlKey && (event.key === '?' || event.key === 'Shift')) {
    event.preventDefault()
    showShortcutsModal.value = true
  }

  // 检查是否按下了Esc 关闭弹窗
  if (event.key === 'Escape') {
    if (showShortcutsModal.value) {
      showShortcutsModal.value = false
    }
  }

  // 检查是否按下了上下箭头键，且左侧页面列表有焦点
  if (pagesListHasFocus.value && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
    // 阻止默认滚动行为
    event.preventDefault()

    // 计算新的页面号
    let newPage = selectedPage.value
    if (event.key === 'ArrowUp') {
      // 向上箭头：上一页
      newPage = Math.max(1, selectedPage.value - 1)
    } else if (event.key === 'ArrowDown') {
      // 向下箭头：下一页
      newPage = Math.min(pages.value.length, selectedPage.value + 1)
    }

    // 如果页面号有变化，则选择新页面
    if (newPage !== selectedPage.value) {
      select(newPage)
    }
  }
}

async function loadPdfData() {
  if (!fileId.value) {
    error.value = '文件ID不存在'
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await Api.info(fileId.value)
    // if (response.status && response.status !== 'success') {
    //   throw new Error('Failed to fetch PDF data')
    // }

    const data = response
    pdfData.value = data

    // 使用环境变量构建API基础URL
    const baseURL = import.meta.env.VITE_APP_BASE_API || 'http://127.0.0.1:8000'

    // 根据API返回的数据构建页面列表
    if (data.pages && Array.isArray(data.pages)) {
      pages.value = data.pages.map(page => ({
        index: page.page_number,
        image_url: `${baseURL}/api/file/${fileId.value}/image/${page.page_number}`,
        thumb_url: page.thumb_url || `${baseURL}/api/file/${fileId.value}/image/${page.page_number}`,
        ocr_text: page.ocr_text,
        width: page.width,
        height: page.height
      }))
    } else {
      // 如果没有pages数组，尝试从total_pages生成
      const totalPages = data.total_pages || 0
      pages.value = Array.from({ length: totalPages }, (_, i) => ({
        index: i + 1,
        image_url: `${baseURL}/api/file/${fileId.value}/image/${i + 1}`,
        thumb_url: `${baseURL}/api/file/${fileId.value}/image/${i + 1}`,
        ocr_text: "",
        width: null,
        height: null
      }))
    }

    // 显示页面：从本地缓存读取上次选中的页面
    if (pages.value.length > 0) {
      // 从本地缓存读取上次选中的页面
      const cacheKey = `file_${fileId.value}_page`
      const cachedPage = localStorage.getItem(cacheKey)
      let pageToSelect = selectedPage.value
      console.log(cachedPage)
      // 如果缓存存在且有效，则使用缓存的页面号
      if (cachedPage) {
        const cachedPageNum = parseInt(cachedPage)
        if (!isNaN(cachedPageNum) && cachedPageNum >= 1 && cachedPageNum <= pages.value.length) {
          pageToSelect = cachedPageNum
          selectedPage.value = cachedPageNum
        }
      } else if (pageToSelect < 1 || pageToSelect > pages.value.length) {
        // 如果当前选中页面无效，则默认选择第一页
        pageToSelect = 1
        selectedPage.value = 1
      }
      
      await displayPage(pageToSelect)
    }
  } catch (err) {
    console.error('Error loading PDF data:', err)
    error.value = '加载PDF信息失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function noOcr() {
  try {
      const response = await Api.noOcr(fileId.value, selectedPage.value, {
        again: ocrAgain.value
      })
      if (response.status == 'success') {
        console.log(response.json())
      }
    } catch (err) {
      console.error('result:', err)
    }
}

async function againOcr() {
  try {
      ocrAgain.value = true
      generatePageContent()
    } catch (err) {
      console.error('result:', err)
    }
}

// 尝试从API获取该页面的OCR结果
async function fetchPageOcr(page) {
  try {
    ocrLoading.value = true
    ocrProgress.value = 0
    const response = await Api.ocr(fileId.value, page, {
      again: ocrAgain.value
    })
    console.log(response)
    ocrProgress.value = 100
    if (response.status == 'success') {
      return response.recognized_text || ''
    }
    ocrAgain.value = false
  } catch (err) {
    ocrAgain.value = false
    console.error('Error fetching OCR result:', err)
  } finally {
    ocrLoading.value = false
    ocrProgress.value = 0
  }
  return ''
}

// 为当前页面生成内容
function generatePageContent() {
  if (!fileId.value) return

  // 异步获取OCR结果
  fetchPageOcr(selectedPage.value).then(ocrText => {
    selectedPageInfo.value.ocr_text = ocrText
  })
}

// 批量OCR
async function batchOcr() {
  try {
    const page = selectedPage.value
    const totalToProcess = Math.min(10, pages.value.length - page + 1)

    batchOcrProgress.value = { current: 0, total: totalToProcess }

    for (let i = page; i < page + totalToProcess; i++) {
      let ocrText = await fetchPageOcr(i)
      if (ocrText) {
        pages.value[i].ocr_text = ocrText
      }
      batchOcrProgress.value.current = i - page + 1
    }

    batchOcrProgress.value = { current: 0, total: 0 }
  } catch (err) {
    console.error('result:', err)
    batchOcrProgress.value = { current: 0, total: 0 }
  }
}

// 滚动到选中页面的缩略图
function scrollToSelectedPage() {
  if (!pagesContainerRef.value) return
  
  // 延迟执行，确保DOM已经更新
  setTimeout(() => {
    const selectedPageElement = document.querySelector('.bg-blue-50.border-blue-200')
    if (selectedPageElement && pagesContainerRef.value) {
      pagesContainerRef.value.scrollTo({
        top: selectedPageElement.offsetTop - pagesContainerRef.value.offsetTop - 20,
        behavior: 'smooth'
      })
    }
  }, 100)
}

// 显示页面图片
async function displayPage(pageNumber) {
  console.log(pageNumber)
  const page = pages.value.find(p => p.index === pageNumber)
  if (!page) {
    return
  }

  // 更新选中页面信息
  selectedPageInfo.value = page
  if (!page.ocr_text) {
    selectedPageInfo.value.ocr_text = ' '
  }
  // 滚动到选中页面的缩略图
  scrollToSelectedPage()
}

function select(p) {
  selectedPage.value = p
  
  // 将当前页面信息存入本地缓存
  if (fileId.value) {
    const cacheKey = `file_${fileId.value}_page`
    localStorage.setItem(cacheKey, p.toString())
  }
}

// 放大按钮事件
function handleZoomIn() {
  if (previewSectionRef.value) {
    previewSectionRef.value.handleZoomIn()
  }
}

// 缩小按钮事件
function handleZoomOut() {
  if (previewSectionRef.value) {
    previewSectionRef.value.handleZoomOut()
  }
}

watch(selectedPage, async (p) => {
  await displayPage(p)
})

onMounted(async () => {
  await loadPdfData()
  
  // 添加键盘事件监听器
  document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  const src = route.query.src
  if (src?.startsWith('blob:')) URL.revokeObjectURL(src)
  
  // 移除键盘事件监听器
  document.removeEventListener('keydown', handleKeyDown)
})

// 保存状态相关
const lastSaveTime = ref('')
const isSaving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')

// 保存内容到服务器
async function saveContentToFile() {
  if (!fileId.value) return

  isSaving.value = true
  saveSuccess.value = false
  saveError.value = ''

  try {
    const response = await Api.saveContent(fileId.value, selectedPage.value, {
      page_number: selectedPage.value,
      content: selectedPageInfo.value.ocr_text,
    })
    console.log(response)

    if (response.status != 'success') {
      throw new Error('保存失败')
    }

    saveSuccess.value = true
    lastSaveTime.value = new Date().toLocaleString('zh-CN')
    console.log('内容保存成功')
    
    // 3秒后重置保存成功状态
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (err) {
    console.error('Error saving content:', err)
    saveError.value = '保存失败，请稍后重试'
    // 3秒后重置错误状态
    setTimeout(() => {
      saveError.value = ''
    }, 3000)
  } finally {
    isSaving.value = false
  }
}

// 添加防抖函数
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

function replacePunctuation() {
  console.log(selectedPageInfo)

  if (!selectedPageInfo.value.ocr_text) return
  
  selectedPageInfo.value.ocr_text = selectedPageInfo.value.ocr_text
    .replace(/,\s*/g, '，')
    .replace(/\"/g, '”')
    .replace(/~/g, '～')
    .replace(/\(/g, '（')
    .replace(/\)/g, '）')
    .replace(/\?/g, '？')
    .replace(/:\s*/g, '：')
    .replace(/;\s*/g, '；')
    .replace(/!\s*/g, '！')
    .replace(/\s*“/g, '“')
    .replace(/”\s*/g, '”')
    .replace(/\./g, '。');
}

</script>

<template>
  <div class="container mx-auto p-4 flex-grow">
    
    <div class="flex flex-col md:flex-row bg-white rounded-xl shadow-lg overflow-hidden h-[800px]">
      <div class="flex h-full border-2 border-gray-200">
        <!-- 左侧导航区 -->
        <div class="w-3/20 fixed-height-column border-r p-2 border-gray-200 hide-scrollbar border-1 w-[220px]  h-[600px]">
          <!-- 标题栏 -->
          <div class="flex justify-between items-center">
            <!-- 跳转按钮 -->
            <button
              class="ml-2 bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-1 rounded text-sm"
              @click="$router.push('/files')"
            >
              <Icon icon="mdi:arrow-left" width="18" height="18" />
            </button>
          </div>
          <div class="border-b border-gray-200">
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-bold text-gray-800">{{ pdfData?.original_filename || '文档导航' }}</h2>
              <!-- 导出按钮 -->
              <div class="flex space-x-2">
                <button
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  @click="exportToFile"
                  title="导出为文本文件"
                >
                  导出 TXT
                </button>
                <button
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  @click="exportToMarkdown"
                  title="导出为 Markdown 文件"
                >
                  导出 MD
                </button>
              </div>
            </div>
          </div>
          <!-- 搜索与跳转 -->
          <div class="border-b border-gray-200">
            <div class="mb-4">
              <div class="relative">
                <span class="iconify absolute left-3 top-1/2 transform -translate-y-1/2" data-icon="mdi:magnify"
                  data-width="18"></span>
                <input
                  class="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:border-blue-600 focus:ring-1 focus:ring-blue-100"
                  placeholder="搜索文档内容" type="text" />
              </div>
            </div>
          </div>
          <!-- 缩略图列表 -->
          <div 
            class="h-full overflow-y-auto p-3" 
            ref="pagesContainerRef"
            @mouseenter="pagesListHasFocus = true"
            @mouseleave="pagesListHasFocus = false"
            tabindex="0"
          >
            <div v-if="loading" class="text-center py-8 text-gray-500">
              加载页面列表中...
            </div>
            <div v-else-if="error" class="text-center py-8 text-red-500">
              {{ error }}
            </div>
            <div v-else-if="pages.length === 0" class="text-center py-8 text-gray-500">
              没有页面数据
            </div>
            <div v-else class="space-y-3">
              <div 
                v-for="p in pages" 
                :key="p.index"
                :class="['bg-white border', 
                         selectedPage === p.index ? 'bg-blue-50 border-blue-200' : 'border-gray-200']"
                @click="select(p.index)"
              >
                <div class="items-center justify-center overflow-hidden">
                  <img 
                    :alt="`PDF document page ${p.index}`" 
                    class="object-contain hover:scale-105" 
                    :src="p.image_url" 
                    @error="e => { e.target.src = 'https://via.placeholder.com/120x160?text=Page+' + p.index }"
                  />
                </div>
                <div class="text-xs text-center">{{ p.index }}</div>
              </div>
            </div>
          </div>
        </div>
        <!-- 右侧区域 - 85% -->
        <div class="w-17/20 fixed-height-column flex">
          <!-- 左侧50% - 预览区 -->
          <div class="w-1/2 border-r border-gray-200 border-2 hide-scrollbar w-[640px] h-full">
            <!-- 预览工具栏 -->
            <div class="p-3 bg-gray-50 border-b border-gray-200 flex items-center">
              <div class="flex space-x-1">
                <button class="tool-btn" @click="handleZoomIn" :disabled="ocrLoading">
                  <span class="iconify mr-1" data-icon="mdi:magnify-plus-outline" data-width="18">放大</span>
                </button>
                <button class="tool-btn" @click="handleZoomOut" :disabled="ocrLoading">
                  <span class="iconify mr-1" data-icon="mdi:magnify-minus-outline" data-width="18">缩小</span>
                </button>
                <button class="tool-btn" @click="generatePageContent" :disabled="ocrLoading" :class="{ 'opacity-50 cursor-not-allowed': ocrLoading }">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">OCR</span>
                </button>
                <button class="tool-btn" @click="batchOcr" :disabled="ocrLoading || batchOcrProgress.total > 0" :class="{ 'opacity-50 cursor-not-allowed': ocrLoading || batchOcrProgress.total > 0 }">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">批量OCR</span>
                </button>
                <button class="tool-btn" @click="againOcr" :disabled="ocrLoading" :class="{ 'opacity-50 cursor-not-allowed': ocrLoading }">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">重新OCR</span>
                </button>
                <button class="tool-btn" @click="noOcr" :disabled="ocrLoading" :class="{ 'opacity-50 cursor-not-allowed': ocrLoading }">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">无需OCR</span>
                </button>
              </div>
              <div class="ml-auto text-sm text-gray-700">第 {{ selectedPage }} 页 ({{ pages.length }})</div>
              <!-- 快捷键帮助按钮 -->
              <button
                class="ml-2 text-gray-500 hover:text-gray-700"
                @click="showShortcutsModal = true"
                title="键盘快捷键"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <!-- OCR进度指示器 -->
              <div v-if="ocrLoading" class="ml-4 flex items-center">
                <svg class="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span class="ml-2 text-sm text-blue-600">OCR中... {{ ocrProgress }}%</span>
              </div>
              <!-- 批量OCR进度指示器 -->
              <div v-if="batchOcrProgress.total > 0" class="ml-4 flex items-center">
                <svg class="animate-spin h-5 w-5 text-green-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span class="ml-2 text-sm text-green-600">批量OCR: {{ batchOcrProgress.current }}/{{ batchOcrProgress.total }}</span>
              </div>
            </div>
            <!-- 预览内容 -->
            <PreviewSection
              ref="previewSectionRef"
              :image-url="selectedPageInfo.image_url"
              :alt-text="`第 ${selectedPage} 页`"
              class="h-full"
            ></PreviewSection>
          </div>
          <!-- 右侧50% - 编辑区 -->
          <div class="w-1/2">
            <!-- 编辑内容区 -->
            <div class="editor-content h-[760px] overflow-hidden">
              <QuillEditor
                v-model:content="selectedPageInfo.ocr_text"
                :options="editorOptions"
                ref="editorRef"
                contentType="text"
                style="height: 90%;"
              />
              <!-- <textarea v-text="selectedPageInfo.ocr_text" class="m-3 w-full h-[760px]" /> -->
            </div>
            <!-- 保存状态 -->
            <div class="bg-gray-50 border-t border-gray-200 flex items-center">
              <div class="text-sm">
                <span v-if="isSaving" class="text-yellow-600">保存中...</span>
                <span v-else-if="saveSuccess" class="text-green-600">保存成功！</span>
                <span v-else-if="saveError" class="text-red-600">{{ saveError }}</span>
                <span v-else-if="lastSaveTime" class="text-gray-500">自动保存于 {{ lastSaveTime }}</span>
                <span v-else class="text-gray-500">未保存</span>
              </div>
              <div class="ml-auto">
                <button 
                  class="bg-blue-600 text-white px-4 py-1 rounded-lg text-sm"
                  @click="replacePunctuation"
                >
                  处理标点
                </button>
                <button 
                  class="bg-blue-600 text-white px-4 py-1 m-1 rounded-lg text-sm"
                  :disabled="isSaving"
                  @click="saveContentToFile"
                >
                  {{ isSaving ? '保存中...' : '保存修改' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 键盘快捷键帮助弹窗 -->
    <div v-if="showShortcutsModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-96 max-h-[80vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-semibold">键盘快捷键</h2>
          <button
            @click="showShortcutsModal = false"
            class="text-gray-500 hover:text-gray-700"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">编辑操作</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">保存内容</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Ctrl + S</kbd>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">撤销</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Ctrl + Z</kbd>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">重做</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Ctrl + Y</kbd>
              </div>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">页面导航</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">上一页</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">↑</kbd>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">下一页</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">↓</kbd>
              </div>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">图片预览</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">放大</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Ctrl + 滚轮上</kbd>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">缩小</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Ctrl + 滚轮下</kbd>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">滚动</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">滚轮</kbd>
              </div>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">界面操作</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">显示快捷键</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Ctrl + ?</kbd>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">关闭弹窗</span>
                <kbd class="bg-gray-100 px-2 py-1 rounded">Esc</kbd>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 text-center">
          <button
            @click="showShortcutsModal = false"
            class="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
          >
            知道了
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
  
<style scoped>

  
</style>