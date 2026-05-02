<template>
  <div class="dashboard-page">
    <!-- 实时价格滚动条 -->
    <div class="price-ticker">
      <!-- 恐惧贪婪指数（固定在左边） -->
      <div class="fear-greed-fixed">
        <div class="fgi-icon">{{ fearGreedEmoji }}</div>
        <div class="fgi-content">
          <div class="fgi-value" :class="fearGreedClass">{{ fearGreedIndex }}</div>
          <div class="fgi-label">{{ fearGreedLabel }}</div>
        </div>
      </div>
      <!-- 滚动的币种价格：内容脱离 Vue 模板，由 JS 直接管理 DOM -->
      <div class="ticker-scroll-area">
        <div class="ticker-track" ref="tickerTrack"></div>
      </div>
    </div>

    <!-- 个人中心 / 量化机器人收益 / 热门活动 -->
    <el-row :gutter="20">
      <!-- 左侧：个人中心 + 量化机器人收益 + 资产曲线 -->
      <el-col :span="18">
    <el-row :gutter="20" class="pair-row">
      <el-col :span="15">
        <el-card shadow="hover" class="panel-card profit-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">个人中心</span>
            </div>
          </template>
          <div class="personal-center">
            <!-- 交易所绑定卡片 -->
            <div class="exchange-cards" :class="{ 'single-bound': okxBound }">
              <!-- OKX -->
              <div class="exchange-card" :class="{ 'exchange-card--bound': okxBound }">
                <div class="exchange-header">
                  <div class="exchange-logo okx-logo">
                    <img :src="okxLogo" alt="OKX" class="exchange-logo-img" />
                  </div>
                  <div class="exchange-info">
                    <div class="exchange-name">OKX</div>
                    <el-tag :type="okxBound ? 'success' : 'info'" size="small">
                      {{ okxBound ? '已绑定' : '未绑定' }}
                    </el-tag>
                  </div>
                </div>
                <!-- 已绑定：统计网格 -->
                <div v-if="okxBound" class="bound-stats">
                  <div class="bound-stat">
                    <div class="bound-stat-label">UID</div>
                    <div class="bound-stat-value">{{ apiConfig.okx_uid || '--' }}</div>
                  </div>
                  <div class="bound-stat">
                    <div class="bound-stat-label">账户余额</div>
                    <div class="bound-stat-value" :class="{ 'stat-loading': accountBalance === null }">{{ accountBalance === null ? '...' : '$' + formatNum(accountBalance) }}</div>
                  </div>
                  <div class="bound-stat">
                    <div class="bound-stat-label">策略</div>
                    <div class="bound-stat-value accent" :class="{ 'stat-loading': runningStrategies === null }">{{ runningStrategies === null ? '...' : runningStrategies + ' 个' }}</div>
                  </div>
                  <div class="bound-stat">
                    <div class="bound-stat-label">总盈亏</div>
                    <div class="bound-stat-value" :class="[totalStrategyProfit === null ? '' : (totalStrategyProfit >= 0 ? 'stat-up' : 'stat-down'), { 'stat-loading': totalStrategyProfit === null }]">
                      {{ totalStrategyProfit === null ? '...' : (totalStrategyProfit >= 0 ? '+' : '') + '$' + formatNum(totalStrategyProfit) }}
                    </div>
                  </div>
                </div>
                <div v-if="okxBound" class="bound-unbind" @click="unbindExchange('okx')">
                  <span class="unbind-icon">❌</span>
                  <span class="unbind-text">解除绑定</span>
                </div>
                <div v-if="!okxBound" class="exchange-actions">
                  <a :href="registerUrls.okx || '#'" target="_blank" class="register-btn">注册</a>
                  <el-button type="primary" size="small" @click="showBindDialog('okx')">绑定</el-button>
                </div>
              </div>

              <!-- Bitget & HTX: OKX未绑定时显示 -->
              <template v-if="!okxBound">
              <div class="exchange-card">
                <div class="exchange-header">
                  <div class="exchange-logo bitget-logo">
                    <span class="logo-text">BG</span>
                  </div>
                  <div class="exchange-info">
                    <div class="exchange-name">Bitget</div>
                    <el-tag type="info" size="small">未绑定</el-tag>
                  </div>
                </div>
                <div class="exchange-actions">
                  <a v-if="registerUrls.bitget" :href="registerUrls.bitget" target="_blank" class="register-btn">注册</a>
                  <el-button type="primary" size="small" disabled>绑定</el-button>
                </div>
              </div>

              <div class="exchange-card">
                <div class="exchange-header">
                  <div class="exchange-logo htx-logo">
                    <span class="logo-text">HTX</span>
                  </div>
                  <div class="exchange-info">
                    <div class="exchange-name">HTX</div>
                    <el-tag type="info" size="small">未绑定</el-tag>
                  </div>
                </div>
                <div class="exchange-actions">
                  <a v-if="registerUrls.htx" :href="registerUrls.htx" target="_blank" class="register-btn">注册</a>
                  <el-button type="primary" size="small" disabled>绑定</el-button>
                </div>
              </div>
            </template>
            </div>
            <div v-if="!okxBound" class="exchange-tip">
              <img src="/images/warning.png" class="tip-icon" alt="⚠" />
              注意：以上三个交易所只能同时绑定一个
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="9">
        <el-card shadow="hover" class="panel-card robot-panel">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">
                <span class="robot-title-icon">🤖</span>
                量化机器人收益
              </span>
              <router-link to="/strategy/robots" class="robot-view-all">
                查看全部
                <span class="view-all-arrow">→</span>
              </router-link>
            </div>
          </template>
          <div class="robot-summary-list" v-loading="robotsLoading">
            <template v-if="robotsData.length > 0">
              <!-- 总览头部 -->
              <div class="robot-overview">
                <div class="rov-item">
                  <span class="rov-label">运行中</span>
                  <span class="rov-value rov-running">{{ runningRobotCount }}</span>
                </div>
                <div class="rov-divider"></div>
                <div class="rov-item">
                  <span class="rov-label">总盈亏</span>
                  <span class="rov-value" :class="totalRobotPnl >= 0 ? 'val-up' : 'val-down'">
                    {{ totalRobotPnl >= 0 ? '+' : '' }}{{ totalRobotPnl.toFixed(2) }}U
                  </span>
                </div>
                <div class="rov-divider"></div>
                <div class="rov-item">
                  <span class="rov-label">平均胜率</span>
                  <span class="rov-value rov-winrate">{{ avgWinRate.toFixed(1) }}%</span>
                </div>
              </div>

              <!-- 机器人列表 -->
              <div class="robot-item" v-for="r in robotsData" :key="r.id">
                <div class="ri-left">
                  <div class="ri-avatar" :class="r.is_running ? 'ri-avatar-active' : ''">
                    <span class="ri-emoji">{{ r.is_running ? '🤖' : '⏸️' }}</span>
                  </div>
                  <div class="ri-info">
                    <div class="ri-name">{{ r.name }}</div>
                    <div class="ri-meta">
                      <span class="ri-strategies">{{ r.strategy_count || 0 }}个策略</span>
                      <span class="ri-dot">·</span>
                      <span class="ri-monthly" :class="calcRobotMonthly(r) >= 0 ? 'val-up' : 'val-down'">
                        月化{{ calcRobotMonthly(r) >= 0 ? '+' : '' }}{{ calcRobotMonthly(r).toFixed(1) }}%
                      </span>
                    </div>
                  </div>
                </div>
                <div class="ri-right">
                  <div class="ri-pnl" :class="r.total_pnl >= 0 ? 'pnl-up' : 'pnl-down'">
                    {{ r.total_pnl >= 0 ? '+' : '' }}{{ r.total_pnl.toFixed(2) }}U
                  </div>
                  <div class="ri-stats">
                    <span class="ri-winrate" :class="r.win_rate >= 70 ? 'win-high' : ''">
                      胜率 {{ r.win_rate.toFixed(1) }}%
                    </span>
                    <span class="ri-trades">{{ r.trade_count }}笔</span>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="placeholder-block">
              <el-empty description="暂无机器人" :image-size="48" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 资产曲线 -->
    <el-card shadow="hover" class="panel-card" style="margin-top: 16px;">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">资产曲线</span>
          <el-radio-group v-model="pnlPeriod" size="small" @change="fetchPnlCurve">
            <el-radio-button label="7d">7天</el-radio-button>
            <el-radio-button label="30d">30天</el-radio-button>
            <el-radio-button label="90d">90天</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div class="chart-area" ref="pnlChartRef"></div>
    </el-card>
      </el-col>
      <!-- 右侧：热门活动 -->
      <el-col :span="6">
        <div class="hot-activity-section">
          <div class="panel-header">
            <span class="panel-title">
              <img src="/images/fire.png" class="title-icon" alt="🔥" />
              热门活动
            </span>
          </div>
          <div class="activity-banner">
            <img v-if="activityBannerUrl" :src="activityBannerUrl" alt="活动横幅" class="banner-image" />
            <div v-else class="banner-placeholder">图片展示区</div>
          </div>
          <div class="activity-list" v-if="!hotActivityLoading">
            <div class="activity-item" v-for="(item, idx) in hotActivities" :key="idx">
              <div class="activity-icon">
                <img :src="item.icon" alt="" class="activity-icon-img" />
              </div>
              <div class="activity-info">
                <div class="activity-title">{{ item.title }}</div>
                <div class="activity-desc">{{ item.desc }}</div>
                <div class="activity-status" :class="item.statusType">{{ item.status }}</div>
              </div>
              <span v-if="item.badge" class="activity-badge" :class="'badge-' + item.badgeType">{{ item.badge }}</span>
            </div>
          </div>
          <div class="activity-list" v-else>
            <div class="activity-item activity-skeleton" v-for="n in 3" :key="n">
              <div class="skeleton-icon"></div>
              <div class="skeleton-info">
                <div class="skeleton-line w-60"></div>
                <div class="skeleton-line w-90"></div>
                <div class="skeleton-line w-35"></div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 最近交易 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">最近交易</span>
              <el-button text size="small" type="primary">查看全部</el-button>
            </div>
          </template>
          <div class="trade-list">
            <div class="trade-item" v-for="t in recentTrades" :key="t.id">
              <div class="trade-left">
                <el-tag :type="t.side === '买入' ? 'danger' : 'success'" size="small" effect="plain" round>
                  {{ t.side }}
                </el-tag>
                <span class="trade-symbol">{{ t.symbol }}</span>
              </div>
              <div class="trade-right">
                <span class="trade-price">{{ t.price || '--' }}</span>
                <span class="trade-pnl" v-if="t.pnl" :class="t.pnl >= 0 ? 'pnl-up' : 'pnl-down'">
                  {{ t.pnl >= 0 ? '+' : '' }}{{ t.pnl }}
                </span>
              </div>
            </div>
            <el-empty v-if="recentTrades.length === 0" description="暂无交易记录" :image-size="40" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- OKX 绑定对话框 -->
    <el-dialog
      v-model="bindDialogVisible"
      width="380px"
      :close-on-click-modal="false"
      :show-close="true"
      class="bind-dialog"
      align-center
      destroy-on-close
    >
      <!-- 自定义标题 -->
      <template #header>
        <div class="bind-dialog-header">
          <span class="bind-title">OKX API 登录</span>
        </div>
      </template>

      <div class="bind-dialog-content">
        <!-- 提示信息栏 -->
        <div class="bind-notice">
          交易所提供的ApiKey与Secret非常重要，请安全保管，我们不会上传您的信息，确保资产安全。
        </div>
        <!-- 表单 -->
        <el-form :model="bindForm" label-position="top" class="bind-form" :hide-required-asterisk="true">
          <el-form-item>
            <template #label>
              <span class="form-label">API Key</span>
            </template>
            <el-input 
              v-model="bindForm.key" 
              placeholder="请输入 API Key" 
              clearable 
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="form-label">Secret Key</span>
            </template>
            <el-input 
              v-model="bindForm.secret" 
              type="password" 
              placeholder="请输入 Secret Key" 
              show-password 
              clearable 
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="form-label">Passphrase</span>
            </template>
            <el-input 
              v-model="bindForm.passphrase" 
              type="password" 
              placeholder="请输入 Passphrase" 
              show-password 
              clearable 
            />
          </el-form-item>
        </el-form>
        <!-- 教程链接 -->
        <div class="bind-tutorial">
          <a href="https://www.okx.com/cn/account/my-api" target="_blank">不知道如何获取API? 查看教程</a>
        </div>
        <!-- 确认按钮 -->
        <el-button 
          type="primary" 
          class="bind-submit-btn" 
          :loading="bindLoading" 
          @click="confirmBind"
        >
          确认登录
        </el-button>
      </div>
      <template #footer>
        <span></span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, WarningFilled } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'
