<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

// 定义组件属性
const props = defineProps({
  imageUrl: {
    type: String,
    required: true
  },
  altText: {
    type: String,
    default: ''
  },
  loadingText: {
    type: String,
    default: '加载中...'
  },
  errorText: {
    type: String,
    default: '图片加载失败'
  }
})

// 定义组件事件
const emit = defineEmits(['imageLoaded', 'zoomChange'])

// 图片缩放和拖动相关变量
const scale = ref(1) // 缩放比例
const translateX = ref(0) // 水平偏移量
const translateY = ref(0) // 垂直偏移量
const isDragging = ref(false) // 是否正在拖动
const startX = ref(0) // 拖动开始时的鼠标X坐标
const startY = ref(0) // 拖动开始时的鼠标Y坐标
const startTranslateX = ref(0) // 拖动开始时的水平偏移量
const startTranslateY = ref(0) // 拖动开始时的垂直偏移量

const previewContainer = ref(null)
const imgElement = ref(null)

let animationFrameId = null

// 应用变换并限制拖动范围
const applyTransform = () => {
  if (!imgElement.value || !previewContainer.value) return
  
  const containerRect = previewContainer.value.getBoundingClientRect()
  const imgWidth = imgElement.value.naturalWidth * scale.value
  const imgHeight = imgElement.value.naturalHeight * scale.value
  
  // 改进边界计算，允许负值使图片可以居中
  const maxTranslateX = Math.max(0, (imgWidth - containerRect.width) / 2)
  const minTranslateX = -maxTranslateX
  const maxTranslateY = Math.max(0, (imgHeight - containerRect.height) / 2)
  const minTranslateY = -maxTranslateY
  
  // 当图片小于容器时，允许在容器内自由移动
  if (imgWidth <= containerRect.width) {
    const availableSpaceX = (containerRect.width - imgWidth) / 2
    translateX.value = Math.max(-availableSpaceX, Math.min(availableSpaceX, translateX.value))
  } else {
    translateX.value = Math.max(minTranslateX, Math.min(maxTranslateX, translateX.value))
  }
  
  // 对Y轴做同样的处理
  if (imgHeight <= containerRect.height) {
    const availableSpaceY = (containerRect.height - imgHeight) / 2
    translateY.value = Math.max(-availableSpaceY, Math.min(availableSpaceY, translateY.value))
  } else {
    translateY.value = Math.max(minTranslateY, Math.min(maxTranslateY, translateY.value))
  }
  
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  
  animationFrameId = requestAnimationFrame(() => {
    imgElement.value.style.transform = `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`
  })
}

// 鼠标按下事件 - 开始拖动
const handleMouseDown = (e) => {
  // console.log('handleMouseDown', e.button)
  console.log('isDragging', isDragging.value)
  // 只响应左键点击
  if (e.button !== 0) return
  if (!imgElement.value) return
  
  isDragging.value = true

  startX.value = e.clientX
  startY.value = e.clientY
  startTranslateX.value = translateX.value
  startTranslateY.value = translateY.value
  
  if (previewContainer.value) {
    previewContainer.value.style.cursor = 'grabbing'
  }
  
  // 阻止默认行为，避免可能的选择文本行为
  e.preventDefault()
}

// 鼠标移动事件 - 拖动中
const handleMouseMove = (e) => {
  if (!isDragging.value) return
  
  const deltaX = (e.clientX - startX.value) / scale.value
  const deltaY = (e.clientY - startY.value) / scale.value
  
  translateX.value = startTranslateX.value + deltaX
  translateY.value = startTranslateY.value + deltaY
  
  // 应用变换并限制拖动范围
  applyTransform()
}

// 鼠标释放事件 - 结束拖动
const handleMouseUp = () => {
  if (isDragging.value) {
    isDragging.value = false
    
    if (previewContainer.value) {
      previewContainer.value.style.cursor = 'grab'
    }
  }
}

// 鼠标离开容器事件
const handleMouseLeave = () => {
  if (isDragging.value) {
    isDragging.value = false
    
    if (previewContainer.value) {
      previewContainer.value.style.cursor = 'grab'
    }
  }
}

