const KEY = 'ocr_configs'

// 默认配置
const DEFAULT_CONFIGS = [
  {
    id: 'default',
    name: '默认配置',
    apiUrl: 'https://api.example.com/ocr',
    apiKey: '',
    isActive: true
  }
]

function getConfigs() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : DEFAULT_CONFIGS
  } catch {
    return DEFAULT_CONFIGS
  }
}

function saveConfigs(configs) {
  localStorage.setItem(KEY, JSON.stringify(configs))
}

// 获取所有配置
export function listConfigs() {
  return getConfigs()
}

// 获取当前激活的配置
export function getActiveConfig() {
  const configs = getConfigs()
  return configs.find(config => config.isActive) || configs[0]
}

// 添加新配置
export function addConfig({ name, apiUrl, apiKey }) {
  const configs = getConfigs()
  const id = (crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now() + Math.random())
  const newConfig = {
    id,
    name,
    apiUrl,
    apiKey,
    isActive: false
  }
  configs.push(newConfig)
  saveConfigs(configs)
  return id
}

// 更新配置
export function updateConfig(id, partial) {
  const configs = getConfigs()
  const index = configs.findIndex(config => config.id === id)
  if (index >= 0) {
    configs[index] = { ...configs[index], ...partial }
    saveConfigs(configs)
  }
}

// 删除配置
export function removeConfig(id) {
  const configs = getConfigs()
  // 不允许删除最后一个配置
  if (configs.length <= 1) {
    throw new Error('至少需要保留一个OCR配置')
  }
  
  const newConfigs = configs.filter(config => config.id !== id)
  // 如果删除的是激活的配置，则激活第一个配置
  const wasActive = configs.some(config => config.id === id && config.isActive)
  if (wasActive && newConfigs.length > 0) {
    newConfigs[0].isActive = true
  }
  saveConfigs(newConfigs)
}

// 激活配置
export function activateConfig(id) {
  const configs = getConfigs()
  configs.forEach(config => {
    config.isActive = config.id === id
  })
  saveConfigs(configs)
}
