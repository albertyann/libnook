<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listConfigs, addConfig, updateConfig, removeConfig, activateConfig } from '../store/ocrConfig'

const router = useRouter()
const configs = ref([])
const showAddDialog = ref(false)
const editingConfig = ref(null)
const showEditDialog = ref(false)
const errorMessage = ref('')

// 表单数据
const formData = ref({
  name: '',
  apiUrl: '',
  apiKey: ''
})

// 加载配置列表
function loadConfigs() {
  configs.value = listConfigs()
  errorMessage.value = ''
}

// 打开添加配置对话框
function openAddDialog() {
  formData.value = {
    name: '',
    apiUrl: '',
    apiKey: ''
  }
  showAddDialog.value = true
}

// 打开编辑配置对话框
function openEditDialog(config) {
  editingConfig.value = { ...config }
  formData.value = {
    name: config.name,
    apiUrl: config.apiUrl,
    apiKey: config.apiKey
  }
  showEditDialog.value = true
}

// 提交添加配置
function submitAddConfig() {
  if (!validateForm()) return
  
  try {
    addConfig({
      name: formData.value.name,
      apiUrl: formData.value.apiUrl,
      apiKey: formData.value.apiKey
    })
    showAddDialog.value = false
    loadConfigs()
  } catch (error) {
    errorMessage.value = error.message
  }
}

// 提交更新配置
function submitUpdateConfig() {
  if (!validateForm() || !editingConfig.value) return
  
  try {
    updateConfig(editingConfig.value.id, {
      name: formData.value.name,
      apiUrl: formData.value.apiUrl,
      apiKey: formData.value.apiKey
    })
    showEditDialog.value = false
    loadConfigs()
  } catch (error) {
    errorMessage.value = error.message
  }
}

// 删除配置
function deleteConfig(id) {
  if (confirm('确定要删除这个配置吗？')) {
    try {
      removeConfig(id)
      loadConfigs()
    } catch (error) {
      errorMessage.value = error.message
    }
  }
}

// 激活配置
function setActive(id) {
  activateConfig(id)
  loadConfigs()
}

// 验证表单
function validateForm() {
  if (!formData.value.name.trim()) {
    errorMessage.value = '请输入配置名称'
    return false
  }
  if (!formData.value.apiUrl.trim()) {
    errorMessage.value = '请输入API地址'
    return false
  }
  try {
    new URL(formData.value.apiUrl)
  } catch {
    errorMessage.value = '请输入有效的API地址'
    return false
  }
  return true
}

// 返回首页
function goHome() {
  router.push({ name: 'home' })
}

onMounted(loadConfigs)
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <div class="max-w-4xl mx-auto">
      <!-- 头部导航 -->
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-900">OCR 配置管理</h1>
        <div class="space-x-2">
          <button 
            class="rounded-md bg-indigo-600 text-white px-4 py-2 text-sm hover:bg-indigo-700 transition-colors"
            @click="openAddDialog"
          >
            添加配置
          </button>
          <button 
            class="rounded-md bg-gray-100 px-4 py-2 text-sm hover:bg-gray-200 transition-colors"
            @click="goHome"
          >
            返回首页
          </button>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg">
        {{ errorMessage }}
      </div>

      <!-- 配置列表 -->
      <div class="bg-white border rounded-xl shadow-sm overflow-hidden mb-6">
        <table class="w-full">
          <thead class="bg-gray-50 text-left text-sm text-gray-600">
            <tr>
              <th class="p-4">配置名称</th>
              <th class="p-4">API地址</th>
              <th class="p-4">状态</th>
              <th class="p-4 w-64">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="config in configs" :key="config.id" class="border-t hover:bg-gray-50 transition-colors">
              <td class="p-4 text-sm font-medium">{{ config.name }}</td>
              <td class="p-4 text-sm text-gray-600 break-all max-w-xs">{{ config.apiUrl }}</td>
              <td class="p-4">
                <span 
                  v-if="config.isActive" 
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                >
                  已激活
                </span>
                <span 
                  v-else 
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  未激活
                </span>
              </td>
              <td class="p-4">
                <div class="flex items-center gap-2">
                  <button 
                    v-if="!config.isActive"
                    class="rounded-md bg-green-600 text-white px-3 py-1 text-xs hover:bg-green-700 transition-colors"
                    @click="setActive(config.id)"
                  >
                    激活
                  </button>
                  <button 
                    class="rounded-md bg-blue-600 text-white px-3 py-1 text-xs hover:bg-blue-700 transition-colors"
                    @click="openEditDialog(config)"
                  >
                    编辑
                  </button>
                  <button 
                    class="rounded-md bg-red-600 text-white px-3 py-1 text-xs hover:bg-red-700 transition-colors"
                    @click="deleteConfig(config.id)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!configs.length">
              <td colspan="4" class="p-6 text-center text-gray-500">暂无配置</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 使用说明 -->
      <div class="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
        <h3 class="text-sm font-semibold text-indigo-800 mb-2">使用说明</h3>
        <ul class="text-sm text-indigo-700 space-y-1">
          <li>• 请确保API地址格式正确，以http或https开头</li>
          <li>• 可以添加多个OCR配置，但同一时间只能激活一个</li>
          <li>• 至少需要保留一个OCR配置</li>
          <li>• 激活的配置将用于PDF文件的文字识别</li>
        </ul>
      </div>
    </div>

    <!-- 添加配置对话框 -->
    <div v-if="showAddDialog" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">添加OCR配置</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">配置名称</label>
            <input 
              v-model="formData.name"
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="请输入配置名称"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API地址</label>
            <input 
              v-model="formData.apiUrl"
              type="url" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="https://api.example.com/ocr"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API密钥</label>
            <input 
              v-model="formData.apiKey"
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="请输入API密钥（可选）"
            >
          </div>
        </div>
        
        <div class="flex justify-end gap-3 mt-6">
          <button 
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            @click="showAddDialog = false"
          >
            取消
          </button>
          <button 
            class="px-4 py-2 bg-indigo-600 border border-transparent rounded-md text-sm font-medium text-white hover:bg-indigo-700"
            @click="submitAddConfig"
          >
            添加
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑配置对话框 -->
    <div v-if="showEditDialog" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">编辑OCR配置</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">配置名称</label>
            <input 
              v-model="formData.name"
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="请输入配置名称"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API地址</label>
            <input 
              v-model="formData.apiUrl"
              type="url" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="https://api.example.com/ocr"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API密钥</label>
            <input 
              v-model="formData.apiKey"
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="请输入API密钥（可选）"
            >
          </div>
        </div>
        
        <div class="flex justify-end gap-3 mt-6">
          <button 
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            @click="showEditDialog = false"
          >
            取消
          </button>
          <button 
            class="px-4 py-2 bg-indigo-600 border border-transparent rounded-md text-sm font-medium text-white hover:bg-indigo-700"
            @click="submitUpdateConfig"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
