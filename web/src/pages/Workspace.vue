<script setup>
import { onMounted, ref, watch, onBeforeUnmount, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// 导入TUI Editor
import { VueEditor } from "vue3-editor";

const route = useRoute()
const router = useRouter()
const fileId = ref(route.query.id || '')
const isPreviewMode = ref(route.query.preview === 'true')
const pdfData = ref(null)
const pages = ref([])
const selectedPage = ref(1)
const selectedPageInfo = ref({ocr_text: ""})
const mdContent = ref(``)
const isMobile = ref(window.innerWidth < 768) // 是否为移动设备
const previewContainer = ref(null)
const gridEl = ref(null)
const isResizing = ref(!isPreviewMode.value)
const topHeight = ref(420)
const HANDLE_H = 8
const MIN_TOP = 180
const MIN_BOTTOM = 160
const loading = ref(false)
const error = ref(null)
const sidePanelWidth = ref(isMobile.value ? 200 : 300) // 默认侧边栏宽度
const sidebarCollapsed = ref(isMobile.value) // 移动设备默认收起侧边栏

// 图片拖动和缩放相关状态
const isDragging = ref(false)
const startX = ref(0)
const startY = ref(0)
const translateX = ref(0)
const translateY = ref(0)
const scale = ref(1)

const mdInput = ref(null)

const editorRef = ref(null)

// 响应式处理
function handleResize() {
  const newIsMobile = window.innerWidth < 768
  isMobile.value = newIsMobile
  // 移动设备上默认收起侧边栏
  if (newIsMobile) {
    sidebarCollapsed.value = true
  } else {
    sidebarCollapsed.value = false
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
    const response = await fetch(`http://127.0.0.1:8000/api/pdf/${fileId.value}/info`)
    if (!response.ok) {
      throw new Error('Failed to fetch PDF data')
    }

    const data = await response.json()
    pdfData.value = data
    console.log(data.pages)

    // 根据API返回的数据构建页面列表
    if (data.pages && Array.isArray(data.pages)) {
      pages.value = data.pages.map(page => ({
        index: page.page_number,
        image_url: `http://127.0.0.1:8000/api/pdf/${fileId.value}/image/${page.page_number}`,
        thumb_url: page.thumb_url || page.image_url,
        ocr_text: page.ocr_text,
        width: page.width,
        height: page.height
      }))
    } else {
      // 如果没有pages数组，尝试从total_pages生成
      const totalPages = data.total_pages || 0
      pages.value = Array.from({ length: totalPages }, (_, i) => ({
        index: i + 1,
        image_url: `http://127.0.0.1:8000/api/pdf/${fileId.value}/image/${i + 1}`,
        thumb_url: `http://127.0.0.1:8000/api/pdf/${fileId.value}/image/${i + 1}`,
        ocr_text: "",
        width: null,
        height: null
      }))
    }

    // 显示第一页
    if (pages.value.length > 0) {
      await displayPage(selectedPage.value)
    }
  } catch (err) {
    console.error('Error loading PDF data:', err)
    error.value = '加载PDF信息失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 为当前页面生成内容
function generatePageContent() {
  if (!fileId.value) return

  // 尝试从API获取该页面的OCR结果
  async function fetchPageOcr() {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/pdf/${fileId.value}/ocr/${selectedPage.value}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        const pageData = await response.json()
        return pageData.recognized_text || ''
      }
    } catch (err) {
      console.error('Error fetching OCR result:', err)
    }
    return ''
  }

  // 异步获取OCR结果
  fetchPageOcr().then(ocrText => {
    selectedPageInfo.value.ocr_text = ocrText
  })
}

// 显示页面图片
async function displayPage(pageNumber) {
  if (!previewContainer.value) return

  const page = pages.value.find(p => p.index === pageNumber)
  if (!page || !page.image_url) {
    previewContainer.value.innerHTML = '<div class="text-gray-500">页面图片不存在</div>'
    return
  }

  // 更新选中页面信息
  selectedPageInfo.value = page

  // 重置位置和缩放
  translateX.value = 0
  translateY.value = 0
  // scale.value = 1
  
  // 创建图片元素
  const img = document.createElement('img')
  img.alt = `第 ${pageNumber} 页`
  img.src = page.image_url
  
  // 设置图片样式
  img.style.position = 'absolute'
  img.style.transition = 'transform 0.1s ease'
  img.style.cursor = 'grab'
  
  // 添加拖动事件
  img.addEventListener('mousedown', startDrag)
  img.addEventListener('touchstart', startDrag)
  
  // 添加缩放事件
  img.addEventListener('wheel', (e) => {
    if (e.ctrlKey) {
      e.preventDefault()
      handleWheel(e)
    }
  }, { passive: false })
  img.addEventListener('touchmove', handleTouchZoom, { passive: false })
  
  // 添加加载状态
  previewContainer.value.innerHTML = '<div class="text-gray-500">加载中...</div>'

  img.onload = () => {
    previewContainer.value.innerHTML = ''
    previewContainer.value.appendChild(img)
    
    // 居中图片
    const containerWidth = previewContainer.value.clientWidth
    const containerHeight = previewContainer.value.clientHeight
    const imgWidth = img.offsetWidth
    const imgHeight = img.offsetHeight
    
    translateX.value = (containerWidth - imgWidth) / 2
    translateY.value = (containerHeight - imgHeight) / 2
    
    updateImageTransform(img)
  }

  img.onerror = () => {
    previewContainer.value.innerHTML = '<div class="text-red-500">图片加载失败</div>'
  }
  
  // 重置全局事件监听
  function cleanupEvents() {
    document.removeEventListener('mousemove', drag)
    document.removeEventListener('mouseup', endDrag)
    document.removeEventListener('touchmove', drag)
    document.removeEventListener('touchend', endDrag)
  }
  
  // 开始拖动
  function startDrag(e) {
    e.preventDefault()
    isDragging.value = true
    
    // 移除其他图片的事件监听
    const allImages = previewContainer.value.querySelectorAll('img')
    allImages.forEach(img => {
      if (img !== e.currentTarget) {
        img.removeEventListener('mousedown', startDrag)
        img.removeEventListener('touchstart', startDrag)
      }
    })
    
    const img = e.currentTarget
    img.style.cursor = 'grabbing'
    
    if (e.type === 'mousedown') {
      startX.value = e.clientX - translateX.value
      startY.value = e.clientY - translateY.value
      
      document.addEventListener('mousemove', drag)
      document.addEventListener('mouseup', endDrag)
    } else if (e.type === 'touchstart') {
      const touch = e.touches[0]
      startX.value = touch.clientX - translateX.value
      startY.value = touch.clientY - translateY.value
      
      document.addEventListener('touchmove', drag)
      document.addEventListener('touchend', endDrag)
    }
  }
  
  // 拖动中
  function drag(e) {
    if (!isDragging.value) return
    e.preventDefault()
    
    const img = previewContainer.value.querySelector('img')
    if (!img) return
    
    let clientX, clientY
    if (e.type === 'mousemove') {
      clientX = e.clientX
      clientY = e.clientY
    } else if (e.type === 'touchmove') {
      const touch = e.touches[0]
      clientX = touch.clientX
      clientY = touch.clientY
    }
    
    translateX.value = clientX - startX.value
    translateY.value = clientY - startY.value
    
    updateImageTransform(img)
  }
  
  // 结束拖动
  function endDrag() {
    isDragging.value = false
    const img = previewContainer.value.querySelector('img')
    if (img) {
      img.style.cursor = 'grab'
    }
    // 清理触摸距离，确保下次触摸操作能正确初始化
    handleTouchZoom.touchDistance = null
    cleanupEvents()
  }
  
  // 处理鼠标滚轮缩放
  function handleWheel(e) {
    e.preventDefault()
    
    const img = e.currentTarget
    const container = previewContainer.value
    const rect = container.getBoundingClientRect()
    
    // 计算鼠标在容器中的相对位置
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top
    
    // 计算缩放前的鼠标相对于图片中心的位置
    const imgX = translateX.value + (img.offsetWidth * scale.value) / 2
    const imgY = translateY.value + (img.offsetHeight * scale.value) / 2
    const relX = mouseX - imgX
    const relY = mouseY - imgY
    
    // 设置缩放因子
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1
    const newScale = scale.value * scaleFactor
    
    // 限制缩放范围
    if (newScale < 0.5 || newScale > 5) return
    
    // 更新缩放值
    scale.value = newScale
    
    // 调整位置，使缩放以鼠标位置为中心
    translateX.value += relX * (scaleFactor - 1)
    translateY.value += relY * (scaleFactor - 1)
    
    updateImageTransform(img)
  }
  
  // 处理触控缩放
  function handleTouchZoom(e) {
    // 如果只有一个触摸点，则不处理缩放
    if (e.touches.length !== 2 || isDragging.value) return
    
    e.preventDefault()
    
    const img = e.currentTarget
    const container = previewContainer.value
    const touch1 = e.touches[0]
    const touch2 = e.touches[1]
    
    // 计算两个触摸点之间的距离
    const distance = Math.hypot(
      touch2.clientX - touch1.clientX,
      touch2.clientY - touch1.clientY
    )
    
    // 使用闭包变量保存初始距离，避免使用this导致的上下文问题
    if (!handleTouchZoom.touchDistance) {
      handleTouchZoom.touchDistance = distance
      return
    }
    
    // 计算缩放比例
    const scaleFactor = distance / handleTouchZoom.touchDistance
    const newScale = scale.value * scaleFactor
    
    // 限制缩放范围
    if (newScale >= 0.5 && newScale <= 5) {
      // 计算缩放中心点
      const containerRect = container.getBoundingClientRect()
      const centerX = (touch1.clientX + touch2.clientX) / 2 - containerRect.left
      const centerY = (touch1.clientY + touch2.clientY) / 2 - containerRect.top
      
      // 计算缩放前中心点相对于图片的位置
      const imgX = translateX.value + (img.offsetWidth * scale.value) / 2
      const imgY = translateY.value + (img.offsetHeight * scale.value) / 2
      const relX = centerX - imgX
      const relY = centerY - imgY
      
      // 更新缩放值
      scale.value = newScale
      
      // 调整位置，使缩放以双指中心为中心点
      translateX.value += relX * (scaleFactor - 1)
      translateY.value += relY * (scaleFactor - 1)
      
      updateImageTransform(img)
    }
    
    // 更新触摸距离
    handleTouchZoom.touchDistance = distance
  }
  
  // 更新图片变换
  function updateImageTransform(img) {
    img.style.transform = `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`
  }
  
  // 清理所有事件监听器
  function cleanupAllEvents(img) {
    if (!img) return
    
    img.removeEventListener('mousedown', startDrag)
    img.removeEventListener('touchstart', startDrag)
    img.removeEventListener('wheel', handleWheel)
    img.removeEventListener('touchmove', handleTouchZoom)
    // 清理触摸距离状态
    handleTouchZoom.touchDistance = null
  }
  
  // 在页面切换时清理之前的图片事件
  const oldImg = previewContainer.value.querySelector('img')
  if (oldImg) {
    cleanupAllEvents(oldImg)
  }
}

// 切换侧边栏显示状态
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 组件卸载时清理事件监听器
onBeforeUnmount(() => {
  const img = previewContainer.value?.querySelector('img')
  if (img) {
    img.removeEventListener('mousedown', startDrag)
    img.removeEventListener('touchstart', startDrag)
    img.removeEventListener('wheel', handleWheel)
    img.removeEventListener('touchmove', handleTouchZoom)
  }
  
  document.removeEventListener('mousemove', drag)
  document.removeEventListener('mouseup', endDrag)
  document.removeEventListener('touchmove', drag)
  document.removeEventListener('touchend', endDrag)
})

function select(p) {
  selectedPage.value = p
  // console.log(selectedPage.value)
  // 切换页面时生成相应的页面内容
  // generatePageContent()
  
  // 移动设备上选择页面后自动关闭侧边栏
  if (isMobile.value) {
    sidebarCollapsed.value = true
  }
}

watch(selectedPage, async (p) => {
  await displayPage(p)
  // 页面切换后延迟一点生成内容
  setTimeout(() => {
    // generatePageContent()
  }, 300)
})

onMounted(async () => {
  await loadPdfData()
  if (gridEl.value) {
    const h = gridEl.value.clientHeight
    topHeight.value = Math.max(MIN_TOP, Math.min(Math.round(h * 0.6), h - MIN_BOTTOM))
  }
  
  // 添加窗口调整事件监听
  handleResize()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  const src = route.query.src
  if (src?.startsWith('blob:')) URL.revokeObjectURL(src)
  
  // 组件卸载时移除事件监听
  window.removeEventListener('resize', handleResize)
})

function onResizeStart(e) {
  e.preventDefault()
  isResizing.value = true
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
  window.addEventListener('touchmove', onResizeMove)
  window.addEventListener('touchend', onResizeEnd)
}

function onResizeMove(e) {
  if (!isResizing.value || !gridEl.value) return
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  const rect = gridEl.value.getBoundingClientRect()
  const h = gridEl.value.clientHeight
  let y = clientY - rect.top
  y = Math.max(MIN_TOP, Math.min(y, h - MIN_BOTTOM))
  topHeight.value = y - HANDLE_H / 2
}

async function onResizeEnd() {
  if (!isResizing.value) return
  isResizing.value = false
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeEnd)
  window.removeEventListener('touchmove', onResizeMove)
  window.removeEventListener('touchend', onResizeEnd)
  await nextTick()
  // 调整大小时重新渲染当前页面
  await displayPage(selectedPage.value)
}