import * as echarts from 'echarts'
import okxLogo from '../assets/okx-logo.png'
import { useRouter } from 'vue-router'

const { on: wsOn, off: wsOff, connected: wsConnected } = useWebSocket()
const router = useRouter()

const pnlPeriod = ref('30d')
const pnlChartRef = ref(null)
let pnlChart = null

const hasApiKey = ref(localStorage.getItem('okx_bound') === '1')  // 先用 localStorage 快速渲染，防止闪烁
const accountBalance = ref(null)
const registerUrls = ref({ okx: '', bitget: '', htx: '' })
const unrealizedPnl = ref(null)
const fundingBalance = ref(0)
const currencies = ref([])
const positions = ref([])
const recentTrades = ref([])
const runningStrategies = ref(null)
const totalStrategyProfit = ref(null)

// 量化机器人数据
const robotsData = ref([])
const robotsLoading = ref(true)

// 机器人统计计算属性
const runningRobotCount = computed(() => robotsData.value.filter(r => r.is_running).length)
const totalRobotPnl = computed(() => robotsData.value.reduce((s, r) => s + (r.total_pnl || 0), 0))
const avgWinRate = computed(() => {
  if (robotsData.value.length === 0) return 0
  return robotsData.value.reduce((s, r) => s + (r.win_rate || 0), 0) / robotsData.value.length
})

