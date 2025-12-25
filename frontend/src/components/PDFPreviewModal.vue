<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url'

// 设置PDF.js工作器
GlobalWorkerOptions.workerSrc = workerUrl

// 组件属性
const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  pdfUrl: {
    type: String,
    required: true
  },
  title: {
    type: String,
    default: 'PDF预览'
  }
})

// 组件事件
const emit = defineEmits(['close'])

// 响应式数据
const pdfDoc = ref(null)
const pages = ref([])
const currentPage = ref(1)
const totalPages = ref(0)
const loading = ref(false)
const error = ref('')
const scale = ref(1.0)
const containerRef = ref(null)
const canvasRef = ref(null)
const isFullscreen = ref(false)

// 监听visible变化
watch(() => props.visible, (newValue) => {
  if (newValue) {
    setTimeout(() => {
      loadPdf()
    }, 100)
    document.body.style.overflow = 'hidden'
  } else {
    cleanup()
    document.body.style.overflow = ''
  }
})

// 监听pdfUrl变化，重新加载PDF
watch(() => props.pdfUrl, () => {
  if (props.visible) {
    loadPdf()
  }
})

// 加载PDF文档
async function loadPdf() {
  if (!props.pdfUrl) return
  
  loading.value = true
  error.value = ''
  pdfDoc.value = null
  pages.value = []
  currentPage.value = 1
  
  try {
    const loadingTask = getDocument("https://mozilla.github.io/pdf.js/web/compressed.tracemonkey-pldi-09.pdf")
    pdfDoc.value = 'https://mozilla.github.io/pdf.js/web/compressed.tracemonkey-pldi-09.pdf';//await loadingTask.promise
    totalPages.value = pdfDoc.value.numPages
    await renderCurrentPage()
    // 预加载前几页的缩略图
    await preloadThumbnails()
  } catch (err) {
    console.error('加载PDF失败:', err)
    error.value = 'PDF加载失败，请重试'
  } finally {
    loading.value = false
  }
}

// 渲染当前页面
async function renderCurrentPage() {
  if (!pdfDoc.value || !canvasRef.value || !containerRef.value) return
  
  try {
    const page = await pdfDoc.value.getPage(currentPage.value)
    const canvas = canvasRef.value
    const container = containerRef.value
    
    // 计算适合容器的缩放比例
    const viewport = page.getViewport({ scale })
    const containerWidth = container.clientWidth
    const containerHeight = container.clientHeight
    
    let newScale = scale.value
    // 如果页面大于容器，自动缩放以适应
    if (viewport.width > containerWidth || viewport.height > containerHeight) {
      const widthScale = containerWidth / viewport.width
      const heightScale = containerHeight / viewport.height
      newScale = Math.min(widthScale, heightScale, 1.5) // 最大缩放1.5倍
      viewport.width = viewport.width * newScale
      viewport.height = viewport.height * newScale
    }
    
    // 设置canvas尺寸
    canvas.width = viewport.width
    canvas.height = viewport.height
    
    // 渲染页面
    const ctx = canvas.getContext('2d')
    await page.render({
      canvasContext: ctx,
      viewport
    }).promise
    
  } catch (err) {
    console.error('渲染页面失败:', err)
    error.value = '页面渲染失败'
  }
}

// 预加载缩略图
async function preloadThumbnails() {
  if (!pdfDoc.value) return
  
  const preloadCount = Math.min(5, totalPages.value)
  for (let i = 1; i <= preloadCount; i++) {
    try {
      const page = await pdfDoc.value.getPage(i)
      const viewport = page.getViewport({ scale: 0.1 })
      const canvas = document.createElement('canvas')
      canvas.width = viewport.width
      canvas.height = viewport.height
      const ctx = canvas.getContext('2d')
      await page.render({
        canvasContext: ctx,
        viewport
      }).promise
      // 存储缩略图数据
      pages.value[i - 1] = {
        index: i,
        thumb: canvas.toDataURL()
      }
    } catch (err) {
      console.error(`预加载第${i}页缩略图失败:`, err)
    }
  }
}

// 上一页
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    renderCurrentPage()
  }
}

// 下一页
function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    renderCurrentPage()
  }
}

// 跳转到指定页
function goToPage(pageNum) {
  if (pageNum >= 1 && pageNum <= totalPages.value) {
    currentPage.value = pageNum
    renderCurrentPage()
  }
}

// 缩放控制
function zoomIn() {
  scale.value = Math.min(scale.value + 0.1, 3.0) // 最大3倍
  renderCurrentPage()
}

