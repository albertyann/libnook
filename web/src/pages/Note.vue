<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'

const router = useRouter()

// 响应式数据
const notes = ref([]) // 笔记列表
const selectedNote = ref(null) // 当前选中的笔记
const noteContent = ref('') // 笔记内容
const loading = ref(false) // 加载状态
const saving = ref(false) // 保存状态
const showCreateModal = ref(false) // 创建笔记弹窗显示状态
const noteTitle = ref('') // 笔记标题
const noteTitleInput = ref(null) // 笔记标题输入框引用

// 页面加载时获取笔记列表
onMounted(() => {
  loadNotes()
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
  } catch (err) {
    console.error('Error loading note content:', err)
    alert('加载笔记内容失败')
  } finally {
    loading.value = false
  }
}

// 保存笔记内容
async function saveNote() {
  if (!selectedNote.value || saving.value) return
  
  saving.value = true
  try {
    await request(`/api/notes/${selectedNote.value.id}`, 'PUT', {
      content: noteContent.value
    })
    
    // 可以在这里显示保存成功的提示
    console.log('笔记保存成功')
  } catch (err) {
    console.error('Error saving note:', err)
    alert('保存笔记失败，请稍后重试')
  } finally {
    saving.value = false
  }
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
  
  if (!confirm(`确定要删除笔记"${selectedNote.value.title}"吗？此操作不可恢复。`)) {
    return
  }
  
  try {
    await request(`/api/notes/${selectedNote.value.id}`, 'DELETE')
    
    // 从列表中移除已删除的笔记
    const index = notes.value.findIndex(n => n.id === selectedNote.value.id)
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
    }
    
    alert('笔记删除成功')
  } catch (err) {
    console.error('Error deleting note:', err)
    alert('删除笔记失败，请稍后重试')
  }
}
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <!-- 左侧笔记列表 -->
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-medium text-gray-900">我的笔记</h2>
          <button
            @click="showCreateModal = true"
            class="bg-blue-500 text-white rounded-md px-3 py-1 text-sm hover:bg-blue-600"
          >
            新增
          </button>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto">
        <div v-if="loading && notes.length === 0" class="p-4 text-center text-gray-500">
          加载中...
        </div>
        
        <div v-else-if="notes.length === 0" class="p-4 text-center text-gray-500">
          暂无笔记
        </div>
        
        <div v-else>
          <div
            v-for="note in notes"
            :key="note.id"
            @click="selectNote(note)"
            :class="[
              'p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50',
              selectedNote && selectedNote.id === note.id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
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
          class="w-full bg-gray-100 text-gray-700 rounded-md px-3 py-2 text-sm hover:bg-gray-200"
        >
          返回文件管理
        </button>
      </div>
    </div>
    
    <!-- 右侧笔记内容 -->
    <div class="flex-1 flex flex-col">
      <div v-if="!selectedNote" class="flex-1 flex items-center justify-center text-gray-500">
        <div class="text-center">
          <p class="text-lg">请选择一个笔记开始编辑</p>
          <p class="text-sm mt-2">或者创建一个新笔记</p>
        </div>
      </div>
      
      <div v-else class="flex-1 flex flex-col">
        <!-- 顶部工具栏 -->
        <div class="bg-white border-b border-gray-200 p-4">
          <div class="flex items-center justify-between">
            <h1 class="text-xl font-medium text-gray-900">{{ selectedNote.title }}</h1>
            <div class="flex space-x-2">
              <button
                @click="saveNote"
                :disabled="saving"
                class="bg-green-500 text-white rounded-md px-3 py-1 text-sm hover:bg-green-600 disabled:bg-green-300"
              >
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button
                @click="deleteNote"
                class="bg-red-500 text-white rounded-md px-3 py-1 text-sm hover:bg-red-600"
              >
                删除
              </button>
            </div>
          </div>
        </div>
        
        <!-- 内容编辑区 -->
        <div class="flex-1 p-4 overflow-y-auto">
          <textarea
            v-model="noteContent"
            placeholder="开始编写笔记内容..."
            class="w-full h-full p-4 border border-gray-200 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          ></textarea>
        </div>
      </div>
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
          :disabled="saving || !noteTitle.trim()"
          class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-blue-300"
        >
          {{ saving ? '创建中...' : '创建' }}
        </button>
      </div>
    </div>
  </div>
</template>