<script setup>
import { computed } from 'vue'

// 定义组件属性
const props = defineProps({
  variant: {
    type: String,
    default: 'primary', // primary, secondary, danger, success, warning, info
    validator: (value) => ['primary', 'secondary', 'danger', 'success', 'warning', 'info'].includes(value)
  },
  size: {
    type: String,
    default: 'medium', // small, medium, large
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  type: {
    type: String,
    default: 'button', // button, submit, reset
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  fullWidth: {
    type: Boolean,
    default: false
  }
})

// 定义组件事件
const emit = defineEmits(['click'])

// 样式映射
const variantClasses = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300',
  secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:bg-gray-50',
  danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
  success: 'bg-green-600 text-white hover:bg-green-700 disabled:bg-green-300',
  warning: 'bg-yellow-500 text-white hover:bg-yellow-600 disabled:bg-yellow-300',
  info: 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300'
}

const sizeClasses = {
  small: 'px-3 py-1 text-sm',
  medium: 'px-4 py-2 text-sm',
  large: 'px-6 py-3 text-base'
}

// 计算属性
const buttonClass = computed(() => {
  const classes = [
    'rounded-md font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2',
    variantClasses[props.variant] || variantClasses.primary,
    sizeClasses[props.size] || sizeClasses.medium,
    props.fullWidth ? 'w-full' : '',
    props.disabled || props.loading ? 'cursor-not-allowed' : 'cursor-pointer'
  ]

  if (props.variant === 'primary' || props.variant === 'info') {
    classes.push('focus:ring-blue-500')
  } else if (props.variant === 'danger') {
    classes.push('focus:ring-red-500')
  } else if (props.variant === 'success') {
    classes.push('focus:ring-green-500')
  } else {
    classes.push('focus:ring-gray-500')
  }

  return classes.join(' ')
})

function handleClick(event) {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="buttonClass"
    @click="handleClick"
    :aria-disabled="disabled || loading"
  >
    <span v-if="loading" class="inline-flex items-center">
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      加载中...
    </span>
    <slot v-else></slot>
  </button>
</template>

<style scoped>
/* 禁用状态的透明度 */
button:disabled {
  opacity: 0.6;
}
</style>
