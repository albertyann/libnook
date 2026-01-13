<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
// import { Api } from '../api/api'

const router = useRouter()
const files = ref([])
const filteredFiles = ref([]) // 过滤后的文件列表
const fileInput = ref(null)
const uploading = ref(false)
const loading = ref(false)
const error = ref(null)
const total = ref(0)
const isDragging = ref(false) // 拖放状态
const dragCounter = ref(0) // 拖放计数器，用于处理子元素拖放事件
const showNoteModal = ref(false) // 笔记弹窗显示状态
const noteTitle = ref('') // 笔记标题
const noteSubmitting = ref(false) // 笔记提交状态
const noteTitleInput = ref(null) // 笔记标题输入框引用

// 搜索和过滤
const searchQuery = ref('') // 搜索关键词
const statusFilter = ref('all') // 状态过滤器: all, pending, processing, images_generated, completed, error

// 监听弹窗显示状态，自动聚焦输入框
watch(showNoteModal, (newVal) => {
  if (newVal) {
    nextTick(() => {
      if (noteTitleInput.value) {
        noteTitleInput.value.focus()
      }
    })
  }
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await request('/api/file/list', 'GET')
    files.value = data.files || []
    total.value = data.total || 0
    applyFilters() // 应用搜索和过滤
  } catch (err) {
    console.error('Error loading files:', err)
    error.value = '加载文件失败，请稍后重试'
    files.value = []
    filteredFiles.value = []
  } finally {
    loading.value = false
  }
}

// 应用搜索和过滤
function applyFilters() {
  filteredFiles.value = files.value.filter(file => {
    // 应用搜索关键词
    const matchesSearch = searchQuery.value === '' ||
      file.original_filename.toLowerCase().includes(searchQuery.value.toLowerCase())

    // 应用状态过滤
    const matchesStatus = statusFilter.value === 'all' ||
      file.status === statusFilter.value

    return matchesSearch && matchesStatus
  })
}

// 监听搜索和过滤条件变化
watch([searchQuery, statusFilter], () => {
  applyFilters()
})

function goWorkspace(id) {
  // 确保跳转到工作区页面，使用query参数传递文件ID
  router.push({ name: 'workspace', query: { id } })
}

function previewFile(id) {
  const file = files.value.find(f => f.id === id)
  if (file) {
    // 使用环境变量构建预览URL
    const baseURL = import.meta.env.VITE_APP_BASE_API || 'http://127.0.0.1:8000'
    const previewUrl = `${baseURL}/api/file/${id}`
    window.open(previewUrl, '_blank', 'width=900,height=800,toolbar=no,menubar=no,scrollbars=yes,resizable=yes')
  }
}

async function del(id) {
  const file = files.value.find(f => f.id === id)
  if (!file) return

  const confirmed = confirm(`确定要删除文件"${file.original_filename}"吗？\n\n此操作将删除文件及其所有OCR结果，且无法恢复。`)

  if (!confirmed) return

  try {
    await request(`/api/file/${id}`, 'DELETE')
    load() // 删除成功后重新加载列表
  } catch (err) {
    console.error('Error deleting file:', err)
    alert('删除文件失败，请稍后重试')
  }
}

function triggerFileUpload() {
  fileInput.value.click()
}

// 拖放事件处理函数
// 创建笔记
async function createNote() {
  if (!noteTitle.value.trim()) {
    alert('请输入笔记标题')
    return
  }
  
  noteSubmitting.value = true
  try {
    const data = await request('/api/notes', 'POST', {
      title: noteTitle.value.trim()
    })
    
    // 创建成功
    alert('笔记创建成功')
    showNoteModal.value = false
    noteTitle.value = ''
    
    // 可以在这里跳转到笔记编辑页面或刷新笔记列表
    console.log('创建的笔记:', data)
  } catch (err) {
    console.error('Error creating note:', err)
    alert('创建笔记失败，请稍后重试')
  } finally {
    noteSubmitting.value = false
  }
}

function handleDragEnter(e) {
  e.preventDefault()
  e.stopPropagation()
  dragCounter.value++
  if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
    isDragging.value = true
  }
}

