<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import request from '../api/request'
import * as versionHistory from '../utils/versionHistory'

const router = useRouter()
const route = useRoute()

// 响应式数据
const notes = ref([]) // 笔记列表
const filteredNotes = ref([]) // 过滤后的笔记列表
const selectedNote = ref(null) // 当前选中的笔记
const noteContent = ref('') // 笔记内容
const loading = ref(false) // 加载状态
const saving = ref(false) // 保存状态
const showCreateModal = ref(false) // 创建笔记弹窗显示状态
const noteTitle = ref('') // 笔记标题
const noteTitleInput = ref(null) // 笔记标题输入框引用

// 搜索和过滤
const searchQuery = ref('') // 搜索关键词
const showExportMenu = ref(false) // 显示导出菜单

// 版本历史
const showVersionHistory = ref(false) // 显示版本历史
const versions = ref([]) // 版本列表
const selectedVersion = ref(null) // 选中的版本

// 对话相关数据
const chatMessages = ref([]) // 对话消息列表
const chatInput = ref('') // 对话输入框内容
const chatSending = ref(false) // 对话发送状态

// 工作结果相关数据
const workResults = ref([]) // 工作结果列表
const selectedWorkResult = ref(null) // 当前选中的工作结果

// 页面加载时获取笔记列表
onMounted(() => {
  loadNotes()
  
  // 如果URL中有ID参数，则选中对应该ID的笔记
  if (route.query.id) {
    // 等待笔记列表加载完成后再选择
    watch(notes, (newNotes) => {
      if (newNotes.length > 0) {
        const noteToSelect = newNotes.find(n => n.id == route.query.id)
        if (noteToSelect) {
          selectNote(noteToSelect)
        }
      }
    }, { immediate: true })
  }
})

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

// 获取笔记列表
async function loadNotes() {
  loading.value = true
  try {
    const data = await request('/api/notes', 'GET')
    notes.value = data
    applySearch() // 应用搜索
    if (notes.value.length > 0 && !selectedNote.value) {
      selectNote(notes.value[0])
    }
  } catch (err) {
    console.error('Error loading notes:', err)
    alert('加载笔记失败，请刷新页面重试')
  } finally {
    loading.value = false
  }
}

// 应用搜索
function applySearch() {
  if (!searchQuery.value) {
    filteredNotes.value = notes.value
  } else {
    const query = searchQuery.value.toLowerCase()
    filteredNotes.value = notes.value.filter(note =>
      note.title.toLowerCase().includes(query) ||
      (note.content && note.content.toLowerCase().includes(query))
    )
  }
}

// 监听搜索关键词变化
watch(searchQuery, () => {
  applySearch()
})

// 选择笔记
async function selectNote(note) {
  if (selectedNote.value && selectedNote.value.id === note.id) {
    return
  }
  
  selectedNote.value = note
  loading.value = true
  
  try {
    const data = await request(`/api/notes/${note.id}`, 'GET')
    noteContent.value = data.content || ''
    
    // 加载该笔记的对话历史
    loadChatHistory(note.id)
    // 加载该笔记的工作结果
    loadWorkResults(note.id)
  } catch (err) {
    console.error('Error loading note content:', err)
    alert('加载笔记内容失败')
  } finally {
    loading.value = false
  }
}

// 加载对话历史
async function loadChatHistory(noteId) {
  try {
    const data = await request(`/api/notes/${noteId}/chat`, 'GET')
    chatMessages.value = data || []
  } catch (err) {
    console.error('Error loading chat history:', err)
    chatMessages.value = []
  }
}

// 加载工作结果
async function loadWorkResults(noteId) {
  try {
    const data = await request(`/api/notes/${noteId}/results`, 'GET')
    workResults.value = data || []
  } catch (err) {
    console.error('Error loading work results:', err)
    workResults.value = []
  }
}

// 导出笔记为文本文件
async function exportNoteToText() {
  if (!selectedNote.value) return

  try {
    let content = `笔记标题: ${selectedNote.value.title}\n`
    content += `导出时间: ${new Date().toLocaleString('zh-CN')}\n`
    content += `更新时间: ${selectedNote.value.updated_at || '未知'}\n`
    content += '\n' + '='.repeat(50) + '\n\n'
    content += noteContent.value

    // 创建 Blob 并下载
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${selectedNote.value.title}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    // 显示成功提示
    if (window.toastManager) {
      window.toastManager.show({ message: '笔记导出成功！', type: 'success', duration: 3000, title: '导出完成' })
    }
  } catch (error) {
    console.error('导出失败:', error)
    if (window.toastManager) {
      window.toastManager.show({ message: '导出失败，请稍后重试', type: 'error', duration: 3000, title: '导出错误' })
    }
  }
}