// 鼠标滚轮事件 - 缩放和滚动
const handleWheel = (e) => {
  if (!imgElement.value) return
  
  // 如果按下Ctrl键，则进行缩放
  if (e.ctrlKey) {
    e.preventDefault()
    
    // 计算缩放比例
    const zoomSpeed = 0.1
    const delta = e.deltaY > 0 ? -zoomSpeed : zoomSpeed
    const newScale = Math.max(0.1, Math.min(5, scale.value + delta))
    
    // 如果缩放比例没有变化，直接返回
    if (Math.abs(newScale - scale.value) < 0.01) return
    
    // 获取鼠标位置相对于容器
    const rect = previewContainer.value.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - rect.width / 2
    const mouseY = e.clientY - rect.top - rect.height / 2
    
    // 关键修复：以鼠标位置为中心的缩放
    // 计算缩放前后的坐标变化
    const prevScale = scale.value
    
    // 计算当前鼠标位置在图片坐标系统中的位置
    // 图片坐标系统：原点在容器中心，加上当前的偏移
    const pointX = mouseX - translateX.value * prevScale
    const pointY = mouseY - translateY.value * prevScale
    
    // 更新缩放比例
    scale.value = newScale
    
    // 调整偏移量，使鼠标位置在缩放后保持不变
    // 公式：newTranslate = oldTranslate + (1/oldScale - 1/newScale) * point
    translateX.value += (pointX / prevScale - pointX / newScale)
    translateY.value += (pointY / prevScale - pointY / newScale)
    
    // 应用变换并限制拖动范围
    applyTransform()
    
    // 发送缩放变化事件
    emit('zoomChange', scale.value)
  } else {
    // 否则，进行滚动上下移动
    e.preventDefault()
    translateY.value += e.deltaY * 0.5 / scale.value
    applyTransform()
  }
}

// 放大按钮事件
const handleZoomIn = () => {
  scale.value = Math.min(1.5, scale.value + 1.5)
  applyTransform()
  emit('zoomChange', scale.value)
}

// 缩小按钮事件
const handleZoomOut = () => {
  scale.value = Math.max(0.8, scale.value - 0.2)
  applyTransform()
  emit('zoomChange', scale.value)
}

// 重置缩放和位置
const resetZoomAndPosition = () => {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
  applyTransform()
  emit('zoomChange', scale.value)
}

// 暴露方法给父组件
defineExpose({
  handleZoomIn,
  handleZoomOut,
  resetZoomAndPosition,
  scale
})

// 图片加载完成事件
const handleImageLoaded = () => {
  emit('imageLoaded', {
    width: imgElement.value.naturalWidth,
    height: imgElement.value.naturalHeight
  })
}

// 全局鼠标事件处理函数
const handleGlobalMouseMove = (e) => {
  handleMouseMove(e)
}

const handleGlobalMouseUp = () => {
  handleMouseUp()
}

// 组件挂载时初始化
onMounted(() => {
  // 使用全局事件监听，确保即使鼠标移动到容器外也能继续拖动
  document.addEventListener('mousemove', handleGlobalMouseMove)
  document.addEventListener('mouseup', handleGlobalMouseUp)
})

// 组件卸载时清理
onBeforeUnmount(() => {
  document.removeEventListener('mousemove', handleGlobalMouseMove)
  document.removeEventListener('mouseup', handleGlobalMouseUp)
  
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<template>
  <div class="preview-section bg-gray-50 h-full relative">
    <div 
      ref="previewContainer"
      class="items-center justify-center h-full flex overflow-hidden"
      style="cursor: grab;"
      @wheel="handleWheel"
      @mouseleave="handleMouseLeave"
    >
      <div v-if="!imgElement" class="text-gray-500">
        {{ loadingText }}
      </div>
      <img
        v-if="imageUrl"
        ref="imgElement"
        :src="imageUrl"
        :alt="altText"
        style="max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.1s ease; position: relative; transform-origin: center center;"
        @load="handleImageLoaded"
        @error="() => console.error('Image load error')"
        @mousedown="handleMouseDown"
      />
      <div v-if="errorText && !imageUrl" class="text-red-500">
        {{ errorText }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.preview-section {
  overflow: hidden;
}
</style>
