<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// 导航项定义
const navItems = [
  { name: 'home', label: '首页', icon: 'mdi:home' },
  { name: 'files', label: '文件管理', icon: 'mdi:file-multiple' },
  { name: 'notes', label: '笔记', icon: 'mdi:notebook' },
  { name: 'settings', label: '设置', icon: 'mdi:cog' }
]

// 判断当前路由
const isActive = (name) => {
  return route.name === name
}

// 导航函数
function navigateTo(name) {
  router.push({ name })
}
</script>

<template>
  <nav class="bg-white border-b border-gray-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo / 标题 -->
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <svg class="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div class="ml-3">
            <span class="text-xl font-bold text-gray-900">PDF OCR</span>
          </div>
        </div>

        <!-- 导航链接 -->
        <div class="hidden md:flex items-center space-x-4">
          <a
            v-for="item in navItems"
            :key="item.name"
            href="#"
            @click.prevent="navigateTo(item.name)"
            :class="[
              'flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors',
              isActive(item.name)
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            ]"
            :aria-current="isActive(item.name) ? 'page' : undefined"
          >
            <span class="iconify mr-2" :data-icon="item.icon" data-width="20"></span>
            {{ item.label }}
          </a>
        </div>

        <!-- 移动端菜单按钮 -->
        <div class="md:hidden">
          <button
            type="button"
            class="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            aria-controls="mobile-menu"
            aria-expanded="false"
          >
            <span class="sr-only">打开主菜单</span>
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 移动端菜单 -->
    <div class="md:hidden hidden" id="mobile-menu">
      <div class="px-2 pt-2 pb-3 space-y-1 bg-white border-t border-gray-200">
        <a
          v-for="item in navItems"
          :key="item.name"
          href="#"
          @click.prevent="navigateTo(item.name)"
          :class="[
            'flex items-center px-3 py-2 rounded-md text-base font-medium',
            isActive(item.name)
              ? 'bg-indigo-50 text-indigo-700'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
          ]"
        >
          <span class="iconify mr-3" :data-icon="item.icon" data-width="20"></span>
          {{ item.label }}
        </a>
      </div>
    </div>
  </nav>
</template>

<style scoped>
/* 隐藏移动端菜单，可以通过 JavaScript 切换显示 */
#mobile-menu.hidden {
  display: none;
}
</style>