function handleDragLeave(e) {
  e.preventDefault()
  e.stopPropagation()
  dragCounter.value--
  if (dragCounter.value === 0) {
    isDragging.value = false
  }
}

function handleDragOver(e) {
  e.preventDefault()
  e.stopPropagation()
  return false
}

function handleDrop(e) {
  e.preventDefault()
  e.stopPropagation()
  isDragging.value = false
  dragCounter.value = 0
  
  const files = e.dataTransfer.files
  if (files && files.length > 0) {
    handleDroppedFiles(files)
  }
  return false
}

// 处理拖放的文件
async function handleDroppedFiles(files) {
  // 只处理第一个文件
  const file = files[0]
  if (!file) return
  
  // 检查文件类型是否为PDF
  // if (!file.type.match('application/pdf')) {
  //   alert('请上传PDF文件')
  //   return
  // }
  
  // 检查文件大小，限制为100MB
  const maxSize = 100 * 1024 * 1024 // 100MB
  if (file.size > maxSize) {
    alert('文件大小不能超过100MB')
    return
  }
  
  // 设置上传状态
  uploading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    // 使用axios上传文件，需要设置Content-Type为multipart/form-data
    await request('/api/file/upload', 'POST', formData, {
      'Content-Type': 'multipart/form-data'
    })
    
    await load() // 重新加载文件列表
    console.log('文件上传成功:', file.name)
  } catch (err) {
    console.error('文件上传失败:', err)
    alert('文件上传失败，请重试')
  } finally {
    // 重置上传状态
    uploading.value = false
  }
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  
  // 检查文件类型是否为PDF
  // if (!file.type.match('application/pdf')) {
  //   alert('请上传PDF文件')
  //   return
  // }
  
  // 检查文件大小，限制为100MB
  const maxSize = 100 * 1024 * 1024 // 100MB
  if (file.size > maxSize) {
    alert('文件大小不能超过100MB')
    return
  }
  
  // 设置上传状态
  uploading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    // 使用axios上传文件，需要设置Content-Type为multipart/form-data
    await request('/api/file/upload', 'POST', formData, {
      'Content-Type': 'multipart/form-data'
    })
    
    await load() // 重新加载文件列表
    console.log('文件上传成功:', file.name)
  } catch (err) {
    console.error('文件上传失败:', err)
    alert('文件上传失败，请重试')
  } finally {
    // 重置上传状态
    uploading.value = false
  }
  
  // 重置文件输入，允许重新选择相同的文件
  event.target.value = ''
}

