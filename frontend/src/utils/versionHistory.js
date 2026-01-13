// 版本历史管理工具

const VERSION_STORAGE_KEY = 'version_history'

/**
 * 生成唯一ID
 */
function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

/**
 * 获取所有版本历史
 */
function getAllVersions() {
  try {
    const raw = localStorage.getItem(VERSION_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch (error) {
    console.error('Error loading version history:', error)
    return {}
  }
}

/**
 * 保存版本历史
 */
function saveAllVersions(versions) {
  try {
    localStorage.setItem(VERSION_STORAGE_KEY, JSON.stringify(versions))
  } catch (error) {
    console.error('Error saving version history:', error)
  }
}

/**
 * 获取指定资源的版本历史
 * @param {string} resourceType - 资源类型: 'note', 'workspace_page'
 * @param {string} resourceId - 资源ID
 * @returns {Array} 版本列表
 */
export function getVersions(resourceType, resourceId) {
  const versions = getAllVersions()
  const key = `${resourceType}_${resourceId}`
  return versions[key] || []
}

/**
 * 保存新版本
 * @param {string} resourceType - 资源类型: 'note', 'workspace_page'
 * @param {string} resourceId - 资源ID
 * @param {string} content - 内容
 * @param {string} description - 版本描述
 * @returns {string} 版本ID
 */
export function saveVersion(resourceType, resourceId, content, description = '') {
  const versions = getAllVersions()
  const key = `${resourceType}_${resourceId}`

  if (!versions[key]) {
    versions[key] = []
  }

  const version = {
    id: generateId(),
    content,
    description,
    createdAt: new Date().toISOString(),
    createdBy: 'user'
  }

  // 添加新版本到列表开头
  versions[key].unshift(version)

  // 限制版本数量（最多保留50个版本）
  if (versions[key].length > 50) {
    versions[key] = versions[key].slice(0, 50)
  }

  saveAllVersions(versions)

  return version.id
}

/**
 * 恢复到指定版本
 * @param {string} resourceType - 资源类型: 'note', 'workspace_page'
 * @param {string} resourceId - 资源ID
 * @param {string} versionId - 版本ID
 * @returns {Object|null} 版本内容
 */
export function restoreVersion(resourceType, resourceId, versionId) {
  const versions = getVersions(resourceType, resourceId)
  const version = versions.find(v => v.id === versionId)

  if (!version) {
    console.error('Version not found:', versionId)
    return null
  }

  // 创建新的恢复版本
  saveVersion(
    resourceType,
    resourceId,
    version.content,
    `恢复自版本 ${new Date(version.createdAt).toLocaleString('zh-CN')}`
  )

  return version
}

/**
 * 删除指定版本
 * @param {string} resourceType - 资源类型: 'note', 'workspace_page'
 * @param {string} resourceId - 资源ID
 * @param {string} versionId - 版本ID
 */
export function deleteVersion(resourceType, resourceId, versionId) {
  const versions = getAllVersions()
  const key = `${resourceType}_${resourceId}`

  if (versions[key]) {
    versions[key] = versions[key].filter(v => v.id !== versionId)
    saveAllVersions(versions)
  }
}

/**
 * 清除指定资源的所有版本
 * @param {string} resourceType - 资源类型: 'note', 'workspace_page'
 * @param {string} resourceId - 资源ID
 */
export function clearVersions(resourceType, resourceId) {
  const versions = getAllVersions()
  const key = `${resourceType}_${resourceId}`

  if (versions[key]) {
    delete versions[key]
    saveAllVersions(versions)
  }
}

/**
 * 清除所有版本历史
 */
export function clearAllVersions() {
  try {
    localStorage.removeItem(VERSION_STORAGE_KEY)
  } catch (error) {
    console.error('Error clearing version history:', error)
  }
}

/**
 * 获取版本统计信息
 * @param {string} resourceType - 资源类型: 'note', 'workspace_page'
 * @param {string} resourceId - 资源ID
 * @returns {Object} 统计信息
 */
export function getVersionStats(resourceType, resourceId) {
  const versions = getVersions(resourceType, resourceId)

  return {
    total: versions.length,
    latest: versions[0] || null,
    oldest: versions[versions.length - 1] || null,
    size: JSON.stringify(versions).length // 版本数据大小（字符数）
  }
}
