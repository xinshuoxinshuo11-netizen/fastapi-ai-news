// 后端地址与模型配置独立，便于切换课程千问和本机 DeepSeek 配置。
export const apiConfig = {
  baseURL: (import.meta.env && import.meta.env.VITE_API_BASE_URL) || 'http://127.0.0.1:19000',
}
export const aiChatConfig = {
  apiEndpoint: (import.meta.env && import.meta.env.VITE_AI_API_ENDPOINT) || 'https://api.deepseek.com/chat/completions',
  apiKey: (import.meta.env && import.meta.env.VITE_AI_API_KEY) || '',
  model: (import.meta.env && import.meta.env.VITE_AI_MODEL) || 'deepseek-chat',
}
