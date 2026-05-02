/**
 * WebSocket 客户端 — 自动连接/重连 + 消息分发
 *
 * 用法:
 *   import { useWebSocket } from '../utils/ws'
 *   const { on, off, send, connected } = useWebSocket()
 *   on('ticker', (data) => { ... })
 */
import { ref, readonly } from 'vue'

// 连接状态
const connected = ref(false)
const lastMessage = ref(null)

// 消息处理器: type → Set<callback>
const handlers = {}

// WebSocket 实例
let ws = null
let reconnectTimer = null
let reconnectCount = 0
const MAX_RECONNECT_DELAY = 30000

/**
 * 获取 WebSocket URL
 * 自动适配 http → ws, https → wss
 */
function getWsUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws`
}

/**
 * 注册消息处理器
 */
function on(type, callback) {
  if (!handlers[type]) {
    handlers[type] = new Set()
  }
  handlers[type].add(callback)
}

/**
 * 移除消息处理器
 */
function off(type, callback) {
  if (handlers[type]) {
    handlers[type].delete(callback)
  }
}

/**
 * 发送消息到服务端
 */
function send(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(typeof data === 'string' ? data : JSON.stringify(data))
  }
}

/**
 * 分发收到的消息
 */
function dispatch(message) {
  try {
    const msg = typeof message === 'string' ? JSON.parse(message) : message
    lastMessage.value = msg

    const type = msg.type
    const data = msg.data

    // 调用该类型的所有处理器
    if (handlers[type]) {
      handlers[type].forEach(cb => {
        try {
          cb(data, msg)
        } catch (e) {
          console.error(`[WS] Handler error for "${type}":`, e)
        }
      })
    }

    // 通配符处理器
    if (handlers['*']) {
      handlers['*'].forEach(cb => {
        try {
          cb(data, msg)
        } catch (e) {
          console.error('[WS] Wildcard handler error:', e)
        }
      })
    }
  } catch (e) {
    console.error('[WS] Parse error:', e)
  }
}

/**
 * 连接 WebSocket
 */
function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return
  }

  const url = getWsUrl()
  console.log('[WS] Connecting to', url)

  ws = new WebSocket(url)

  ws.onopen = () => {
    console.log('[WS] Connected')
    connected.value = true
    reconnectCount = 0
  }

  ws.onmessage = (event) => {
    dispatch(event.data)
  }

  ws.onclose = (event) => {
    console.log('[WS] Disconnected:', event.code, event.reason)
    connected.value = false
    scheduleReconnect()
  }

  ws.onerror = (error) => {
    console.error('[WS] Error:', error)
    connected.value = false
  }
}

/**
 * 断开连接
 */
function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.onclose = null // 避免触发重连
    ws.close()
    ws = null
  }
  connected.value = false
}

/**
 * 自动重连（指数退避）
 */
function scheduleReconnect() {
  if (reconnectTimer) return

  reconnectCount++
  const delay = Math.min(1000 * Math.pow(2, reconnectCount - 1), MAX_RECONNECT_DELAY)
  console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectCount})`)

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connect()
  }, delay)
}

/**
 * 组合式 API：在组件中使用 WebSocket
 */
export function useWebSocket() {
  return {
    connected: readonly(connected),
    lastMessage: readonly(lastMessage),
    on,
    off,
    send,
    connect,
    disconnect,
  }
}

// 自动连接（模块加载时）
connect()