// 导出笔记为 Markdown 文件
async function exportNoteToMarkdown() {
  if (!selectedNote.value) return

  try {
    let content = `# ${selectedNote.value.title}\n\n`
    content += `*更新时间: ${selectedNote.value.updated_at || '未知'}*\n\n`
    content += '---\n\n'
    content += noteContent.value

    // 创建 Blob 并下载
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${selectedNote.value.title}.md`
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

// 导出笔记为 Word 文档（使用 HTML + content-type）
async function exportNoteToWord() {
  if (!selectedNote.value) return

  try {
    // 简单的 HTML 格式，可以被 Word 打开
    let content = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>${selectedNote.value.title}</title>
<style>
body { font-family: 'Microsoft YaHei', Arial, sans-serif; }
h1 { color: #2E86C1; }
</style>
</head>
<body>
<h1>${selectedNote.value.title}</h1>
<p><strong>更新时间:</strong> ${selectedNote.value.updated_at || '未知'}</p>
<hr/>
${noteContent.value.replace(/\n/g, '<br/>')}
</body>
</html>`

    // 创建 Blob 并下载
    const blob = new Blob([content], {
      type: 'application/msword',
      charset: 'utf-8'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${selectedNote.value.title}.doc`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    if (window.toastManager) {
      window.toastManager.show({ message: 'Word 文档导出成功！', type: 'success', duration: 3000, title: '导出完成' })
    }
  } catch (error) {
    console.error('导出失败:', error)
    if (window.toastManager) {
      window.toastManager.show({ message: '导出失败，请稍后重试', type: 'error', duration: 3000, title: '导出错误' })
    }
  }
}

// 保存笔记内容
async function saveNote() {
  if (!selectedNote.value || saving.value) return

  // 保存前创建版本
  saveVersionHistory()

  saving.value = true
  try {
    await request(`/api/notes/${selectedNote.value.id}`, 'PUT', {
      content: noteContent.value
    })

    if (window.toastManager) {
      window.toastManager.show({ message: '笔记保存成功！', type: 'success', duration: 3000, title: '保存完成' })
    }
  } catch (err) {
    console.error('Error saving note:', err)
    if (window.toastManager) {
      window.toastManager.show({ message: '保存笔记失败，请稍后重试', type: 'error', duration: 3000, title: '保存错误' })
    }
  } finally {
    saving.value = false
  }
}

// 保存版本历史
function saveVersionHistory() {
  if (selectedNote.value) {
    versionHistory.saveVersion(
      'note',
      selectedNote.value.id,
      noteContent.value,
      '手动保存'
    )
  }
}

// 加载版本历史
function loadVersionHistory() {
  if (selectedNote.value) {
    versions.value = versionHistory.getVersions('note', selectedNote.value.id)
  }
}

// 查看版本历史
function showVersions() {
  loadVersionHistory()
  showVersionHistory.value = true
}

// 恢复版本
function restoreToVersion(versionId) {
  if (!selectedNote.value) return

  const version = versionHistory.restoreVersion('note', selectedNote.value.id, versionId)
  if (version) {
    noteContent.value = version.content
    loadVersionHistory()
    showVersionHistory.value = false

    if (window.toastManager) {
      window.toastManager.show({ message: '版本已恢复！', type: 'success', duration: 3000, title: '恢复完成' })
    }
  }
}

// 删除版本
function deleteVersion(versionId) {
  if (!selectedNote.value) return

  if (confirm('确定要删除这个版本吗？')) {
    versionHistory.deleteVersion('note', selectedNote.value.id, versionId)
    loadVersionHistory()

    if (window.toastManager) {
      window.toastManager.show({ message: '版本已删除', type: 'info', duration: 3000, title: '删除完成' })
    }
  }
}

// 格式化日期时间
function formatDateTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 创建新笔记
async function createNote() {
  if (!noteTitle.value.trim()) {
    alert('请输入笔记标题')
    return
  }
  
  saving.value = true
  try {
    const data = await request('/api/notes', 'POST', {
      title: noteTitle.value.trim()
    })
    
    // 创建成功，刷新笔记列表
    await loadNotes()
    
    // 选中新创建的笔记
    if (data.id) {
      const newNote = notes.value.find(n => n.id === data.id)
      if (newNote) {
        selectNote(newNote)
      }
    }
    
    // 关闭弹窗并重置表单
    showCreateModal.value = false
    noteTitle.value = ''
    
    alert('笔记创建成功')
  } catch (err) {
    console.error('Error creating note:', err)
    alert('创建笔记失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

// 删除笔记
async function deleteNote() {
  if (!selectedNote.value) return

  const noteToDelete = selectedNote.value
  const hasChatHistory = chatMessages.value.length > 0

  let confirmMessage = `确定要删除笔记"${noteToDelete.title}"吗？\n\n`
  if (hasChatHistory) {
    confirmMessage += `此操作将同时删除：\n- 笔记内容\n- ${chatMessages.value.length} 条对话记录\n- 工作结果\n\n此操作无法恢复，确定继续？`
  } else {
    confirmMessage += `此操作无法恢复，确定继续？`
  }

  if (!confirm(confirmMessage)) {
    return
  }

  try {
    await request(`/api/notes/${noteToDelete.id}`, 'DELETE')

    // 从列表中移除已删除的笔记
    const index = notes.value.findIndex(n => n.id === noteToDelete.id)
    if (index > -1) {
      notes.value.splice(index, 1)
    }

    // 选择其他笔记或清空内容
    if (notes.value.length > 0) {
      const nextIndex = Math.min(index, notes.value.length - 1)
      selectNote(notes.value[nextIndex])
    } else {
      selectedNote.value = null
      noteContent.value = ''
      chatMessages.value = []
      workResults.value = []
    }

    alert('笔记删除成功')
  } catch (err) {
    console.error('Error deleting note:', err)
    alert('删除笔记失败，请稍后重试')
  }
}

// 发送对话消息
async function sendMessage() {
  if (!chatInput.value.trim() || !selectedNote.value || chatSending.value) return
  
  const message = chatInput.value.trim()
  chatInput.value = ''
  chatSending.value = true
  
  // 添加用户消息到列表
  chatMessages.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })
  
  try {
    // 发送消息到服务器
    const response = await request(`/api/notes/${selectedNote.value.id}/chat`, 'POST', {
      message: message
    })
    
    // 添加AI回复到列表
    chatMessages.value.push({
      role: 'assistant',
      content: response.content || response.message || '抱歉，我无法处理您的请求。',
      timestamp: new Date().toISOString()
    })
  } catch (err) {
    console.error('Error sending message:', err)
    chatMessages.value.push({
      role: 'assistant',
      content: '发送消息失败，请稍后重试。',
      timestamp: new Date().toISOString()
    })
  } finally {
    chatSending.value = false
  }
}

// 选择工作结果
function selectWorkResult(result) {
  selectedWorkResult.value = result
}
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <!-- 左侧笔记列表 -->
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-medium text-gray-900">我的笔记</h2>
          <button
            @click="showCreateModal = true"
            class="btn-primary px-3 py-1 text-sm"
          >
            新增
          </button>
        </div>
        <!-- 搜索框 -->
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索笔记..."
          class="input-field"
        />
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="loading && notes.length === 0" class="p-4 text-center text-gray-500">
          加载中...
        </div>

        <div v-else-if="filteredNotes.length === 0" class="p-4 text-center text-gray-500">
          {{ searchQuery ? '未找到匹配的笔记' : '暂无笔记' }}
        </div>

        <div v-else>
          <div
            v-for="note in filteredNotes"
            :key="note.id"
            @click="selectNote(note)"
            :class="[
              'p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50',
              selectedNote && selectedNote.id === note.id ? 'bg-indigo-50 border-l-4 border-l-indigo-500' : ''
            ]"
          >
            <h3 class="font-medium text-gray-900 truncate">{{ note.title }}</h3>
            <p class="text-sm text-gray-500 mt-1">{{ note.updated_at || '最近更新' }}</p>
          </div>
        </div>
      </div>
      
      <div class="p-4 border-t border-gray-200">
        <button
          @click="router.push({name:'files'})"
          class="w-full btn-secondary text-sm"
        >
          返回文件管理
        </button>
      </div>
    </div>
    
    <!-- 中间对话区域 -->
    <div class="flex-1 flex flex-col bg-white">
      <div v-if="!selectedNote" class="flex-1 flex items-center justify-center text-gray-500">
        <div class="text-center">
          <p class="text-lg">请选择一个笔记开始对话</p>
          <p class="text-sm mt-2">或者创建一个新笔记</p>
        </div>
      </div>
      
      <div v-else class="flex-1 flex flex-col">
        <!-- 顶部工具栏 -->
        <div class="bg-gray-50 border-b border-gray-200 p-4">
          <div class="flex items-center justify-between">
            <h1 class="text-xl font-medium text-gray-900">{{ selectedNote.title }}</h1>
            <div class="flex space-x-2">
              <!-- 版本历史按钮 -->
              <button
                @click="showVersions"
                class="btn-secondary text-sm"
              >
                版本历史 ({{ versions.length }})
              </button>

              <!-- 导出按钮 -->
              <div class="relative">
                <button
                  class="btn-secondary text-sm"
                  @click="showExportMenu = !showExportMenu"
                >
                  导出
                  <svg class="inline-block w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <!-- 导出菜单 -->
                <div
                  v-if="showExportMenu"
                  class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-10"
                >
                  <a
                    href="#"
                    @click.prevent="exportNoteToText"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    导出为文本
                  </a>
                  <a
                    href="#"
                    @click.prevent="exportNoteToMarkdown"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    导出为 Markdown
                  </a>
                  <a
                    href="#"
                    @click.prevent="exportNoteToWord"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    导出为 Word
                  </a>
                </div>
              </div>

              <button
                @click="saveNote"
                :disabled="saving"
                class="btn-success text-sm"
              >
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button
                @click="deleteNote"
                class="btn-danger text-sm"
              >
                删除
              </button>
            </div>
          </div>
        </div>
        
        <!-- 对话消息区域 -->
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="chatMessages.length === 0" class="flex items-center justify-center h-full text-gray-500">
            <p class="text-center">开始与AI助手对话，询问关于笔记的问题</p>
          </div>
          
          <div v-else class="space-y-4">
            <div
              v-for="(message, index) in chatMessages"
              :key="index"
              :class="[
                'flex',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              ]"
            >
              <div
                :class="[
                  'max-w-xs px-4 py-2 rounded-lg',
                  message.role === 'user' 
                    ? 'bg-indigo-600 text-white' 
                    : 'bg-gray-200 text-gray-800'
                ]"
              >
                {{ message.content }}
              </div>
            </div>
          </div>
        </div>
        
        <!-- 对话输入区域 -->
        <div class="border-t border-gray-200 p-4">
          <div class="flex space-x-2">
            <input
              v-model="chatInput"
              type="text"
              placeholder="输入您的问题..."
              class="input-field flex-1"
              @keyup.enter="sendMessage"
              :disabled="chatSending"
            />
            <button
              @click="sendMessage"
              :disabled="chatSending || !chatInput.trim()"
              class="btn-primary"
            >
              {{ chatSending ? '发送中...' : '发送' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 右侧工作结果列表 -->
    <div class="w-80 bg-white border-l border-gray-200 flex flex-col">
      <div class="p-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">工作结果</h2>
      </div>
      
      <div class="flex-1 overflow-y-auto">
      <div v-if="!selectedNote" class="p-4 text-center text-gray-500">
        请先选择笔记
      </div>
      
      <div v-else-if="workResults.length === 0" class="p-4 text-center text-gray-500">
        暂无工作结果
      </div>
      
      <div v-else>
        <div
          v-for="result in workResults"
          :key="result.id"
          @click="selectWorkResult(result)"
          :class="[
            'p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50',
            selectedWorkResult && selectedWorkResult.id === result.id ? 'bg-indigo-50 border-l-4 border-l-indigo-500' : ''
          ]"
        >
          <h3 class="font-medium text-gray-900 truncate">{{ result.title }}</h3>
          <p class="text-sm text-gray-500 mt-1">{{ result.created_at || '创建时间' }}</p>
          <p class="text-sm text-gray-600 mt-2">{{ result.summary }}</p>
          </div>
        </div>
      </div>
      
      <div v-if="selectedWorkResult" class="p-4 border-t border-gray-200">
        <div class="bg-gray-50 rounded-lg p-3">
          <h3 class="font-medium text-gray-900 mb-2">{{ selectedWorkResult.title }}</h3>
          <p class="text-sm text-gray-600">{{ selectedWorkResult.content }}</p>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 创建笔记弹窗 -->
  <div v-if="showCreateModal" class="modal-overlay">
    <div class="modal-content max-w-md">
      <h3 class="text-lg font-medium mb-4">新增笔记</h3>
      <input
        v-model="noteTitle"
        type="text"
        placeholder="请输入笔记标题"
        class="input-field mb-4"
        @keyup.enter="createNote"
        ref="noteTitleInput"
      />
      <div class="flex justify-end space-x-2">
        <button
          @click="showCreateModal = false; noteTitle = ''"
          class="btn-secondary"
        >
          取消
        </button>
        <button
          @click="createNote"
          :disabled="saving || !noteTitle.trim()"
          class="btn-primary"
        >
          {{ saving ? '创建中...' : '创建' }}
        </button>
      </div>
    </div>
  </div>
</template>