function calcRobotMonthly(robot) {
  if (!robot.initial_capital || !robot.created_at) return 0
  const totalReturn = (robot.total_pnl / robot.initial_capital) * 100
  const createdAt = new Date(robot.created_at)
  const now = new Date()
  const daysRunning = Math.max(1, Math.floor((now - createdAt) / (1000 * 60 * 60 * 24)))
  return (totalReturn / daysRunning) * 30
}

// API配置相关
const apiConfig = ref({
  key: '',
  secret: '',
  passphrase: '',
  sandbox: true,
  okx_uid: localStorage.getItem('okx_bound_uid') || '',
})
const savingApi = ref(false)
const testingApi = ref(false)
const refreshingUid = ref(false)
const testResult = ref(null)

// 热门活动数据 - setup 阶段从 localStorage 读取，首帧即有数据
const CACHE_KEY = 'hot_activities_cache'

function _readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) { /* ignore */ }
  return null
}
const _cached = _readCache()

const hotActivities = ref((_cached && _cached.activities) ? _cached.activities : [])
const activityBannerUrl = ref((_cached && _cached.banner_url) ? _cached.banner_url : '')
const hotActivityLoading = ref(!_cached)

function saveActivitiesToCache(bannerUrl, activities) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ banner_url: bannerUrl, activities }))
  } catch (e) { /* ignore */ }
}

async function fetchHotActivities() {
  try {
    const res = await api.get('/activities')
    const activities = (res.activities || []).map(a => ({
      icon: a.icon_url,
      title: a.title,
      desc: a.desc,
      status: a.status,
      statusType: a.status_type || 'status-active',
      badge: a.badge,
      badgeType: a.badge_type || '',
    }))
    activityBannerUrl.value = res.banner_url || ''
    hotActivities.value = activities
    saveActivitiesToCache(res.banner_url, activities)
  } catch (e) {
    console.error('Failed to load hot activities:', e)
  } finally {
    hotActivityLoading.value = false
  }
}

// 绑定对话框相关
const bindDialogVisible = ref(false)
const bindLoading = ref(false)
const bindForm = ref({
  key: '',
  secret: '',
  passphrase: '',
  sandbox: false, // 强制使用实盘
})

// OKX 是否已绑定
const okxBound = computed(() => {
  return hasApiKey.value === true
})

// 实时价格滚动条 — 纯 CSS 动画 + DOM 直操作，脱离 Vue 响应式
const tickerTrack = ref(null)
const tickerCoins = [
  { symbol: 'BTC', price: 0, change: 0 },
  { symbol: 'ETH', price: 0, change: 0 },
  { symbol: 'BNB', price: 0, change: 0 },
  { symbol: 'SOL', price: 0, change: 0 },
  { symbol: 'XRP', price: 0, change: 0 },
  { symbol: 'ADA', price: 0, change: 0 },
  { symbol: 'DOGE', price: 0, change: 0 },
  { symbol: 'DOT', price: 0, change: 0 },
]
let tickerBuilt = false
let tickerFlushTimer = null    // 限频刷新定时器
let pendingTickerUpdates = {}  // 暂存待更新数据

// ── 无缝滚动：纯 CSS animation 方案（固定宽度容器，永不变形） ──
// 核心改进：给 .ticker-price 用固定宽度容器，价格文本更新不会改变 DOM 布局宽度
// 这样 CSS @keyframes 的移动距离始终精确，无需在运行中重新测量

function buildTickerDOM() {
  const track = tickerTrack.value
  if (!track || tickerBuilt) return

  const itemsHTML = tickerCoins.map(c => `<div class="ticker-item"><span class="ticker-symbol">${c.symbol}</span><span class="ticker-price" data-sym="${c.symbol}">$0.00</span><span class="ticker-change" data-sym-chg="${c.symbol}">0.00%</span></div>`).join('')

  // 放 4 份内容：确保在任何屏幕宽度下都能无缝循环
  track.innerHTML = `<div class="ticker-content">${itemsHTML}</div><div class="ticker-content" aria-hidden="true">${itemsHTML}</div><div class="ticker-content" aria-hidden="true">${itemsHTML}</div><div class="ticker-content" aria-hidden="true">${itemsHTML}</div>`
  tickerBuilt = true
}

