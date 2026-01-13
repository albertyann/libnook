import { createApp } from 'vue'

// Toast 通知系统
class ToastManager {
  constructor() {
    this.container = null
    this.toasts = []
    this.toastId = 0
  }

  // 初始化容器
  init() {
    if (!this.container) {
      this.container = document.createElement('div')
      this.container.id = 'toast-container'
      this.container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2'
      document.body.appendChild(this.container)
    }
  }

  // 显示 Toast
  show({ message, type = 'info', duration = 3000, title = '' }) {
    this.init()

    const id = ++this.toastId
    const toast = {
      id,
      message,
      type,
      duration,
      title,
      createdAt: Date.now()
    }

    this.toasts.push(toast)
    this.render()

    // 自动移除
    if (duration > 0) {
      setTimeout(() => {
        this.remove(id)
      }, duration)
    }

    return id
  }

  // 移除 Toast
  remove(id) {
    const index = this.toasts.findIndex(t => t.id === id)
    if (index > -1) {
      this.toasts.splice(index, 1)
      this.render()
    }
  }

  // 清除所有 Toast
  clear() {
    this.toasts = []
    this.render()
  }

  // 渲染 Toast
  render() {
    if (!this.container) return

    this.container.innerHTML = this.toasts.map(toast => this.createToastHTML(toast)).join('')
  }

  // 创建 Toast HTML
  createToastHTML(toast) {
    const typeStyles = {
      success: 'bg-green-500 border-green-600',
      error: 'bg-red-500 border-red-600',
      warning: 'bg-yellow-500 border-yellow-600',
      info: 'bg-blue-500 border-blue-600'
    }

    const icons = {
      success: `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`,
      error: `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`,
      warning: `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>`,
      info: `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`
    }

    return `
      <div
        id="toast-${toast.id}"
        class="toast ${typeStyles[toast.type] || typeStyles.info} border-l-4 text-white px-4 py-3 rounded-lg shadow-lg transform transition-all duration-300 ease-in-out"
        style="min-width: 300px; max-width: 500px;"
      >
        <div class="flex items-start">
          <div class="flex-shrink-0 text-white">
            ${icons[toast.type] || icons.info}
          </div>
          <div class="ml-3 flex-1">
            ${toast.title ? `<h3 class="font-semibold text-sm">${toast.title}</h3>` : ''}
            <p class="text-sm ${toast.title ? 'mt-1' : ''}">${toast.message}</p>
          </div>
          <button
            onclick="window.toastManager.remove(${toast.id})"
            class="flex-shrink-0 ml-4 text-white hover:text-gray-200 focus:outline-none"
            aria-label="关闭"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>
    `
  }
}

// 创建全局实例
const toastManager = new ToastManager()

// 将实例挂载到 window 以便全局访问
if (typeof window !== 'undefined') {
  window.toastManager = toastManager
}

// Vue 插件
const ToastPlugin = {
  install(app) {
    app.config.globalProperties.$toast = {
      success(message, duration, title) {
        return toastManager.show({ message, type: 'success', duration, title })
      },
      error(message, duration, title) {
        return toastManager.show({ message, type: 'error', duration, title })
      },
      warning(message, duration, title) {
        return toastManager.show({ message, type: 'warning', duration, title })
      },
      info(message, duration, title) {
        return toastManager.show({ message, type: 'info', duration, title })
      },
      remove(id) {
        toastManager.remove(id)
      },
      clear() {
        toastManager.clear()
      }
    }
  }
}

export default ToastPlugin
export { toastManager }