function chooseMd() {
  mdInput.value?.click()
}

async function onMdFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = async () => {
    mdContent.value = String(reader.result || '')
    // 编辑器内容更新后保存到服务器
    await saveContentToFile()
  }
  reader.readAsText(file)
}

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
    const response = await fetch(`http://127.0.0.1:8000/api/pdf/${fileId.value}/content`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content: mdContent.value
      })
    })

    if (!response.ok) {
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

// 创建防抖保存函数
const debouncedSave = debounce(saveContentToFile, 2000)

// 当编辑器内容变化时自动保存
function handleEditorChange({ markdown }) {
  // 使用防抖函数避免频繁保存
  mdContent.value = markdown
  debouncedSave()
}
</script>

<template>
    <!-- 侧边栏切换按钮 - 移动端 -->
    <button 
      class="fixed top-4 left-4 z-50 bg-white p-2 rounded-full shadow-md lg:hidden"
      @click="toggleSidebar"
    >
      <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
      </svg>
    </button>
    
    <div class="w-full max-w-7xl mx-auto px-4 py-4">
      <div class="bg-white rounded-xl shadow-lg flex">
        <!-- 左侧导航区 -->
        <div 
          class="border-r border-gray-200 transition-all duration-300 ease-in-out"
          :style="{ width: sidebarCollapsed && isMobile ? 0 : '280px', minWidth: sidebarCollapsed && isMobile ? 0 : '280px', overflow: sidebarCollapsed && isMobile ? 'hidden' : 'visible' }"
        >
          <!-- 标题栏 -->
          <div class="p-5 border-b border-gray-200">
            <h2 class="text-xl font-bold text-gray-800">{{ pdfData?.original_filename || '文档导航' }}</h2>
            <p class="text-sm text-gray-500 mt-1">{{ pages.length }} 页</p>
          </div>
          <!-- 搜索与跳转 -->
          <div class="p-4 border-b border-gray-200">
            <div class="mb-4">
              <div class="relative">
                <span class="iconify absolute left-3 top-1/2 transform -translate-y-1/2" data-icon="mdi:magnify"
                  data-width="18"></span>
                <input
                  class="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:border-blue-600 focus:ring-1 focus:ring-blue-100"
                  placeholder="搜索文档内容" type="text" />
              </div>
            </div>
            <div>
              <label class="text-sm font-medium text-gray-700 mb-1 block">跳转至</label>
              <div class="flex">
                <input
                  class="w-20 border border-gray-200 rounded-l-lg py-2 px-3 text-sm focus:border-blue-600 focus:ring-1 focus:ring-blue-100"
                  placeholder="页码" type="text" />
                <button
                  class="bg-blue-600 text-white rounded-r-lg px-4 py-2 text-sm hover:bg-blue-700 transition-colors">跳转</button>
              </div>
            </div>
          </div>
          <!-- 缩略图列表 -->
          <div class="h-full overflow-y-auto p-3">
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
                :class="['bg-white border rounded-lg cursor-pointer hover:shadow-md transition-all', 
                         selectedPage === p.index ? 'bg-blue-50 border-blue-300 ring-1 ring-blue-200' : 'border-gray-200']"
                @click="select(p.index)"
              >
                <div class="items-center justify-center overflow-hidden">
                  <img 
                    :alt="`PDF document page ${p.index}`" 
                    class="object-contain transition-transform hover:scale-105" 
                    :src="p.image_url" 
                    @error="e => { e.target.src = 'https://via.placeholder.com/120x160?text=Page+' + p.index }"
                  />
                </div>
                <div class="text-xs text-gray-500 mt-1 text-right">{{ p.index }}</div>
              </div>
            </div>
          </div>
        </div>
      
        <!-- 右侧主工作区 -->
        <div class="column justify-between">
          <!-- 预览区 -->
          <div class="border-r-2 md-4 border-gray-200">
            <!-- 预览工具栏 -->
            <div class="p-3 bg-gray-50 border-b border-gray-200 flex items-center">
              <div class="flex space-x-1">
                <button class="tool-btn">
                  <span class="iconify mr-1" data-icon="mdi:magnify-plus-outline" data-width="18"></span> 放大
                </button>
                <button class="tool-btn">
                  <span class="iconify mr-1" data-icon="mdi:magnify-minus-outline" data-width="18"></span> 缩小
                </button>
                <button class="tool-btn">
                  <span class="iconify mr-1" data-icon="mdi:rotate-right" data-width="18"></span> 旋转
                </button>
                <button class="tool-btn">
                  <span class="iconify mr-1" data-icon="mdi:arrow-expand-horizontal" data-width="18"></span> 适应宽度
                </button>
                <button class="tool-btn">
                  <span class="iconify mr-1" data-icon="mdi:arrow-expand-vertical" data-width="18"></span> 适应高度
                </button>
                <button class="tool-btn">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18"></span> 全屏
                </button>
                <button class="tool-btn" @click="generatePageContent">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18"></span> OCR
                </button>
              </div>
              <div class="ml-auto text-sm text-gray-700">第 4 页 (100%)</div>
            </div>
            <!-- 预览内容 -->
            <div class="preview-section bg-gray-50">
              <div class="items-center justify-center p-4" ref="previewContainer">
                <!-- 预览内容将通过JavaScript动态加载 -->
              </div>
            </div>
          </div>
          <!-- 编辑区 -->
          <div class="editor-section md-5">
            <!-- 编辑内容区 -->
            <div class="flex-1 flex">
              <!-- 文本编辑区 -->
              <div class="editor-content flex-1">
                <!-- <div v-html="selectedPageInfo.ocr_text"></div> -->
                <VueEditor
                  v-model="selectedPageInfo.ocr_text"
                  ref="editorRef"
                />
              </div>
              <!-- 批注列表 -->
              <!-- <div class="w-[280px] border-l border-gray-200">
                <div class="p-3 border-b border-gray-200">
                  <h3 class="font-medium text-gray-800">批注列表</h3>
                </div>
                <div class="p-2 overflow-y-auto" style="max-height: calc(100% - 40px);">
                  <div class="border border-gray-200 rounded-lg p-3 mb-2">
                    <div class="flex justify-between items-start">
                      <span class="font-medium text-sm">第4页内容修改</span>
                      <span class="text-xs text-gray-500">12:05</span>
                    </div>
                    <p class="text-sm mt-1">将"高效"改为"快速"更符合上下文语义</p>
                    <div class="flex mt-2">
                      <span class="text-xs px-2 py-0.5 bg-red-500 text-white rounded-full">已处理</span>
                    </div>
                  </div>
                  <div class="border border-gray-200 rounded-lg p-3 mb-2 bg-blue-50">
                    <div class="flex justify-between items-start">
                      <span class="font-medium text-sm">术语统一建议</span>
                      <span class="text-xs text-gray-500">11:48</span>
                    </div>
                    <p class="text-sm mt-1">第2段和第5段使用的术语不一致：一处使用"PDF"，另一处使用"pdf"，建议统一</p>
                    <div class="flex mt-2">
                      <span class="text-xs px-2 py-0.5 bg-yellow-500 text-white rounded-full">待处理</span>
                    </div>
                  </div>
                </div>
              </div> -->
            </div>
            <!-- 保存状态 -->
            <div class="p-2 bg-gray-50 border-t border-gray-200 flex items-center px-4">
              <div class="text-sm">
                <span v-if="isSaving" class="text-yellow-600">保存中...</span>
                <span v-else-if="saveSuccess" class="text-green-600">保存成功！</span>
                <span v-else-if="saveError" class="text-red-600">{{ saveError }}</span>
                <span v-else-if="lastSaveTime" class="text-gray-500">自动保存于 {{ lastSaveTime }}</span>
                <span v-else class="text-gray-500">未保存</span>
              </div>
              <button 
                class="ml-auto bg-blue-600 text-white px-4 py-1 rounded-lg text-sm hover:bg-blue-700 transition-colors"
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
  </template>
  
  <style scoped>
  /* 全局全屏高度布局 */
  body, html {
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }
  
  /* 主容器样式 */
  .w-full {
    padding: 0;
    margin: 0;
  }
  .h-full {
    height: 176vh;
  }
  
  .max-w-7xl {
    padding: 1rem;
    margin: 0;
    width: 100%;
    max-width: 100%;
  }

  .preview-section {
    height: 65%;
    min-height: 400px;
    flex: 0 0 auto;
  }
  
  /* 编辑器内容区样式 */
  .editor-content {
    transition: border-color 0.2s ease;
  }
  
  .editor-content:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
  }
  
  /* 工具按钮样式 */
  .tool-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6px 12px;
    border: 1px solid #e5e7eb;
    background-color: #ffffff;
    border-radius: 6px;
    color: #374151;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 14px;
  }
  
  .tool-btn:hover {
    background-color: #f3f4f6;
    border-color: #d1d5db;
  }
  
  .tool-btn:active {
    background-color: #e5e7eb;
    transform: translateY(1px);
  }
  
  /* 美化滚动条 */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  
  ::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
  }
  
  ::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
  }
  
  ::-webkit-scrollbar-thumb:hover {
    background: #a1a1a1;
  }
  
  /* 加载状态动画 */
  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }
  
  .text-center.py-8 {
    animation: pulse 1.5s ease-in-out infinite;
  }
  
  /* 批注列表样式 */
  .w-\[280px\].border-l {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  /* 缩略图卡片样式增强 */
  /* 预览区域样式 */
  .preview-section {
    overflow: hidden;
    position: relative;
  }

  /* 预览容器样式 */
  .items-center.justify-center.p-4 {
    height: 100%;
    width: 100%;
    position: relative;
  }

  /* 缩略图卡片样式增强 */
  .thumb-card {
    transition: all 0.2s ease;
    border: 2px solid transparent;
  }
  
  .thumb-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  
  .thumb-card.selectedPage {
    border-color: #3b82f6;
  }
  
  /* 图片加载失败占位符样式 */
  .aspect-\[3\/4\] img[src*="placeholder"] {
    background-color: #f3f4f6;
    color: #6b7280;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
  }
  
  /* 响应式布局样式 */
  /* 移动端适配 (小屏幕) */
  @media (max-width: 640px) {
    .max-w-7xl {
      padding: 0.5rem;
    }
    
    .bg-white.rounded-xl {
      height: calc(100% - 1rem);
      max-height: calc(100vh - 1rem);
    }
    
    .editor-section {
      height: 45%;
    }
    
    /* 移动端侧边栏隐藏效果 */
    .border-r.flex.flex-col {
      position: fixed;
      z-index: 40;
      top: 0;
      left: 0;
      height: 100vh;
      background: white;
      box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
      transition: transform 0.3s ease;
    }
    
    .sidebar-collapsed .border-r.flex.flex-col {
      transform: translateX(-100%);
    }
    
    /* 移动端工具栏简化 */
    .tool-btn span {
      display: none;
    }
    
    /* 移动端批注列表隐藏 */
    .w-\[280px\].border-l {
      display: none;
    }
    
    /* 缩略图调整 */
    .thumb-card {
      min-height: 120px;
      max-height: 160px;
    }
  }
  
  /* 平板设备适配 (中等屏幕) */
  @media (min-width: 641px) and (max-width: 1024px) {
    .editor-section {
      height: 30%;
    }
    
    /* 平板侧边栏宽度调整 */
    .border-r.flex.flex-col {
      width: 240px !important;
      min-width: 240px !important;
    }
    
    /* 批注列表宽度调整 */
    .w-\[280px\].border-l {
      width: 240px !important;
    }
  }
  
  /* 大屏幕设备优化 */
  @media (min-width: 1025px) {
    .border-r.flex.flex-col {
      width: 300px !important;
      min-width: 300px !important;
    }
  }
  </style>