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
  <div class="page-container p-6">
    <div class="max-w-4xl mx-auto">
      <!-- 头部导航 -->
      <div class="page-header">
        <h1 class="page-title">OCR 配置管理</h1>
        <div class="flex gap-2">
          <button 
            class="btn-primary"
            @click="openAddDialog"
          >
            添加配置
          </button>
          <button 
            class="btn-secondary"
            @click="goHome"
          >
            返回首页
          </button>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg border border-red-200">
        {{ errorMessage }}
      </div>

      <!-- 配置列表 -->
      <div class="card table-container mb-6">
        <table class="w-full">
          <thead class="table-header">
            <tr>
              <th class="table-cell">配置名称</th>
              <th class="table-cell">API地址</th>
              <th class="table-cell w-24">状态</th>
              <th class="table-cell w-48">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="config in configs" :key="config.id" class="table-row">
              <td class="table-cell font-medium">{{ config.name }}</td>
              <td class="table-cell text-gray-600 break-all max-w-xs">{{ config.apiUrl }}</td>
              <td class="table-cell">
                <span 
                  v-if="config.isActive" 
                  class="badge badge-success"
                >
                  已激活
                </span>
                <span 
                  v-else 
                  class="badge badge-gray"
                >
                  未激活
                </span>
              </td>
              <td class="table-cell">
                <div class="flex items-center gap-2">
                  <button 
                    v-if="!config.isActive"
                    class="btn-success px-3 py-1 text-xs"
                    @click="setActive(config.id)"
                  >
                    激活
                  </button>
                  <button 
                    class="btn-primary px-3 py-1 text-xs"
                    @click="openEditDialog(config)"
                  >
                    编辑
                  </button>
                  <button 
                    class="btn-danger px-3 py-1 text-xs"
                    @click="deleteConfig(config.id)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!configs.length">
              <td colspan="4" class="table-cell text-center text-gray-500">暂无配置</td>
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
    <div v-if="showAddDialog" class="modal-overlay p-4">
      <div class="modal-content max-w-md">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">添加OCR配置</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">配置名称</label>
            <input 
              v-model="formData.name"
              type="text" 
              class="input-field"
              placeholder="请输入配置名称"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API地址</label>
            <input 
              v-model="formData.apiUrl"
              type="url" 
              class="input-field"
              placeholder="https://api.example.com/ocr"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API密钥</label>
            <input 
              v-model="formData.apiKey"
              type="text" 
              class="input-field"
              placeholder="请输入API密钥（可选）"
            >
          </div>
        </div>
        
        <div class="flex justify-end gap-2 mt-6">
          <button 
            class="btn-secondary"
            @click="showAddDialog = false"
          >
            取消
          </button>
          <button 
            class="btn-primary"
            @click="submitAddConfig"
          >
            添加
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑配置对话框 -->
    <div v-if="showEditDialog" class="modal-overlay p-4">
      <div class="modal-content max-w-md">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">编辑OCR配置</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">配置名称</label>
            <input 
              v-model="formData.name"
              type="text" 
              class="input-field"
              placeholder="请输入配置名称"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API地址</label>
            <input 
              v-model="formData.apiUrl"
              type="url" 
              class="input-field"
              placeholder="https://api.example.com/ocr"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API密钥</label>
            <input 
              v-model="formData.apiKey"
              type="text" 
              class="input-field"
              placeholder="请输入API密钥（可选）"
            >
          </div>
        </div>
        
        <div class="flex justify-end gap-2 mt-6">
          <button 
            class="btn-secondary"
            @click="showEditDialog = false"
          >
            取消
          </button>
          <button 
            class="btn-primary"
            @click="submitUpdateConfig"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
