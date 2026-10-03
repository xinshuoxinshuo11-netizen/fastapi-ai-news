import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const endpoint = env.VITE_AI_API_ENDPOINT || 'https://api.deepseek.com/chat/completions'
  // 保持课程前端直连方式；密钥从本机环境读取，不写入源码。
  const key = env.VITE_AI_API_KEY || (endpoint.includes('api.deepseek.com')
    ? env.DEEPSEEK_API_KEY : env.DASHSCOPE_API_KEY || env.QWEN_API_KEY) || ''
  return {
    plugins: [vue()],
    server: { host: '127.0.0.1', port: 5176, strictPort: true },
    define: { 'import.meta.env.VITE_AI_API_KEY': JSON.stringify(key) },
  }
})