function formatDate(ts) {
  if (!ts) return '-'
  const d = new Date(ts)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusText(status) {
  const statusMap = {
    'pending': '等待处理',
    'processing': '处理中',
    'images_generated': '图片已生成',
    'completed': '已完成',
    'error': '处理失败'
  }
  return statusMap[status] || status
}

function getStatusBadgeClass(status) {
  const classMap = {
    'pending': 'badge-warning',
    'processing': 'badge-info',
    'images_generated': 'badge-info',
    'completed': 'badge-success',
    'error': 'badge-danger'
  }
  return classMap[status] || 'badge-gray'
}

function getProgress(file) {
  if (file.total_pages && file.total_pages > 0) {
    return Math.round((file.pages_processed / file.total_pages) * 100)
  }
  return 0
}

onMounted(load)
</script>

<template>
  <div 
    class="page-container p-6"
    :class="{ 'dragging': isDragging }"
    @dragenter="handleDragEnter"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <div class="max-w-6xl mx-auto">
      <div class="page-header">
          <h1 class="page-title">文件管理</h1>
          <div class="flex items-center gap-4">
            <div v-if="total > 0" class="text-sm text-gray-500">
              共 {{ total }} 个文件 ({{ filteredFiles.length }} 个显示)
            </div>
            <div class="flex gap-2">
              <button class="btn-primary" @click="triggerFileUpload" :disabled="uploading">
                {{ uploading ? '上传中...' : '上传' }}
              </button>
              <input type="file" ref="fileInput" @change="handleFileUpload" accept=".pdf" class="hidden" />
              <button class="btn-primary" @click="showNoteModal = true">新增笔记</button>
              <button class="btn-secondary" @click="router.push({name:'notes'})">笔记管理</button>
              <button class="btn-secondary" @click="router.push({name:'settings'})">OCR 配置</button>
              <button class="btn-secondary" @click="router.push({name:'home'})">返回首页</button>
            </div>
          </div>
      </div>

      <!-- 搜索和过滤栏 -->
      <div class="mb-4 card p-4">
        <div class="flex gap-4">
          <!-- 搜索框 -->
          <div class="flex-1">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索文件名..."
              class="input-field"
            />
          </div>
          <!-- 状态过滤器 -->
          <div class="w-48">
            <select
              v-model="statusFilter"
              class="input-select"
            >
              <option value="all">全部状态</option>
              <option value="pending">等待处理</option>
              <option value="processing">处理中</option>
              <option value="images_generated">图片已生成</option>
              <option value="completed">已完成</option>
              <option value="error">处理失败</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 拖放提示区域 -->
      <div 
        v-if="isDragging" 
        class="fixed inset-0 bg-indigo-50 bg-opacity-90 z-50 flex items-center justify-center pointer-events-none"
      >
        <div class="card shadow-xl p-8 text-center drag-over">
          <div class="text-6xl mb-4">📄</div>
          <h3 class="text-xl font-semibold mb-2">拖放文件到这里上传</h3>
          <p class="text-gray-600">支持 PDF 文件，最大 100MB</p>
        </div>
      </div>

      <div class="card table-container">
        <table class="w-full">
          <thead class="table-header">
            <tr>
              <th class="table-cell">文件名</th>
              <th class="table-cell w-24">页数</th>
              <th class="table-cell w-40">上传时间</th>
              <th class="table-cell w-24">识别</th>
              <th class="table-cell w-24">校对</th>
              <th class="table-cell w-48">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="text-center">
              <td colspan="6" class="table-cell text-gray-500">加载中...</td>
            </tr>
            <tr v-else-if="error" class="text-center">
              <td colspan="6" class="table-cell text-red-500">{{ error }}</td>
            </tr>
            <tr v-for="f in filteredFiles" :key="f.id" class="table-row">
              <td class="table-cell">
                <div class="font-medium">{{ f.original_filename }}</div>
                <div class="mt-1">
                  <span :class="['badge', getStatusBadgeClass(f.status)]">{{ getStatusText(f.status) }}</span>
                </div>
                <div v-if="f.error_message" class="text-xs text-red-500 mt-2">
                  {{ f.error_message }}
                </div>
              </td>
              <td class="table-cell text-sm">{{ f.total_pages || '-' }}</td>
              <td class="table-cell text-sm">{{ formatDate(f.created_at) }}</td>
              <td class="table-cell text-sm">{{ getProgress(f) }}%</td>
              <td class="table-cell text-sm">0%</td>
              <td class="table-cell">
                <div class="flex items-center gap-2">
                  <button class="btn-secondary px-2 py-1" @click="previewFile(f.id)" title="预览">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </button>
                  <button class="btn-primary px-2 py-1" @click="goWorkspace(f.id)" title="编辑">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.536L16.732 3.732z" />
                    </svg>
                  </button>
                  <button class="btn-danger px-2 py-1" @click="del(f.id)" title="删除">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!filteredFiles.length">
              <td colspan="6" class="table-cell text-center text-gray-500">暂无文件，请先上传 PDF</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- 笔记弹窗 -->
  <div v-if="showNoteModal" class="modal-overlay">
    <div class="modal-content">
      <h3 class="text-lg font-medium mb-4">新增笔记</h3>
      <input
        v-model="noteTitle"
        type="text"
        placeholder="请输入笔记标题"
        class="input-field mb-4"
        @keyup.enter="createNote"
        ref="noteTitleInput"
      />
      <div class="flex justify-end gap-2">
        <button
          @click="showNoteModal = false; noteTitle = ''"
          class="btn-secondary"
        >
          取消
        </button>
        <button
          @click="createNote"
          :disabled="noteSubmitting || !noteTitle.trim()"
          class="btn-primary"
        >
          {{ noteSubmitting ? '创建中...' : '创建' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dragging {
  background-color: #e0f2fe;
}
</style>

