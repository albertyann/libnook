<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const files = ref([])
const fileInput = ref(null)
const uploading = ref(false)
const loading = ref(false)
const error = ref(null)
const total = ref(0)

async function load() {
  loading.value = true
  error.value = null
  try {
    const response = await fetch('http://127.0.0.1:8000/api/pdf/files')
    if (!response.ok) {
      throw new Error('Failed to fetch files')
    }
    const data = await response.json()
    files.value = data.files || []
    total.value = data.total || 0
  } catch (err) {
    console.error('Error loading files:', err)
    error.value = '加载文件失败，请稍后重试'
    files.value = []
  } finally {
    loading.value = false
  }
}

function goWorkspace(id) {
  // 确保跳转到工作区页面，使用query参数传递文件ID
  router.push({ name: 'workspace', query: { id } })
}

function previewFile(id) {
  const file = files.value.find(f => f.id === id)
  if (file) {
    // 使用文件ID构建预览URL
    const previewUrl = `http://127.0.0.1:8000/api/pdf/${id}`
    window.open(previewUrl, '_blank', 'width=900,height=800,toolbar=no,menubar=no,scrollbars=yes,resizable=yes')
  }
}

async function del(id) {
  try {
    const response = await fetch(`http://127.0.0.1:8000/api/pdf/${id}`, {
      method: 'DELETE'
    })
    if (!response.ok) {
      throw new Error('Failed to delete file')
    }
    load() // 删除成功后重新加载列表
  } catch (err) {
    console.error('Error deleting file:', err)
    alert('删除文件失败，请稍后重试')
  }
}

function triggerFileUpload() {
  fileInput.value.click()
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  
  // 检查文件类型是否为PDF
  if (!file.type.match('application/pdf')) {
    alert('请上传PDF文件')
    return
  }
  
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
    
    const response = await fetch('http://127.0.0.1:8000/api/pdf/upload', {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error('文件上传失败')
    }
    
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

function getProgress(file) {
  if (file.total_pages && file.total_pages > 0) {
    return Math.round((file.pages_processed / file.total_pages) * 100)
  }
  return 0
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <div class="max-w-5xl mx-auto">
      <div class="flex items-center justify-between mb-4">
          <h1 class="text-2xl font-semibold">文件管理</h1>
          <div v-if="total > 0" class="text-sm text-gray-500">
            共 {{ total }} 个文件
          </div>
        <div class="space-x-2">
          <button class="rounded-md bg-green-500 text-white px-3 py-1" @click="triggerFileUpload" :disabled="uploading">
            {{ uploading ? '上传中...' : '上传PDF' }}
          </button>
          <input type="file" ref="fileInput" @change="handleFileUpload" accept=".pdf" class="hidden" />
          <button class="rounded-md bg-gray-100 px-3 py-1" @click="router.push({name:'settings'})">OCR 配置</button>
          <button class="rounded-md bg-gray-100 px-3 py-1" @click="router.push({name:'home'})">返回首页</button>
        </div>
      </div>

      <div class="bg-white border rounded-xl shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 text-left text-sm text-gray-600">
            <tr>
              <th class="p-3">文件名</th>
              <th class="p-3 w-24">页数</th>
              <th class="p-3 w-40">上传时间</th>
              <th class="p-3 w-30">识别进度</th>
              <th class="p-3 w-30">校对进度</th>
              <th class="p-3 w-68">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="text-center">
              <td colspan="6" class="p-6 text-gray-500">加载中...</td>
            </tr>
            <tr v-else-if="error" class="text-center">
              <td colspan="6" class="p-6 text-red-500">{{ error }}</td>
            </tr>
            <tr v-for="f in files" :key="f.id" class="border-t hover:bg-gray-50 transition-colors">
              <td class="p-3">
                <div class="font-medium">{{ f.original_filename }}</div>
                <div class="text-xs text-gray-500">
                  状态: {{ getStatusText(f.status) }}
                </div>
              </td>
              <td class="p-3 text-sm">{{ f.total_pages || '-' }}</td>
              <td class="p-3 text-sm">{{ formatDate(f.created_at) }}</td>
              <td class="p-3">
                <div class="mt-1 text-xs">{{ getProgress(f) }}%</div>
              </td>
              <td class="p-3">
                <div class="mt-1 text-xs">0%</div>
              </td>
              <td class="p-3">
                <div class="flex items-center gap-2 flex-wrap">
                  <button class="rounded-md bg-blue-500 text-white px-3 py-1 text-sm hover:bg-blue-600 transition-colors" @click="previewFile(f.id)">预览</button>
                  <button class="rounded-md bg-indigo-600 text-white px-3 py-1 text-sm hover:bg-indigo-700 transition-colors" @click="goWorkspace(f.id)">校对</button>
                  <button class="rounded-md bg-gray-100 px-3 py-1 text-sm hover:bg-gray-200 transition-colors" @click="del(f.id)">删除</button>
                  <div v-if="f.error_message" class="text-xs text-red-500 mt-1">
                    {{ f.error_message }}
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="!files.length">
              <td colspan="6" class="p-6 text-center text-gray-500">暂无文件，请先上传 PDF</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

