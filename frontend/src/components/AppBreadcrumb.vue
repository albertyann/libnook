<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

// 面包屑项定义
const breadcrumbs = computed(() => {
  const pathMap = {
    'home': { label: '首页', path: '/' },
    'files': { label: '文件管理', path: '/files' },
    'workspace': { label: '工作区', path: '/workspace' },
    'notes': { label: '笔记', path: '/notes' },
    'note': { label: '笔记详情', path: '/note' },
    'settings': { label: '设置', path: '/settings' }
  }

  const items = [{ label: '首页', path: '/' }]

  if (route.name) {
    // 添加当前页面
    const currentItem = pathMap[route.name]
    if (currentItem && route.name !== 'home') {
      items.push({ ...currentItem })
    }

    // 特殊处理：工作区显示文件名
    if (route.name === 'workspace' && route.query.id) {
      items[items.length - 1].label = '工作区'
    }

    // 特殊处理：笔记详情显示笔记标题
    if (route.name === 'note') {
      items[items.length - 1].label = '笔记详情'
    }
  }

  return items
})

// 跳转到指定路径
function navigateTo(path) {
  window.location.href = path
}
</script>

<template>
  <nav class="bg-gray-50 border-b border-gray-200" aria-label="面包屑导航">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
      <ol class="flex items-center space-x-2 text-sm">
        <li
          v-for="(item, index) in breadcrumbs"
          :key="index"
          class="flex items-center"
        >
          <!-- 分隔符 -->
          <span
            v-if="index > 0"
            class="mx-2 text-gray-400"
            aria-hidden="true"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </span>

          <!-- 面包屑项 -->
          <a
            v-if="index < breadcrumbs.length - 1"
            href="#"
            @click.prevent="navigateTo(item.path)"
            class="text-gray-500 hover:text-gray-700 transition-colors"
          >
            {{ item.label }}
          </a>
          <span
            v-else
            class="text-gray-900 font-medium"
            aria-current="page"
          >
            {{ item.label }}
          </span>
        </li>
      </ol>
    </div>
  </nav>
</template>

<style scoped>
/* 响应式调整 */
@media (max-width: 640px) {
  ol {
    flex-wrap: wrap;
  }
}
</style>
