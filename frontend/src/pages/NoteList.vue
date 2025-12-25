<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'

const router = useRouter()

// 响应式数据
const notes = ref([]) // 笔记列表
const loading = ref(false) // 加载状态
const error = ref(null) // 错误信息
const total = ref(0) // 总数
const showCreateModal = ref(false) // 创建笔记弹窗显示状态
const noteTitle = ref('') // 笔记标题
const noteSubmitting = ref(false) // 笔记提交状态
const noteTitleInput = ref(null) // 笔记标题输入框引用

// 监听弹窗显示状态，自动聚焦输入框
watch(showCreateModal, (newVal) => {
  if (newVal) {
    nextTick(() => {
      if (noteTitleInput.value) {
        noteTitleInput.value.focus()
      }
    })
  }
})

// 页面加载时获取笔记列表
onMounted(() => {
  loadNotes()
})

// 获取笔记列表
async function loadNotes() {
  loading.value = true
  error.value = null
  try {
    const data = await request('/api/notes', 'GET')
    notes.value = data || []
    total.value = notes.value.length
  } catch (err) {
    console.error('Error loading notes:', err)
    error.value = '加载笔记失败，请刷新页面重试'
    notes.value = []
  } finally {
    loading.value = false
  }
}

// 进入笔记详情页
function goToNote(noteId) {
  router.push({ name: 'note', query: { id: noteId } })
}

// 创建新笔记
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
    
    // 创建成功，刷新笔记列表
    await loadNotes()
    
    // 关闭弹窗并重置表单
    showCreateModal.value = false
    noteTitle.value = ''
    
    alert('笔记创建成功')
    
    // 创建成功后直接跳转到笔记详情页
    if (data.id) {
      goToNote(data.id)
    }
  } catch (err) {
    console.error('Error creating note:', err)
    alert('创建笔记失败，请稍后重试')
  } finally {
    noteSubmitting.value = false
  }
}

// 删除笔记
async function deleteNote(note) {
  if (!confirm(`确定要删除笔记"${note.title}"吗？此操作不可恢复。`)) {
    return
  }
  
  try {
    await request(`/api/notes/${note.id}`, 'DELETE')
    
    // 从列表中移除已删除的笔记
    const index = notes.value.findIndex(n => n.id === note.id)
    if (index > -1) {
      notes.value.splice(index, 1)
      total.value = notes.value.length
    }
    
    alert('笔记删除成功')
  } catch (err) {
    console.error('Error deleting note:', err)
    alert('删除笔记失败，请稍后重试')
  }
}

// 格式化日期
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

// 获取笔记内容预览
function getContentPreview(content, maxLength = 100) {
  if (!content) return '暂无内容'
  return content.length > maxLength ? content.substring(0, maxLength) + '...' : content
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <div class="max-w-6xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-semibold">笔记管理</h1>
        <div class="flex items-center space-x-4">
          <div v-if="total > 0" class="text-sm text-gray-500">
            共 {{ total }} 个笔记
          </div>
          <button
            @click="showCreateModal = true"
            class="bg-blue-500 text-white rounded-md px-4 py-2 hover:bg-blue-600"
          >
            新增笔记
          </button>
          <button
            @click="router.push({name:'files'})"
            class="bg-gray-100 text-gray-700 rounded-md px-4 py-2 hover:bg-gray-200"
          >
            返回文件管理
          </button>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 text-left text-sm text-gray-600">
            <tr>
              <th class="p-4 w-1/3">标题</th>
              <th class="p-4 w-2/5">内容预览</th>
              <th class="p-4 w-1/6">创建时间</th>
              <th class="p-4 w-1/6">更新时间</th>
              <th class="p-4 w-1/6">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="text-center">
              <td colspan="5" class="p-8 text-gray-500">加载中...</td>
            </tr>
            <tr v-else-if="error" class="text-center">
              <td colspan="5" class="p-8 text-red-500">{{ error }}</td>
            </tr>
            <tr v-else-if="notes.length === 0" class="text-center">
              <td colspan="5" class="p-8 text-gray-500">暂无笔记，请创建一个新笔记</td>
            </tr>
            <tr 
              v-for="note in notes" 
              :key="note.id" 
              class="border-t hover:bg-gray-50 transition-colors cursor-pointer"
              @click="goToNote(note.id)"
            >
              <td class="p-4">
                <div class="font-medium text-gray-900">{{ note.title }}</div>
              </td>
              <td class="p-4">
                <div class="text-sm text-gray-600 line-clamp-2">
                  {{ getContentPreview(note.content) }}
                </div>
              </td>
              <td class="p-4 text-sm text-gray-500">
                {{ formatDate(note.created_at) }}
              </td>
              <td class="p-4 text-sm text-gray-500">
                {{ formatDate(note.updated_at) }}
              </td>
              <td class="p-4">
                <div class="flex items-center gap-2">
                  <button
                    @click.stop="goToNote(note.id)"
                    class="bg-blue-100 text-blue-700 rounded-md px-3 py-1 text-sm hover:bg-blue-200 transition-colors"
                  >
                    编辑
                  </button>
                  <button
                    @click.stop="deleteNote(note)"
                    class="bg-red-100 text-red-700 rounded-md px-3 py-1 text-sm hover:bg-red-200 transition-colors"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 创建笔记弹窗 -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-96">
        <h3 class="text-lg font-medium mb-4">新增笔记</h3>
        <input
          v-model="noteTitle"
          type="text"
          placeholder="请输入笔记标题"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
          @keyup.enter="createNote"
          ref="noteTitleInput"
        />
        <div class="flex justify-end space-x-2">
          <button
            @click="showCreateModal = false; noteTitle = ''"
            class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            @click="createNote"
            :disabled="noteSubmitting || !noteTitle.trim()"
            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-blue-300"
          >
            {{ noteSubmitting ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>