function flushTickerUpdates() {
  const track = tickerTrack.value
  if (!track) return

  for (const [symbol, data] of Object.entries(pendingTickerUpdates)) {
    const priceStr = '$' + fmtNum(data.price, data.price < 1 ? 4 : 2)
    const changeStr = (data.change >= 0 ? '+' : '') + data.change.toFixed(2) + '%'
    const isUp = data.change >= 0

    track.querySelectorAll(`[data-sym="${symbol}"]`).forEach(el => {
      el.textContent = priceStr
    })
    track.querySelectorAll(`[data-sym-chg="${symbol}"]`).forEach(el => {
      el.textContent = changeStr
      el.style.color = isUp ? '#3fb950' : '#f85149'
      el.style.backgroundColor = isUp ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)'
    })
  }
  pendingTickerUpdates = {}
  tickerFlushTimer = null
}

function remeasureAndSetAnimation() {
  // 不需要重新测量——.ticker-price-box 固定宽度保证布局稳定
}

function scheduleTickerUpdate(symbol, price, change) {
  pendingTickerUpdates[symbol] = { price, change }
  if (!tickerFlushTimer) {
    tickerFlushTimer = setTimeout(flushTickerUpdates, 2000)
  }
}

// 格式化数字（滚动条专用）
function fmtNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '--'
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

// 启动滚动动画
function startTickerAnimation() {
  const track = tickerTrack.value
  if (!track || !tickerBuilt) return

  // 测量单份内容宽度
  void track.offsetWidth  // 强制 reflow
  const contents = track.querySelectorAll('.ticker-content')
  if (contents.length < 2) return
  const r1 = contents[0].getBoundingClientRect()
  const r2 = contents[1].getBoundingClientRect()
  const w = r2.left - r1.left
  if (w < 50) return

  // 设置 CSS 变量：移动 2 份内容宽度（4 份内容中前 2 份 = 一个完整循环）
  track.style.setProperty('--ticker-w', w + 'px')
  // 根据宽度计算合适的动画时长（30px/s 基准速度）
  const duration = (w * 2) / 18
  track.style.setProperty('--ticker-duration', duration + 's')
  track.classList.add('ticker-animated')
}

function stopTickerAnimation() {
  const track = tickerTrack.value
  if (track) track.classList.remove('ticker-animated')
}
const fearGreedIndex = ref(50)
const fearGreedLabel = computed(() => {
  const val = fearGreedIndex.value
  if (val <= 25) return '极度恐惧'
  if (val <= 45) return '恐惧'
  if (val <= 55) return '中性'
  if (val <= 75) return '贪婪'
  return '极度贪婪'
})
const fearGreedClass = computed(() => {
  const val = fearGreedIndex.value
  if (val <= 25) return 'extreme-fear'
  if (val <= 45) return 'fear'
  if (val <= 55) return 'neutral'
  if (val <= 75) return 'greed'
  return 'extreme-greed'
})
const fearGreedEmoji = computed(() => {
  const val = fearGreedIndex.value
  if (val <= 25) return '😱'
  if (val <= 45) return '😰'
  if (val <= 55) return '😐'
  if (val <= 75) return '😊'
  return '🤑'
})

// 格式化数字（通用，Dashboard 其他地方也用）
function formatNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '--'
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

// ─── WebSocket 实时数据回调 ───

function onTicker(data) {
  if (data && data.price && data.symbol) {
    const symbol = data.symbol.replace('-USDT', '')
    const coin = tickerCoins.find(c => c.symbol === symbol)
    if (coin) {
      coin.price = data.price
      if (data.change_24h !== undefined) coin.change = data.change_24h
      // 限频更新 DOM，避免打断 CSS 动画
      scheduleTickerUpdate(symbol, data.price, data.change_24h ?? coin.change)
    }
  }
}

function onAccount(data) {
  if (data && data.total_equity !== undefined) {
    accountBalance.value = data.total_equity
    if (data.total_unrealized_pnl !== undefined) {
      unrealizedPnl.value = data.total_unrealized_pnl
    }
    if (data.details) {
      currencies.value = data.details
    }
  }
}

function onPosition(data) {
  if (data && data.positions) {
    positions.value = data.positions
  }
}

function onTrade(data) {
  if (data) {
    // 新成交推送到最近交易列表头部
    recentTrades.value.unshift({
      id: Date.now(),
      side: data.side === 'buy' ? '买入' : '卖出',
      symbol: data.symbol,
      price: data.price ? '$' + formatNum(data.price) : '--',
      pnl: null,
    })
    if (recentTrades.value.length > 10) {
      recentTrades.value = recentTrades.value.slice(0, 10)
    }
  }
}

function onSignal(data) {
  // 策略信号可以触发 Dashboard 数据刷新
  if (data && (data.signal === 'open_long' || data.signal === 'open_short' ||
      data.signal === 'close_long' || data.signal === 'close_short')) {
    // 信号触发后刷新持仓和账户
    fetchOverview()
  }
}

async function fetchOverview() {
  try {
    const res = await api.get('/dashboard/overview')
    hasApiKey.value = res.has_api_key

    // 更新币种价格
    if (res.prices) {
      for (const [symbol, data] of Object.entries(res.prices)) {
        const coinSymbol = symbol.replace('-USDT', '')
        const coin = tickerCoins.find(c => c.symbol === coinSymbol)
        if (coin && data.price > 0) {
          coin.price = data.price
          coin.change = data.change_24h || 0
          scheduleTickerUpdate(coinSymbol, data.price, coin.change)
        }
      }
      // 始终立即刷新一次，确保价格和宽度在动画启动前就正确
      flushTickerUpdates()
    }

    // 更新恐惧贪婪指数
    if (res.fear_greed_index !== undefined) {
      fearGreedIndex.value = res.fear_greed_index
    }

    // 账户余额
    if (res.account_balance !== null) {
      accountBalance.value = res.account_balance
      if (res.unrealized_pnl !== null) {
        unrealizedPnl.value = res.unrealized_pnl
      }
    }

    // 持仓
    positions.value = res.positions || []

    // 资金账户
    if (res.funding_balance !== null) {
      fundingBalance.value = res.funding_balance
    }

    // 币种明细
    currencies.value = res.currencies || []

    // 策略统计
    runningStrategies.value = res.running_strategies ?? 0
    totalStrategyProfit.value = res.total_strategy_profit ?? 0
  } catch (e) {
    console.error('Dashboard overview error:', e)
  }
}

