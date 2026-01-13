<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'medium', // small, medium, large
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  closeOnClickOutside: {
    type: Boolean,
    default: true
  },
  closeOnEsc: {
    type: Boolean,
    default: true
  },
  showCloseButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close', 'confirm'])

// 模态框引用
const modalRef = ref(null)
const modalContentRef = ref(null)

// 焦点管理
const previousActiveElement = ref(null)

// 尺寸映射
const sizeClasses = {
  small: 'max-w-md',
  medium: 'max-w-2xl',
  large: 'max-w-5xl'
}

// 打开模态框时设置焦点
async function openModal() {
  await nextTick()
  // 保存当前焦点元素
  previousActiveElement.value = document.activeElement

  // 聚焦模态框
  if (modalContentRef.value) {
    modalContentRef.value.focus()

    // 找到第一个可聚焦元素并聚焦
    const focusableElements = modalContentRef.value.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    if (focusableElements.length > 0) {
      focusableElements[0].focus()
    }
  }

  // 禁用背景滚动
  document.body.style.overflow = 'hidden'
}

// 关闭模态框
function closeModal() {
  emit('close')

  // 恢复背景滚动
  document.body.style.overflow = ''

  // 恢复焦点
  if (previousActiveElement.value) {
    previousActiveElement.value.focus()
    previousActiveElement.value = null
  }
}

// 处理点击外部
function handleClickOutside(event) {
  if (props.closeOnClickOutside && modalRef.value && !modalRef.value.contains(event.target)) {
    closeModal()
  }
}

// 处理 Escape 键
function handleEscKey(event) {
  if (props.closeOnEsc && event.key === 'Escape') {
    closeModal()
  }
}

// 处理焦点陷阱
function handleFocusTrap(event) {
  if (!modalContentRef.value) return

  const focusableElements = Array.from(
    modalContentRef.value.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
  )

  if (focusableElements.length === 0) return

  const firstFocusable = focusableElements[0]
  const lastFocusable = focusableElements[focusableElements.length - 1]

  if (event.shiftKey) {
    // Shift+Tab: 如果焦点在第一个元素上，移动到最后一个元素
    if (document.activeElement === firstFocusable) {
      event.preventDefault()
      lastFocusable.focus()
    }
  } else {
    // Tab: 如果焦点在最后一个元素上，移动到第一个元素
    if (document.activeElement === lastFocusable) {
      event.preventDefault()
      firstFocusable.focus()
    }
  }
}

// 监听显示状态变化
watch(() => props.show, (newVal) => {
  if (newVal) {
    openModal()
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  // 添加全局事件监听
  document.addEventListener('click', handleClickOutside, true)
  document.addEventListener('keydown', handleEscKey, true)
  document.addEventListener('keydown', handleFocusTrap, true)
})

onBeforeUnmount(() => {
  // 移除全局事件监听
  document.removeEventListener('click', handleClickOutside, true)
  document.removeEventListener('keydown', handleEscKey, true)
  document.removeEventListener('keydown', handleFocusTrap, true)

  // 清理样式
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <!-- 背景遮罩 -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="show"
        ref="modalRef"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="title ? 'modal-title' : null"
      >
        <!-- 模态框内容 -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="show"
            ref="modalContentRef"
            :class="[
              'bg-white rounded-xl shadow-2xl w-full mx-4 overflow-hidden',
              sizeClasses[size]
            ]"
            tabindex="-1"
            role="document"
          >
            <!-- 标题栏 -->
            <div v-if="title || showCloseButton" class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 v-if="title" id="modal-title" class="text-lg font-semibold text-gray-900">
                {{ title }}
              </h2>
              <button
                v-if="showCloseButton"
                @click="closeModal"
                class="text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600 transition-colors"
                aria-label="关闭"
              >
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- 内容区域 -->
            <div class="px-6 py-4">
              <slot></slot>
            </div>

            <!-- 底部操作栏（可选） -->
            <div v-if="$slots.footer" class="flex items-center justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-200">
              <slot name="footer" :close="closeModal"></slot>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 模态框动画 */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* 防止背景滚动 */
body {
  overflow: hidden;
}
</style>
