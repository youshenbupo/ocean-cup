/**
 * 离线缓存管理工具
 * 
 * 用于在小程序端缓存常用数据，支持离线访问：
 * - 常用法律知识卡片
 * - 维权热线信息
 * - 用户身份信息
 */

const CACHE_PREFIX = 'gongyou_cache_'
const CACHE_EXPIRY = 7 * 24 * 60 * 60 * 1000  // 7天过期

const cacheManager = {
  /**
   * 设置缓存
   * @param {string} key 缓存键
   * @param {any} data 缓存数据
   * @param {number} expiry 过期时间（毫秒），默认7天
   */
  set: function(key, data, expiry) {
    const cacheData = {
      data: data,
      timestamp: Date.now(),
      expiry: expiry || CACHE_EXPIRY
    }
    try {
      wx.setStorageSync(CACHE_PREFIX + key, JSON.stringify(cacheData))
    } catch (e) {
      console.error('缓存写入失败:', e)
    }
  },

  /**
   * 获取缓存
   * @param {string} key 缓存键
   * @returns {any|null} 缓存数据，过期或不存在返回null
   */
  get: function(key) {
    try {
      const raw = wx.getStorageSync(CACHE_PREFIX + key)
      if (!raw) return null
      
      const cacheData = JSON.parse(raw)
      const now = Date.now()
      
      // 检查是否过期
      if (now - cacheData.timestamp > cacheData.expiry) {
        this.remove(key)
        return null
      }
      
      return cacheData.data
    } catch (e) {
      console.error('缓存读取失败:', e)
      return null
    }
  },

  /**
   * 删除缓存
   * @param {string} key 缓存键
   */
  remove: function(key) {
    try {
      wx.removeStorageSync(CACHE_PREFIX + key)
    } catch (e) {
      console.error('缓存删除失败:', e)
    }
  },

  /**
   * 清空所有缓存
   */
  clearAll: function() {
    try {
      const res = wx.getStorageInfoSync()
      const keys = res.keys || []
      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          wx.removeStorageSync(key)
        }
      })
    } catch (e) {
      console.error('清空缓存失败:', e)
    }
  },

  /**
   * 检查网络状态，决定使用缓存还是请求网络
   * @returns {boolean} 是否离线
   */
  isOffline: function() {
    return new Promise((resolve) => {
      wx.getNetworkType({
        success: (res) => {
          resolve(res.networkType === 'none')
        },
        fail: () => {
          resolve(true)  // 获取失败时假设离线
        }
      })
    })
  },

  /**
   * 带缓存的请求封装
   * 优先使用缓存，离线时直接使用缓存，在线时更新缓存
   * @param {string} key 缓存键
   * @param {Function} fetchFn 网络请求函数
   * @returns {any} 数据
   */
  fetchWithCache: async function(key, fetchFn) {
    const cached = this.get(key)
    const offline = await this.isOffline()
    
    if (offline) {
      // 离线模式：直接返回缓存
      if (cached) {
        console.log('[Cache] 离线模式，使用缓存:', key)
        return cached
      }
      throw new Error('当前无网络，且无缓存数据')
    }
    
    // 在线模式：尝试请求网络
    try {
      const data = await fetchFn()
      this.set(key, data)  // 更新缓存
      return data
    } catch (e) {
      // 网络请求失败：使用缓存兜底
      if (cached) {
        console.log('[Cache] 网络请求失败，使用缓存:', key)
        return cached
      }
      throw e
    }
  }
}

module.exports = cacheManager
