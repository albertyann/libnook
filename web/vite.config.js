import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': { // 拦截所有以 /api 开头的请求
        target: 'http://127.0.0.1:8000', // 转发到后端地址
        changeOrigin: true, // 修改请求头中的 origin，让后端以为是它自己发的
        pathRewrite: {
          //'^/api': '/api' // 重写路径，去掉 /api 前缀
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  }
})
