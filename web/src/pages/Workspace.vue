<script setup>
import { onMounted, ref, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// 导入TUI Editor
import { VueEditor } from "vue3-editor";

const route = useRoute()
const fileId = ref(route.query.id || '')
const pdfData = ref(null)
const pages = ref([])
const selectedPage = ref(1)
const selectedPageInfo = ref({ocr_text: ""})
const mdContent = ref(``)
const previewContainer = ref(null)
const loading = ref(false)
const error = ref(null)
const ocrAgain = ref(false) // 是否重新OCR

// 图片缩放和拖动相关变量
const scale = ref(1) // 缩放比例
const translateX = ref(0) // 水平偏移量
const translateY = ref(0) // 垂直偏移量
const isDragging = ref(false) // 是否正在拖动
const startX = ref(0) // 拖动开始时的鼠标X坐标
const startY = ref(0) // 拖动开始时的鼠标Y坐标
const startTranslateX = ref(0) // 拖动开始时的水平偏移量
const startTranslateY = ref(0) // 拖动开始时的垂直偏移量

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

async function noOcr() {
  try {
      const response = await fetch(`http://127.0.0.1:8000/api/pdf/${fileId.value}/noocr/${selectedPage.value}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          again: ocrAgain.value
        })
      })
      if (response.ok) {
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
        },
        body: JSON.stringify({
          again: ocrAgain.value
        })
      })
      if (response.ok) {
        const pageData = await response.json()
        return pageData.recognized_text || ''
      }
      ocrAgain.value = false
    } catch (err) {
      ocrAgain.value = false
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
  
  // 重置缩放和偏移
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
  
  // 创建图片元素
  const img = document.createElement('img')
  img.alt = `第 ${pageNumber} 页`
  img.src = page.image_url
  img.style.maxWidth = '100%'
  img.style.maxHeight = '100%'
  img.style.objectFit = 'contain'
  img.style.transition = 'transform 0.1s ease'
  
  // 添加加载状态
  previewContainer.value.innerHTML = '<div class="text-gray-500">加载中...</div>'

  img.onload = () => {
    // 清空容器并添加图片
    previewContainer.value.innerHTML = ''
    previewContainer.value.appendChild(img)
    
    // 获取预览容器
    const container = previewContainer.value
    
    // 鼠标按下事件 - 开始拖动
    const handleMouseDown = (e) => {
      isDragging.value = true
      startX.value = e.clientX
      startY.value = e.clientY
      startTranslateX.value = translateX.value
      startTranslateY.value = translateY.value
      container.style.cursor = 'grabbing'
    }
    
    // 鼠标移动事件 - 拖动中
    const handleMouseMove = (e) => {
      if (!isDragging.value) return
      
      const deltaX = e.clientX - startX.value
      const deltaY = e.clientY - startY.value
      
      translateX.value = startTranslateX.value + deltaX
      translateY.value = startTranslateY.value + deltaY
      
      // 应用变换
      img.style.transform = `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`
    }
    
    // 鼠标释放事件 - 结束拖动
    const handleMouseUp = () => {
      isDragging.value = false
      container.style.cursor = 'grab'
    }
    
    // 鼠标滚轮事件 - 缩放和滚动
    const handleWheel = (e) => {
      // 如果按下Ctrl键，则进行缩放
      if (e.ctrlKey) {
        e.preventDefault()
        
        // 计算缩放比例
        const zoomSpeed = 0.1
        const delta = e.deltaY > 0 ? -zoomSpeed : zoomSpeed
        const newScale = Math.max(0.1, Math.min(5, scale.value + delta))
        
        // 计算缩放中心
        const rect = container.getBoundingClientRect()
        const mouseX = e.clientX - rect.left
        const mouseY = e.clientY - rect.top
        
        // 计算缩放前后的鼠标位置差异
        const prevScale = scale.value
        scale.value = newScale
        
        // 调整偏移量，使缩放中心保持不变
        translateX.value += mouseX * (prevScale - newScale) / prevScale
        translateY.value += mouseY * (prevScale - newScale) / prevScale
        
        // 应用变换
        img.style.transform = `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`
      }
      // 否则，允许默认滚动行为
    }
    
    // 放大按钮事件
    const handleZoomIn = () => {
      scale.value = Math.min(5, scale.value + 0.1)
      img.style.transform = `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`
    }
    
    // 缩小按钮事件
    const handleZoomOut = () => {
      scale.value = Math.max(0.1, scale.value - 0.1)
      img.style.transform = `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`
    }
    
    // 绑定事件
    img.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    container.addEventListener('wheel', handleWheel, { passive: false })
    
    // 查找并绑定工具栏按钮事件
    const zoomInBtn = container.closest('.preview-section').querySelector('.zoom-in-btn')
    const zoomOutBtn = container.closest('.preview-section').querySelector('.zoom-out-btn')
    if (zoomInBtn) zoomInBtn.addEventListener('click', handleZoomIn)
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', handleZoomOut)
    
    // 组件卸载时解绑事件
    const cleanup = () => {
      img.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      container.removeEventListener('wheel', handleWheel)
      if (zoomInBtn) zoomInBtn.removeEventListener('click', handleZoomIn)
      if (zoomOutBtn) zoomOutBtn.removeEventListener('click', handleZoomOut)
    }
    
    // 监听组件卸载事件
    onBeforeUnmount(cleanup)
  }

  img.onerror = () => {
    previewContainer.value.innerHTML = '<div class="text-red-500">图片加载失败</div>'
  }
}

function select(p) {
  selectedPage.value = p
}

watch(selectedPage, async (p) => {
  await displayPage(p)
})

onMounted(async () => {
  await loadPdfData()
})

onBeforeUnmount(() => {
  const src = route.query.src
  if (src?.startsWith('blob:')) URL.revokeObjectURL(src)
})

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
    const response = await fetch(`http://127.0.0.1:8000/api/pdf/content/${fileId.value}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        page_number: selectedPage.value,
        content: selectedPageInfo.value.ocr_text,
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
  <div class="container mx-auto p-4 flex-grow">
    
    <div class="flex flex-col md:flex-row bg-white rounded-xl shadow-lg overflow-hidden h-[800px]">
      <div class="flex h-full">
        <!-- 左侧导航区 -->
        <div class="w-3/20 fixed-height-column border-r border-gray-200 hide-scrollbar border-1 w-[220px]">
          <!-- 标题栏 -->
          <div class="border-b border-gray-200">
            <h2 class="text-xl font-bold text-gray-800">{{ pdfData?.original_filename || '文档导航' }}</h2>
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
          <div class="w-1/2 border-r border-gray-200 border-2 hide-scrollbar w-[640px] h-[600px]">
            <!-- 预览工具栏 -->
            <div class="p-3 bg-gray-50 border-b border-gray-200 flex items-center">
              <div class="flex space-x-1">
                <button class="tool-btn zoom-in-btn">
                  <span class="iconify mr-1" data-icon="mdi:magnify-plus-outline" data-width="18">放大</span>
                </button>
                <button class="tool-btn zoom-out-btn">
                  <span class="iconify mr-1" data-icon="mdi:magnify-minus-outline" data-width="18">缩小</span>
                </button>
                <button class="tool-btn" @click="generatePageContent">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">OCR</span>
                </button>
                <button class="tool-btn" @click="againOcr">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">重新OCR</span>
                </button>
                <button class="tool-btn" @click="noOcr">
                  <span class="iconify mr-1" data-icon="mdi:fullscreen" data-width="18">无需OCR</span>
                </button>
              </div>
              <div class="ml-auto text-sm text-gray-700">第 {{ selectedPage }} 页 ({{ pages.length }})</div>
            </div>
            <!-- 预览内容 -->
            <div class="preview-section bg-gray-50">
              <div class="items-center justify-center" ref="previewContainer">
                <!-- 预览内容将通过JavaScript动态加载 -->
              </div>
            </div>
          </div>
          <!-- 右侧50% - 编辑区 -->
          <div class="w-1/2">
            <!-- 编辑内容区 -->
            <div class="editor-content h-[765px] overflow-hidden">
              <VueEditor
                v-model="selectedPageInfo.ocr_text"
                :editorToolbar="[]"
                ref="editorRef"
                style="height: 90%;"
              />
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
              <button 
                class="ml-auto bg-blue-600 text-white px-4 py-1 rounded-lg text-sm"
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
</template>
  
<style scoped>

  
</style>