function zoomOut() {
  scale.value = Math.max(scale.value - 0.1, 0.1) // 最小0.1倍
  renderCurrentPage()
}

function resetZoom() {
  scale.value = 1.0
  renderCurrentPage()
}

// 切换全屏
function toggleFullscreen() {
  if (!isFullscreen.value) {
    const el = containerRef.value
    if (el.requestFullscreen) {
      el.requestFullscreen()
    } else if (el.webkitRequestFullscreen) {
      el.webkitRequestFullscreen()
    } else if (el.msRequestFullscreen) {
      el.msRequestFullscreen()
    }
    isFullscreen.value = true
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen()
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen()
    }
    isFullscreen.value = false
  }
}

// 处理ESC键关闭弹窗
function handleKeyDown(e) {
  if (e.key === 'Escape' && props.visible) {
    closeModal()
  }
}

// 关闭弹窗
function closeModal() {
  emit('close')
}

// 清理资源
function cleanup() {
  if (pdfDoc.value) {
    pdfDoc.value.destroy()
  }
  pdfDoc.value = null
  pages.value = []
  error.value = ''
}

// 生命周期钩子
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
  // 监听全屏状态变化
  document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement
  })
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement
  })
  cleanup()
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-75">
        <div class="relative w-full max-w-7xl max-h-[95vh] bg-white rounded-lg flex flex-col">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between p-4 border-b">
            <h3 class="text-lg font-medium">{{ title }}</h3>
            <div class="flex items-center gap-3">
              <!-- 缩放控制 -->
              <div class="flex items-center border rounded-md overflow-hidden">
                <button 
                  @click="zoomOut"
                  class="px-2 py-1 text-sm hover:bg-gray-100 transition-colors"
                  aria-label="缩小"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16M4 12h16" />
                  </svg>
                </button>
                <button 
                  @click="resetZoom"
                  class="px-2 py-1 text-sm border-x hover:bg-gray-100 transition-colors"
                  aria-label="重置缩放"
                >
                  100%
                </button>
                <button 
                  @click="zoomIn"
                  class="px-2 py-1 text-sm hover:bg-gray-100 transition-colors"
                  aria-label="放大"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                </button>
              </div>
              
              <!-- 全屏按钮 -->
              <button 
                @click="toggleFullscreen"
                class="p-2 rounded-full hover:bg-gray-100 transition-colors"
                aria-label="全屏"
              >
                <svg v-if="!isFullscreen" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16zM17 12l-5 3m0 0l-5-3m5 3V6" />
                </svg>
              </button>
              
              <!-- 关闭按钮 -->
              <button 
                @click="closeModal"
                class="p-2 rounded-full hover:bg-gray-100 transition-colors"
                aria-label="关闭"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="loading" class="flex-1 flex items-center justify-center">
            <div class="flex flex-col items-center">
              <svg class="animate-spin -ml-1 mr-3 h-8 w-8 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p class="text-gray-500">加载中...</p>
            </div>
          </div>
          
          <!-- 错误状态 -->
          <div v-else-if="error" class="flex-1 flex items-center justify-center p-4">
            <div class="text-center">
              <svg class="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="mt-3 text-gray-600">{{ error }}</p>
              <button @click="loadPdf" class="mt-3 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors">
                重试
              </button>
            </div>
          </div>
          
          <!-- PDF内容 -->
          <div v-else ref="containerRef" class="flex-1 overflow-auto bg-gray-50 relative">
            <canvas ref="canvasRef" class="block mx-auto my-4 shadow-sm"></canvas>
          </div>
          
          <!-- 分页控制 -->
          <div v-if="totalPages > 0 && !loading && !error" class="p-4 border-t flex items-center justify-between">
            <div class="flex items-center gap-2">
              <button 
                @click="prevPage" 
                :disabled="currentPage === 1"
                class="px-3 py-1 border rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                上一页
              </button>
              <button 
                @click="nextPage" 
                :disabled="currentPage === totalPages"
                class="px-3 py-1 border rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                下一页
              </button>
            </div>
            
            <div class="text-sm text-gray-600">
              第 {{ currentPage }} / {{ totalPages }} 页
            </div>
            
            <div class="flex items-center gap-2">
              <input 
                type="number" 
                v-model.number="currentPage"
                :min="1" 
                :max="totalPages"
                class="w-16 px-2 py-1 border rounded-md text-center"
                @change="goToPage(currentPage)"
                @keydown.enter="goToPage(currentPage)"
              />
              <span class="text-sm text-gray-500">of {{ totalPages }}</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 模态框过渡动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.9);
}
</style>