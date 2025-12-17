<script setup>
import { onMounted, ref, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
// 导入TUI Editor
import { VueEditor } from "vue3-editor";

// 导入PreviewSection组件
import PreviewSection from '../components/PreviewSection.vue';

const route = useRoute()
const fileId = ref(route.query.id || '')
const pdfData = ref(null)
const pages = ref([])
const selectedPage = ref(1)
const selectedPageInfo = ref({ocr_text: ""})
const loading = ref(false)
const error = ref(null)
const ocrAgain = ref(false) // 是否重新OCR

// 预览组件引用
const previewSectionRef = ref(null)

// 左侧页面列表容器引用
const pagesContainerRef = ref(null)

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
  const page = pages.value.find(p => p.index === pageNumber)
  if (!page) {
    return
  }

  // 更新选中页面信息
  selectedPageInfo.value = page
  
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
})

onBeforeUnmount(() => {
  const src = route.query.src
  if (src?.startsWith('blob:')) URL.revokeObjectURL(src)
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

function replacePunctuation() {
  console.log(selectedPageInfo)

  if (!selectedPageInfo.value.ocr_text) return
  
  selectedPageInfo.value.ocr_text = selectedPageInfo.value.ocr_text
    .replace(/,\s*/g, '，')
    .replace(/\"/g, '”')
    .replace(/~/g, '～')
    .replace(/\(/g, '（')
    .replace(/\)/g, '）')
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
          <div class="h-full overflow-y-auto p-3" ref="pagesContainerRef">
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
                <button class="tool-btn" @click="handleZoomIn">
                  <span class="iconify mr-1" data-icon="mdi:magnify-plus-outline" data-width="18">放大</span>
                </button>
                <button class="tool-btn" @click="handleZoomOut">
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
  </div>
</template>
  
<style scoped>

  
</style>