async function fetchPnlCurve() {
  try {
    const days = parseInt(pnlPeriod.value)
    const res = await api.get('/dashboard/pnl_curve', { params: { days } })
    const data = res.data || []
    await nextTick()
    renderPnlChart(data)
  } catch (e) {
    console.error('PnL curve error:', e)
  }
}

function renderPnlChart(data) {
  if (!pnlChartRef.value) return
  if (!pnlChart) {
    pnlChart = echarts.init(pnlChartRef.value)
  }
  // 动态读取主题CSS变量
  const cs = getComputedStyle(document.documentElement)
  const textMuted = cs.getPropertyValue('--text-muted').trim() || '#86909c'
  const borderPrimary = cs.getPropertyValue('--border-primary').trim() || '#e5e6eb'
  if (data.length === 0) {
    pnlChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: textMuted, fontSize: 14 } },
      xAxis: { show: false }, yAxis: { show: false }, series: []
    })
    return
  }
  const dates = data.map(d => d.date)
  const values = data.map(d => d.equity)
  pnlChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const p = params[0]
        return `${p.axisValue}<br/>权益: <b>$${formatNum(p.value)}</b>`
      }
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11, color: textMuted }, axisLine: { lineStyle: { color: borderPrimary } } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11, color: textMuted, formatter: v => '$' + (v >= 1000 ? (v/1000).toFixed(1) + 'k' : v.toFixed(0)) }, splitLine: { lineStyle: { color: borderPrimary } } },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#f7931a', width: 2.5 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(247,147,26,0.25)' },
          { offset: 1, color: 'rgba(247,147,26,0.02)' },
        ])
      },
    }]
  })
}

async function fetchRecentTrades() {
  try {
    const res = await api.get('/dashboard/recent_trades', { params: { limit: 10 } })
    recentTrades.value = res.trades || []
  } catch (e) {
    console.error('Recent trades error:', e)
  }
}

async function fetchRobotsSummary() {
  robotsLoading.value = true
  try {
    const res = await api.get('/robots/dashboard/summary')
    robotsData.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('Robots summary error:', e)
    robotsData.value = []
  } finally {
    robotsLoading.value = false
  }
}

function handleResize() {
  pnlChart?.resize()
}

function onThemeChange() {
  // 主题变更后延迟重绘图表，等待CSS变量生效
  setTimeout(() => {
    fetchPnlCurve()
  }, 100)
}

// ─── API 配置管理 ───

async function loadApiConfig() {
  try {
    const res = await api.get('/settings/api')
    // 注册链接（无论是否绑定API都加载）
    registerUrls.value = {
      okx: res.okx_register_url || '',
      bitget: res.bitget_register_url || '',
      htx: res.htx_register_url || '',
    }
    if (res.key) {
      apiConfig.value.key = res.key
      apiConfig.value.secret = res.secret ? '••••••••' : ''
      apiConfig.value.passphrase = res.passphrase ? '••••••••' : ''
      apiConfig.value.sandbox = res.sandbox
      apiConfig.value.okx_uid = res.okx_uid || ''
      hasApiKey.value = true
      localStorage.setItem('okx_bound', '1')
      localStorage.setItem('okx_bound_uid', apiConfig.value.okx_uid)
    } else {
      hasApiKey.value = false
      localStorage.removeItem('okx_bound')
      localStorage.removeItem('okx_bound_uid')
    }
  } catch (e) {
    console.error('加载API配置失败:', e)
  }
}

async function saveApiConfig() {
  savingApi.value = true
  try {
    const res = await api.post('/settings/api', {
      key: apiConfig.value.key,
      secret: apiConfig.value.secret,
      passphrase: apiConfig.value.passphrase,
      sandbox: apiConfig.value.sandbox,
    })
    ElMessage.success('API 配置已保存')
    // 更新UID显示
    if (res.okx_uid) {
      apiConfig.value.okx_uid = res.okx_uid
      ElMessage.success(`OKX UID 已自动获取: ${res.okx_uid}`)
    }
    testResult.value = null
    // 重新加载账户数据
    await fetchOverview()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingApi.value = false
  }
}

async function testConnection() {
  testingApi.value = true
  testResult.value = null
  try {
    const res = await api.post('/settings/test-connection')
    testResult.value = {
      success: true,
      message: `连接成功! 账户权益: $${res.equity?.toLocaleString() || '0'}`,
    }
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    testResult.value = {
      success: false,
      message: `连接失败: ${detail}`,
    }
  } finally {
    testingApi.value = false
  }
}

async function refreshUid() {
  refreshingUid.value = true
  try {
    const res = await api.post('/settings/refresh-uid')
    apiConfig.value.okx_uid = res.okx_uid
    ElMessage.success(`OKX UID 已刷新: ${res.okx_uid}`)
  } catch (e) {
    ElMessage.error('刷新失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    refreshingUid.value = false
  }
}

async function unbindApi() {
  try {
    await ElMessageBox.confirm(
      '确定要解除OKX API绑定吗？解除后需要重新配置API Key。',
      '确认解除绑定',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    // 清空API配置
    apiConfig.value = {
      key: '',
      secret: '',
      passphrase: '',
      sandbox: true,
      okx_uid: '',
    }
    hasApiKey.value = false
    localStorage.removeItem('okx_bound')
    localStorage.removeItem('okx_bound_uid')
    testResult.value = null

    // 调用后端清空配置
    await api.post('/settings/api', {
      key: '',
      secret: '',
      passphrase: '',
      sandbox: true,
    })

    ElMessage.success('已解除OKX API绑定')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('解除绑定失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

// ─── 交易所绑定管理 ───

function showBindDialog(exchange) {
  if (exchange === 'okx') {
    bindForm.value = {
      key: '',
      secret: '',
      passphrase: '',
      sandbox: false,
    }
    bindDialogVisible.value = true
  } else {
    ElMessage.info(`${exchange.toUpperCase()} 绑定功能即将上线`)
  }
}

async function confirmBind() {
  if (!bindForm.value.key || !bindForm.value.secret || !bindForm.value.passphrase) {
    ElMessage.warning('请填写完整的 API Key、Secret Key 和 Passphrase')
    return
  }

  bindLoading.value = true
  try {
    const res = await api.post('/settings/api', {
      key: bindForm.value.key,
      secret: bindForm.value.secret,
      passphrase: bindForm.value.passphrase,
      sandbox: bindForm.value.sandbox,
    })

    // 更新配置状态
    apiConfig.value.key = bindForm.value.key
    apiConfig.value.secret = '••••••••'
    apiConfig.value.passphrase = '••••••••'
    apiConfig.value.sandbox = bindForm.value.sandbox
    if (res.okx_uid) {
      apiConfig.value.okx_uid = res.okx_uid
    }
    hasApiKey.value = true
    localStorage.setItem('okx_bound', '1')
    localStorage.setItem('okx_bound_uid', apiConfig.value.okx_uid)

    bindDialogVisible.value = false
    ElMessage.success('OKX API 绑定成功')
    if (res.okx_uid) {
      ElMessage.success(`OKX UID: ${res.okx_uid}`)
    }

    // 刷新账户数据
    await fetchOverview()
  } catch (e) {
    ElMessage.error('绑定失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    bindLoading.value = false
  }
}

async function unbindExchange(exchange) {
  if (exchange === 'okx') {
    await unbindApi()
  } else {
    ElMessage.info(`${exchange.toUpperCase()} 解绑功能即将上线`)
  }
}

onMounted(async () => {
  // 先加载配置（快速，设置注册按钮和状态）
  await loadApiConfig()

  // 初始化滚动条
  buildTickerDOM()

  // 以下全部并行执行，不互相等待，不阻塞页面
  fetchOverview()
  fetchHotActivities()
  fetchPnlCurve()
  fetchRecentTrades()
  fetchRobotsSummary()
  startTickerAnimation()

  window.addEventListener('resize', handleResize)
  // 监听主题变更，重绘图表
  window.addEventListener('theme-change', onThemeChange)

  // 注册 WebSocket 实时数据
  wsOn('ticker', onTicker)
  wsOn('account', onAccount)
  wsOn('position', onPosition)
  wsOn('trade', onTrade)
  wsOn('signal', onSignal)

  // 兜底定时刷新（WS断线时每60秒刷新一次概览）
  dashboardTimer = setInterval(async () => {
    if (!wsConnected.value) {
      await fetchOverview()
      await fetchRecentTrades()
    }
  }, 60000)
})

let dashboardTimer = null

onBeforeUnmount(() => {
  stopTickerAnimation()
  if (dashboardTimer) clearInterval(dashboardTimer)
  if (tickerFlushTimer) clearTimeout(tickerFlushTimer)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('theme-change', onThemeChange)
  pnlChart?.dispose()

  // 注销 WebSocket 事件
  wsOff('ticker', onTicker)
  wsOff('account', onAccount)
  wsOff('position', onPosition)
  wsOff('trade', onTrade)
  wsOff('signal', onSignal)
})
</script>

<style scoped>
.dashboard-page { min-height: 100%; }

/* 实时价格滚动条 */
.price-ticker {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 0;
  margin-bottom: 20px;
  display: flex;
  overflow: hidden;
}

/* 恐惧贪婪指数（固定在左边） */
.fear-greed-fixed {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(90deg, rgba(88, 166, 255, 0.08) 0%, rgba(88, 166, 255, 0.02) 100%);
  border-right: 2px solid var(--border-secondary);
}

.fgi-icon {
  font-size: 24px;
  line-height: 1;
}

.fgi-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.fgi-value {
  font-size: 16px;
  font-weight: 800;
  line-height: 1;
}

.fgi-value.extreme-fear {
  color: #f85149;
}

.fgi-value.fear {
  color: #ff9f43;
}

.fgi-value.neutral {
  color: #8b949e;
}

.fgi-value.greed {
  color: #3fb950;
}

.fgi-value.extreme-greed {
  color: #00d26a;
}

.fgi-label {
  font-size: 10px;
  color: var(--text-muted);
}

/* 统计卡片网格 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 18px;
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: var(--card-shadow);
}

.stat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.stat-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-footer {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-up { font-size: 12px; color: #22c55e; font-weight: 600; }
.stat-down { font-size: 12px; color: #ef4444; font-weight: 600; }
.stat-period { font-size: 12px; color: var(--text-muted); }

/* 面板卡片 */
.panel-card { border-radius: 10px; }

/* 量化机器人收益 + 个人中心等高（用父级row flex stretch） */
.pair-row {
  display: flex;
  align-items: stretch;
}
.pair-row > .el-col {
  display: flex;
  flex-direction: column;
}
.pair-row .panel-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.pair-row .panel-card :deep(.el-card__body) {
  flex: 1;
}
.panel-header { display: flex; align-items: center; justify-content: space-between; }
.panel-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }

.placeholder-block {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 量化机器人摘要列表 */
.robot-summary-list {
  display: flex;
  flex-direction: column;
  flex: 1;
}

/* 热门活动 */
.hot-activity-section {
  padding: 0;
}

.hot-activity-section .panel-header {
  margin-bottom: 12px;
}

.activity-banner {
  margin-bottom: 16px;
}

.banner-image {
  width: 100%;
  border-radius: 8px;
  display: block;
}

.banner-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--bg-hover);
  border: 1px dashed var(--border-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.title-icon {
  width: 18px;
  height: 18px;
  margin-right: 4px;
  vertical-align: -3px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  background: var(--activity-card-bg, #ffffff);
  border: 1px solid var(--border-primary);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: all 0.2s ease;
  cursor: pointer;
}

.activity-item:hover {
  border-color: var(--accent);
  border-left-width: 5px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}

.activity-item .activity-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  overflow: hidden;
}

.activity-icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-item .activity-info {
  flex: 1;
  min-width: 0;
}

.activity-item .activity-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
  margin-bottom: 3px;
}

.activity-item .activity-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.activity-item .activity-status {
  font-size: 11px;
  font-weight: 500;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  line-height: 1.5;
}

.activity-status.status-active {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
}

.activity-status.status-upcoming {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.08);
}

.activity-status.status-soon {
  color: var(--text-muted);
  background: var(--bg-hover);
}

.activity-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  line-height: 1.4;
  letter-spacing: 0.5px;
}

.badge-hot {
  color: #fff;
  background: linear-gradient(135deg, #f85149, #ff6b35);
}

.badge-new {
  color: #fff;
  background: linear-gradient(135deg, #409eff, #53a8ff);
}

/* 骨架屏 */
.activity-skeleton {
  pointer-events: none;
}

.skeleton-icon,
.skeleton-line {
  background: linear-gradient(90deg, var(--border-primary) 25%, var(--bg-hover) 50%, var(--border-primary) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 6px;
}

.skeleton-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-line {
  height: 12px;
}

.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-90 { width: 90%; }
.skeleton-line.w-35 { width: 35%; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 个人中心 */
.personal-center { padding: 10px 0; display: flex; flex-direction: column; flex: 1; min-height: 240px; }
.api-config-section { display: flex; flex-direction: column; gap: 16px; }
.config-item { display: flex; align-items: center; gap: 20px; }
.config-label {
  min-width: 90px;
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}
.config-value { display: flex; align-items: center; flex: 1; }
.config-actions { display: flex; gap: 10px; margin-top: 10px; }
.test-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 10px;
}
.test-result.success { background: #e8ffea; color: #00b42a; }
.test-result.error { background: #ffece8; color: #f53f3f; }

/* 交易所绑定卡片 */
.exchange-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  flex: 1;
  align-content: stretch;
}

.exchange-cards.single-bound {
  grid-template-columns: 1fr;
}

.exchange-card {
  background: var(--bg-hover);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.exchange-card:hover {
  background: var(--bg-card-hover);
}

.exchange-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.exchange-header .exchange-logo {
  flex-shrink: 0;
}

.exchange-logo {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.exchange-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.exchange-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 操作按钮行 */
.exchange-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}
.exchange-actions .el-button {
  flex: 1;
  min-width: 0;
  height: 32px;
  font-size: 14px;
}

/* 注册按钮 */
.register-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  padding: 0 15px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  background: #fff;
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
}
.register-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 提示文字 */
.exchange-tip {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
  font-size: 13px;
  color: #e74c3c;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tip-icon {
  width: 16px;
  height: 16px;
  vertical-align: middle;
}

.okx-logo {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  overflow: hidden;
}

.exchange-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.bitget-logo {
  background: linear-gradient(135deg, #0052ff 0%, #0066ff 100%);
}

.htx-logo {
  background: linear-gradient(135deg, #00a651 0%, #00c853 100%);
}

.exchange-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-size: 12px;
  color: var(--text-muted);
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 绑定后的统计网格 */
.bound-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--border-secondary);
}

.bound-stat {
  background: var(--bg-secondary);
  border-radius: 6px;
  padding: 8px 10px;
}

.bound-stat-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.bound-stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.bound-stat-value.accent {
  color: #409eff;
}

.bound-unbind {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 8px;
  background: var(--red-light);
  border: 1px solid rgba(244, 63, 94, 0.3);
  border-radius: 6px;
  color: var(--red);
  cursor: pointer;
  transition: all 0.2s;
  padding: 6px 16px;
  font-size: 13px;
}

.bound-unbind:hover {
  background: rgba(244, 63, 94, 0.15);
  border-color: var(--red);
}

.unbind-icon {
  font-size: 14px;
  line-height: 1;
}

.unbind-text {
  font-size: 14px;
  font-weight: 700;
}

.stat-loading {
  color: var(--text-disabled) !important;
  font-size: 14px !important;
  font-weight: 400 !important;
}

/* 图表区域 */
.chart-area { height: 320px; }

/* 账户资产 */
.asset-list { min-height: 280px; }
.asset-empty {
  height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; color: var(--text-muted);
}
.asset-empty p { margin: 10px 0; font-size: 13px; color: var(--text-muted); }

.asset-total { padding: 4px 0 10px; }
.asset-total-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.asset-total-value { font-size: 26px; font-weight: 700; color: var(--text-primary); }
.asset-pnl { margin-top: 4px; font-size: 12px; }

.asset-divider { height: 1px; background: var(--border-secondary); margin: 8px 0; }

.asset-funding { padding: 4px 0 8px; }

.asset-coins { max-height: 160px; overflow-y: auto; }
.asset-coin {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; border-bottom: 1px solid var(--border-primary);
}
.asset-coin:last-child { border-bottom: none; }
.coin-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.coin-right { text-align: right; }
.coin-equity { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.coin-available { font-size: 11px; color: var(--text-muted); margin-left: 8px; }

/* 持仓盈亏色 */
.pnl-up { color: #ef5350; font-weight: 500; }
.pnl-down { color: #26a69a; font-weight: 500; }
.val-up { color: #ef5350; }
.val-down { color: #26a69a; }

/* 量化机器人面板 */
.robot-panel .panel-header {
  position: relative;
}

.robot-title-icon {
  font-size: 16px;
  margin-right: 2px;
}

.robot-view-all {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.robot-view-all:hover {
  color: var(--accent);
}

.view-all-arrow {
  font-size: 14px;
  transition: transform 0.2s;
}

.robot-view-all:hover .view-all-arrow {
  transform: translateX(3px);
}

/* 机器人总览条 */
.robot-overview {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border-radius: 10px;
  margin-bottom: 12px;
}

.rov-item {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.rov-label {
  font-size: 11px;
  color: var(--text-muted);
}

.rov-value {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}

.rov-running { color: #22c55e; }

.rov-winrate { color: #409eff; }

.rov-divider {
  width: 1px;
  height: 30px;
  background: var(--border-primary);
  flex-shrink: 0;
}

/* 机器人列表项 */
.robot-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 10px;
  transition: all 0.2s;
  margin-bottom: 8px;
}

.robot-item:last-child {
  margin-bottom: 0;
}

.robot-item:hover {
  background: var(--bg-hover);
}

.ri-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.ri-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ri-avatar-active {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(16, 185, 129, 0.1));
}

.ri-emoji { font-size: 18px; }

.ri-info {
  flex: 1;
  min-width: 0;
}

.ri-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ri-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.ri-strategies {
  font-size: 11px;
  color: var(--text-muted);
}

.ri-dot {
  font-size: 10px;
  color: var(--border-primary);
}

.ri-monthly {
  font-size: 11px;
  font-weight: 600;
}

.ri-right {
  text-align: right;
  flex-shrink: 0;
}

.ri-pnl {
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.ri-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.ri-winrate {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.ri-winrate.win-high { color: #22c55e; }

.ri-trades {
  font-size: 11px;
  color: var(--text-muted);
}

/* 交易列表 */
.trade-list { min-height: 240px; max-height: 280px; overflow-y: auto; }
.trade-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 0; border-bottom: 1px solid var(--border-primary);
}
.trade-item:last-child { border-bottom: none; }
.trade-left { display: flex; align-items: center; gap: 8px; }
.trade-symbol { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.trade-right { text-align: right; }
.trade-price { font-size: 13px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.trade-pnl { font-size: 12px; margin-left: 8px; }

/* 响应式 */
@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .stat-grid { grid-template-columns: repeat(1, 1fr); }
}

/* 绑定对话框 */
.bind-dialog :deep(.el-dialog) {
  border-radius: 16px !important;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15) !important;
  overflow: hidden;
  animation: bindDialogIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  transform-origin: center center;
}

@keyframes bindDialogIn {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.3);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

.bind-dialog :deep(.el-overlay) {
  animation: bindOverlayIn 0.35s ease forwards;
}

@keyframes bindOverlayIn {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

.bind-dialog :deep(.el-overlay-dialog) {
  display: flex;
  justify-content: center;
  align-items: center;
}

.bind-dialog :deep(.el-dialog__header) {
  padding: 16px 0 8px 0;
  margin: 0 16px;
}

.bind-dialog :deep(.el-dialog__headerbtn) {
  top: 16px;
  right: 8px;
  font-size: 18px;
  color: var(--text-muted);
}

.bind-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.bind-dialog :deep(.el-dialog__footer) {
  padding: 0;
  display: none;
}

.bind-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.bind-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.bind-dialog-content {
  padding: 0 0 12px;
}

/* 提示信息栏 */
.bind-notice {
  background: var(--accent-light) !important;
  padding: 10px 14px !important;
  margin: 0 0 16px 0 !important;
  line-height: 1.5;
  color: var(--text-primary);
  font-size: 12px;
  border-left: 4px solid var(--accent) !important;
  border-radius: 0 !important;
}

/* 表单 */
.bind-form {
  padding: 0 16px;
}

.bind-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.bind-form :deep(.el-input__wrapper) {
  background: var(--bg-input);
  border-radius: 6px;
  box-shadow: 0 0 0 1px var(--border-primary) inset;
  padding: 0 12px;
  height: 40px;
}

.bind-form :deep(.el-input__inner) {
  font-size: 13px;
  color: var(--text-primary);
}

.bind-form :deep(.el-input__inner::placeholder) {
  color: var(--text-muted);
}

/* 教程链接 */
.bind-tutorial {
  text-align: center;
  margin: 4px 16px 14px;
}

.bind-tutorial a {
  color: var(--accent);
  text-decoration: none;
  font-size: 12px;
}

.bind-tutorial a:hover {
  text-decoration: underline;
}

/* 确认按钮 */
.bind-submit-btn {
  display: block;
  width: calc(100% - 32px);
  margin: 0 16px;
  height: 40px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
}
</style>

<!-- 非scoped样式：ticker滚动条由innerHTML动态创建，scoped属性无法匹配 -->
<style>
/* 滚动区域 — 必须非scoped，因为子元素由 innerHTML 创建 */
.ticker-scroll-area {
  flex: 1;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
}

.ticker-track {
  display: flex;
  width: max-content;
  align-items: center;
}

/* 激活动画 */
.ticker-track.ticker-animated {
  animation: tickerScroll var(--ticker-duration, 80s) linear infinite;
  will-change: transform;
}

.ticker-track.ticker-animated:hover {
  animation-play-state: paused;
}

@keyframes tickerScroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(calc(var(--ticker-w, 1200px) * -2)); }
}

.ticker-content {
  display: flex;
  gap: 0;
  align-items: center;
  flex-shrink: 0;
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 8px;
  white-space: nowrap;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 每个 ticker-item 之间用竖线分隔 */
.ticker-item + .ticker-item {
  border-left: 1px solid var(--border-secondary);
}

/* ticker-content 之间的分隔也用竖线 */
.ticker-content + .ticker-content > .ticker-item:first-child {
  border-left: 1px solid var(--border-secondary);
}

.ticker-price {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  display: inline-block;
  min-width: 42px;
}

.ticker-change {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  display: inline-block;
  min-width: 50px;
  text-align: center;
  /* 默认色 */
  color: #8b949e;
  background: transparent;
}

.ticker-symbol {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

/* Element Plus Dialog 覆盖 */
.el-dialog.bind-dialog {
  border-radius: 16px !important;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.18) !important;
  overflow: hidden;
  animation: bindDialogIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  transform-origin: center center;
  padding: 0 !important;
}

@keyframes bindDialogIn {
  0% {
    opacity: 0;
    transform: scale(0.3);
  }
  60% {
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.el-dialog.bind-dialog .el-dialog__header {
  padding: 16px 0 8px !important;
  margin: 0 12px !important;
}

.el-dialog.bind-dialog .el-dialog__body {
  padding: 0 !important;
  margin: 0 !important;
}

.el-dialog.bind-dialog .bind-dialog-content {
  padding: 0 !important;
  margin: 0 !important;
}

.el-dialog.bind-dialog .bind-notice {
  background: var(--accent-light) !important;
  padding: 10px 14px !important;
  margin: 0 0 16px 0 !important;
  border-left: 4px solid var(--accent) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

.el-dialog.bind-dialog .bind-form {
  padding: 0 12px !important;
}

.el-dialog.bind-dialog .bind-tutorial {
  margin: 4px 12px 14px !important;
}

.el-dialog.bind-dialog .bind-submit-btn {
  margin: 0 12px !important;
  width: calc(100% - 24px) !important;
}
</style>
