<template>
  <el-container class="app-container" :class="{ dark: isDark, light: !isDark }">
    <!-- 未登录提示条 -->
    <transition name="slide-down">
      <div v-if="showLoginHint" class="login-hint-bar">
        <span class="hint-text">您还未登录，<strong>{{ loginCountdown }}</strong> 秒后跳转到登录页</span>
        <el-button type="primary" size="small" @click="goLogin">立即登录</el-button>
        <el-button size="small" @click="cancelRedirect">继续浏览</el-button>
      </div>
    </transition>

    <!-- 移动端遮罩 -->
    <div v-if="isMobile && !isCollapsed" class="mobile-overlay" @click="isCollapsed = true"></div>

    <!-- 侧边栏 -->
    <el-aside
      :width="isCollapsed ? '64px' : '220px'"
      class="app-aside"
      :class="{ 'mobile-aside': isMobile, 'mobile-aside-hidden': isMobile && isCollapsed }"
    >
      <!-- Logo -->
      <div class="logo-area" @click="router.push('/dashboard')" style="cursor: pointer;">
        <div class="logo-badge" v-if="!siteLogo">₿</div>
        <img v-else :src="siteLogo" class="logo-img" />
        <transition name="fade-text">
          <div v-show="!isCollapsed" class="logo-text-group">
            <span class="logo-text">{{ siteName }}</span>
            <span class="logo-sub">{{ siteSlogan }}</span>
          </div>
        </transition>
      </div>

      <!-- 导航菜单 -->
      <nav class="nav-list">
        <template v-for="item in filteredMenu" :key="item.path">
          <!-- 有子菜单的项 -->
          <div v-if="item.children" class="nav-group">
            <div class="nav-item" :class="{ active: isChildActive(item) }" @click="handleParentMenuClick(item)">
              <div class="nav-icon-wrap">
                <el-icon :size="18"><component :is="item.icon" /></el-icon>
              </div>
              <transition name="fade-text">
                <span v-show="!isCollapsed" class="nav-label">{{ item.title }}</span>
              </transition>
              <el-icon v-show="!isCollapsed" class="nav-arrow" :class="{ expanded: expandedMenus.includes(item.path) }">
                <ArrowRight />
              </el-icon>
            </div>
            <transition name="submenu">
              <div v-show="!isCollapsed && expandedMenus.includes(item.path)" class="nav-submenu">
                <router-link
                  v-for="child in item.children"
                  :key="child.path"
                  :to="child.path"
                  class="nav-subitem"
                  :class="{ active: currentRoute === child.path }"
                  @click="onNavClick"
                >
                  <el-icon v-if="child.icon" :size="16" class="nav-subicon"><component :is="child.icon" /></el-icon>
                  <span class="nav-label">{{ child.title }}</span>
                </router-link>
              </div>
            </transition>
          </div>
          <!-- 普通菜单项 -->
          <router-link
            v-else
            :to="item.path"
            class="nav-item"
            :class="{ active: currentRoute === item.path }"
            @click="onNavClick"
          >
            <div class="nav-icon-wrap">
              <el-icon :size="18"><component :is="item.icon" /></el-icon>
            </div>
            <transition name="fade-text">
              <span v-show="!isCollapsed" class="nav-label">{{ item.title }}</span>
            </transition>
            <div v-if="currentRoute === item.path" class="nav-active-bar"></div>
          </router-link>
        </template>

        <!-- 平台数据（嵌入菜单） -->
        <div class="nav-divider" v-show="!isCollapsed"></div>
        <div class="nav-stat" v-show="!isCollapsed">
          <div class="nav-stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <span class="nav-label">活跃用户</span>
          <span class="nav-stat-num">{{ platformStats.activeUsers }}</span>
        </div>
        <div class="nav-stat" v-show="!isCollapsed">
          <div class="nav-stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </div>
          <span class="nav-label">策略总数</span>
          <span class="nav-stat-num">{{ platformStats.totalStrategies }}</span>
        </div>
        <div class="nav-stat" v-show="!isCollapsed">
          <div class="nav-stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
          </div>
          <span class="nav-label">平均收益</span>
          <span class="nav-stat-num" :class="platformStats.avgProfit >= 0 ? 'up' : 'down'">{{ platformStats.avgProfit >= 0 ? '+' : '' }}{{ platformStats.avgProfit.toFixed(1) }}%</span>
        </div>
      </nav>

      <!-- 底部折叠 + 退出 -->
      <div class="aside-footer">
        <div class="collapse-btn" @click="isCollapsed = !isCollapsed">
          <el-icon :size="16">
            <component :is="isCollapsed ? 'Expand' : 'Fold'" />
          </el-icon>
          <transition name="fade-text">
            <span v-show="!isCollapsed" class="collapse-label">收起菜单</span>
          </transition>
        </div>
        <!-- 退出登录 -->
        <div v-if="isLoggedIn" class="logout-btn" @click="handleLogout">
          <el-icon :size="16"><SwitchButton /></el-icon>
          <transition name="fade-text">
            <span v-show="!isCollapsed" class="logout-label">退出登录</span>
          </transition>
        </div>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <div v-if="isMobile" class="hamburger" @click="isCollapsed = !isCollapsed">
            <el-icon :size="20"><component :is="isCollapsed ? 'Expand' : 'Fold'" /></el-icon>
          </div>
          <h1 class="page-title">{{ currentTitle }}</h1>
          <span class="page-desc" v-show="!isMobile">{{ currentDesc }}</span>
        </div>
        <div class="header-right">
          <!-- 公告轮播 -->
          <div v-if="announcements.length > 0" class="announcement-bar" @click="showAnnouncementDetail">
            <span class="announcement-emoji">📢</span>
            <span class="announcement-label">公告：</span>
            <div class="announcement-scroll">
              <transition name="announcement-slide" mode="out-in">
                <span :key="currentAnnouncement?.id" class="announcement-text" :style="{ color: currentAnnouncement?.color || '#3b82f6', fontWeight: currentAnnouncement?.bold ? '600' : '400' }">
                  {{ currentAnnouncement?.title }}
                </span>
              </transition>
            </div>
          </div>
          <div class="ws-status" :class="wsConnected ? 'ws-on' : 'ws-off'" :title="wsConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'">
            <span class="ws-dot"></span>
            <span class="ws-text" v-show="false">{{ wsConnected ? '在线' : '离线' }}</span>
          </div>
          <!-- 主题切换按钮 -->
          <button class="theme-toggle-btn" :class="{ light: !isDark }" @click="toggleTheme" title="切换主题">
            <svg v-if="isDark" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          </button>
          <!-- 用户头像 + 下拉 -->
          <el-dropdown trigger="click" @command="onUserCommand">
            <div class="user-avatar-wrap">
              <el-avatar :size="32" class="user-avatar" :src="currentUser?.avatar || undefined">
                <el-icon><User /></el-icon>
              </el-avatar>
              <div class="user-info" v-show="!isMobile">
                <span class="user-name">{{ displayName }}</span>
                <span class="user-username">@{{ currentUser?.username }}</span>
              </div>
              <el-button type="primary" size="small" class="edit-profile-btn" @click.stop="showProfileDialog = true">
                <el-icon><EditPen /></el-icon>
              </el-button>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <span style="color:var(--text-muted)">{{ currentUser?.username }}</span>
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 公告详情弹框 -->
      <el-dialog 
        v-model="announcementDialogVisible" 
        :show-close="false"
        :close-on-click-modal="true"
        :close-on-press-escape="true"
        width="560px"
        custom-class="announcement-detail-dialog"
      >
        <template #header>
          <div class="modal-header">
            <div class="modal-title">公告详情</div>
            <button class="close-btn" @click="announcementDialogVisible = false">×</button>
          </div>
        </template>
        <div class="modal-body">
          <h1 class="announcement-title">{{ selectedAnnouncement?.title }}</h1>
          <div class="meta-info">
            <span>{{ formatAnnouncementTime(selectedAnnouncement?.id) }}</span>
            <span class="tag">系统通知</span>
          </div>
          <div class="announcement-content">{{ selectedAnnouncement?.content }}</div>
        </div>
      </el-dialog>

      <!-- 个人资料弹框 -->
      <el-dialog v-model="showProfileDialog" title="个人资料" width="400px">
        <div class="profile-dialog">
          <div class="profile-avatar" @click="showAvatarPicker = true" style="cursor: pointer;">
            <el-avatar :size="80" :src="profileForm.avatar || undefined">
              <el-icon :size="40"><User /></el-icon>
            </el-avatar>
            <div class="avatar-hint">点击更换头像</div>
          </div>
          <el-form label-width="80px" style="margin-top: 20px;">
            <el-form-item label="昵称">
              <el-input v-model="profileForm.nickname" placeholder="请输入昵称" class="profile-nickname-input" style="--el-input-bg-color:#fff;--el-input-text-color:#333;--el-input-border-color:#dcdfe6;" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input :model-value="currentUser?.username" disabled />
            </el-form-item>
            <el-form-item label="注册时间">
              <el-input :model-value="formatRegisterTime()" disabled />
            </el-form-item>
          </el-form>
        </div>
        <template #footer>
          <el-button @click="showProfileDialog = false">取消</el-button>
          <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存</el-button>
        </template>
      </el-dialog>

      <!-- 头像选择弹框 -->
      <el-dialog v-model="showAvatarPicker" title="选择头像" width="320px">
        <div class="avatar-grid">
          <div
            v-for="i in 9"
            :key="i"
            class="avatar-item"
            :class="{ selected: profileForm.avatar === `/avatars/${i}.jpg` }"
            @click="selectAvatar(i)"
          >
            <img :src="`/avatars/${i}.jpg`" :alt="`头像${i}`" />
          </div>
        </div>
      </el-dialog>

      <!-- 内容区 - 路由视图 -->
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="slide-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 通知面板 -->
    <teleport to="body">
      <transition name="notif-fade">
        <div v-if="showNotifPanel" class="notif-overlay" @click="showNotifPanel = false"></div>
      </transition>
      <transition name="notif-slide">
        <div v-if="showNotifPanel" class="notif-panel">
          <div class="notif-panel-header">
            <span class="notif-panel-title">通知中心</span>
            <div class="notif-panel-actions">
              <el-button text size="small" @click="markAllRead" :disabled="unreadCount === 0">
                全部已读
              </el-button>
              <el-icon size="18" class="notif-close" @click="showNotifPanel = false"><Close /></el-icon>
            </div>
          </div>
          <div class="notif-panel-body" v-loading="notifLoading">
            <template v-if="notifItems.length > 0">
              <div
                v-for="item in notifItems"
                :key="item.id"
                class="notif-item"
                :class="{ unread: !item.read }"
              >
                <div class="notif-dot" :class="item.level"></div>
                <div class="notif-content" @click="readNotif(item)">
                  <div class="notif-item-title">{{ item.title }}</div>
                  <div class="notif-item-msg">{{ item.message }}</div>
                  <div class="notif-item-time">{{ formatTime(item.created_at) }}</div>
                </div>
              </div>
            </template>
            <div v-else class="notif-empty">
              <el-icon :size="32" color="#3A3C42"><BellFilled /></el-icon>
              <p>暂无通知</p>
            </div>
          </div>
          <div class="notif-panel-footer">
            <router-link to="/notifications" @click="showNotifPanel = false" style="color: inherit; text-decoration: none;">
              查看全部通知
            </router-link>
          </div>
        </div>
      </transition>
    </teleport>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, EditPen, Bell } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'

const route = useRoute()
const router = useRouter()
const { on: wsOn, off: wsOff, connected: wsConnected } = useWebSocket()

// ─── 站点配置（带缓存） ───
const SITE_CACHE_KEY = 'site_settings_cache'
const siteName = ref('BTC Quant')
const siteLogo = ref('')
const siteSlogan = ref('量化交易系统')

// 先从缓存加载（首帧即有数据）
function loadSiteSettingsFromCache() {
  try {
    const cached = localStorage.getItem(SITE_CACHE_KEY)
    if (cached) {
      const data = JSON.parse(cached)
      if (data.site_name) siteName.value = data.site_name
      if (data.site_logo) siteLogo.value = data.site_logo
      if (data.site_slogan) siteSlogan.value = data.site_slogan
    }
  } catch (e) { /* ignore */ }
}

// 立即加载缓存
loadSiteSettingsFromCache()

// 监听其他标签页对站点设置的修改（跨标签页同步）
function onStorageChange(e) {
  if (e.key === SITE_CACHE_KEY) {
    if (e.newValue) {
      try {
        const data = JSON.parse(e.newValue)
        if (data.site_name) siteName.value = data.site_name
        if (data.site_logo) siteLogo.value = data.site_logo
        if (data.site_slogan) siteSlogan.value = data.site_slogan
      } catch { /* ignore */ }
    }
  }
}

async function fetchSiteSettings() {
  try {
    const res = await api.get('/settings/site')
    if (res.site_name) siteName.value = res.site_name
    if (res.site_logo) siteLogo.value = res.site_logo
    if (res.site_slogan) siteSlogan.value = res.site_slogan
    // 缓存到 localStorage
    localStorage.setItem(SITE_CACHE_KEY, JSON.stringify({
      site_name: res.site_name || 'BTC Quant',
      site_logo: res.site_logo || '',
      site_slogan: res.site_slogan || '量化交易系统',
    }))
  } catch (e) {
    console.error('Failed to fetch site settings:', e)
  }
}

// ─── 公告轮播 ───
const announcements = ref([])
const currentAnnouncementIndex = ref(0)
const currentAnnouncement = computed(() => announcements.value[currentAnnouncementIndex.value] || null)
let announcementTimer = null

async function fetchAnnouncements() {
  try {
    const res = await api.get('/announcements/active')
    announcements.value = Array.isArray(res) ? res : []
    if (announcements.value.length > 1) {
      startAnnouncementRotation()
    }
  } catch (e) {
    console.error('Failed to fetch announcements:', e)
  }
}

function startAnnouncementRotation() {
  if (announcementTimer) clearInterval(announcementTimer)
  announcementTimer = setInterval(() => {
    if (announcements.value.length > 1) {
      currentAnnouncementIndex.value = (currentAnnouncementIndex.value + 1) % announcements.value.length
    }
  }, 5000) // 每5秒切换
}

// 公告详情弹窗
const announcementDialogVisible = ref(false)
const selectedAnnouncement = ref(null)

function showAnnouncementDetail() {
  if (currentAnnouncement.value) {
    selectedAnnouncement.value = { ...currentAnnouncement.value }
    announcementDialogVisible.value = true
  }
}

function formatAnnouncementTime(id) {
  const dates = ['2026-05-04', '2026-05-03', '2026-05-02']
  return dates[(id - 1) % 3] || '2026-05-04'
}

// ─── 未登录倒计时 ───
const showLoginHint = ref(false)
const loginCountdown = ref(3)
let loginTimer = null

function startLoginCountdown() {
  const token = localStorage.getItem('token')
  if (!token && route.path === '/dashboard') {
    showLoginHint.value = true
    loginCountdown.value = 3
    loginTimer = setInterval(() => {
      loginCountdown.value--
      if (loginCountdown.value <= 0) {
        clearInterval(loginTimer)
        router.push('/login')
      }
    }, 1000)
  }
}

function goLogin() {
  if (loginTimer) clearInterval(loginTimer)
  router.push('/login')
}

function cancelRedirect() {
  if (loginTimer) clearInterval(loginTimer)
  showLoginHint.value = false
}

// ─── 登录状态 ───
const isLoggedIn = computed(() => !!localStorage.getItem('token'))

// ─── 主题切换 ───
const isDark = ref(localStorage.getItem('theme') === 'dark')

function loadTheme() {
  const stored = localStorage.getItem('theme')
  if (stored === 'dark') {
    isDark.value = true
  } else {
    isDark.value = false
  }
  applyTheme()
}

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  applyTheme()
}

function applyTheme() {
  // 更新根元素 class
  const app = document.querySelector('.app-container')
  if (app) {
    app.classList.toggle('dark', isDark.value)
    app.classList.toggle('light', !isDark.value)
  }
  // 更新 body 背景色和 data-theme 属性
  document.body.style.background = isDark.value ? '#0D0E11' : '#f5f5f5'
  document.body.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  // 通知其他组件主题变更（如 ECharts 图表重绘）
  window.dispatchEvent(new CustomEvent('theme-change', { detail: { isDark: isDark.value } }))
}

// ─── 用户信息 ───
const currentUser = ref(null)
const displayName = computed(() => currentUser.value?.nickname || currentUser.value?.username || '')

// 个人资料弹框
const showProfileDialog = ref(false)
const showAvatarPicker = ref(false)
const profileSaving = ref(false)
const profileForm = reactive({
  nickname: '',
  avatar: '',
})

function loadUser() {
  try {
    const stored = localStorage.getItem('user')
    if (stored) currentUser.value = JSON.parse(stored)
  } catch {}
}

// 打开弹框时同步昵称和头像
function syncProfileForm() {
  profileForm.nickname = currentUser.value?.nickname || currentUser.value?.username || ''
  profileForm.avatar = currentUser.value?.avatar || ''
}

// 选择头像
function selectAvatar(i) {
  profileForm.avatar = `/avatars/${i}.jpg`
  showAvatarPicker.value = false
}

// 格式化注册时间
function formatRegisterTime() {
  const t = currentUser.value?.created_at
  if (!t) return '--'
  const d = new Date(t)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

watch(showProfileDialog, (val) => {
  if (val) syncProfileForm()
})

async function saveProfile() {
  profileSaving.value = true
  try {
    await api.put('/auth/profile', { nickname: profileForm.nickname, avatar: profileForm.avatar })
    currentUser.value.nickname = profileForm.nickname
    currentUser.value.avatar = profileForm.avatar
    // 更新 localStorage
    const stored = JSON.parse(localStorage.getItem('user') || '{}')
    stored.nickname = profileForm.nickname
    stored.avatar = profileForm.avatar
    localStorage.setItem('user', JSON.stringify(stored))
    ElMessage.success('资料已更新')
    showProfileDialog.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    profileSaving.value = false
  }
}

function handleLogout() {
  onLogout()
}

function onUserCommand(cmd) {
  if (cmd === 'logout') onLogout()
}

function onLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
    ElMessage.success('已退出登录')
  }).catch(() => {})
}

// ─── 移动端检测 ───
const isMobile = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    isCollapsed.value = true
  }
}

function formatCompact(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return n.toFixed(2)
}

function onNavClick() {
  if (isMobile.value) {
    isCollapsed.value = true
  }
}

// ─── 平台数据统计 ───
const platformStats = ref({
  totalStrategies: 0,
  activeUsers: 0,
  avgProfit: 0,
  winRate: 0,
  runningStrategies: 0,
})

async function fetchPlatformStats() {
  try {
    const res = await api.get('/dashboard/platform_stats')
    if (res) {
      platformStats.value = {
        totalStrategies: res.total_strategies || 0,
        activeUsers: res.active_users || 0,
        avgProfit: res.avg_profit || 0,
        winRate: res.win_rate || 0,
        runningStrategies: res.running_strategies || 0,
      }
    }
  } catch (e) {
    console.error('Failed to fetch platform stats:', e)
  }
}

const isCollapsed = ref(false)
const btcPrice = ref(null)
const ethPrice = ref(null)
const isSandbox = ref(true)

// ─── 通知系统 ───
const showNotifPanel = ref(false)
const unreadCount = ref(0)
const notifItems = ref([])
const notifLoading = ref(false)

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = new Date()
  const diffMs = now - d
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)} 分钟前`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)} 小时前`
  if (diffMs < 604800000) return `${Math.floor(diffMs / 86400000)} 天前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadNotifications() {
  notifLoading.value = true
  try {
    const [countRes, listRes] = await Promise.all([
      api.get('/notifications/unread-count'),
      api.get('/notifications', { params: { limit: 10 } }),
    ])
    unreadCount.value = countRes.count
    notifItems.value = listRes.items || []
  } catch {}
  notifLoading.value = false
}

async function readNotif(item) {
  if (!item.read) {
    item.read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try { await api.post('/notifications/read', { id: item.id }) } catch {}
  }
}

async function markAllRead() {
  try {
    await api.post('/notifications/read', { all: true })
    unreadCount.value = 0
    notifItems.value.forEach(n => n.read = true)
  } catch {}
}

watch(showNotifPanel, (val) => {
  if (val) loadNotifications()
})

function onWsNotification(data) {
  if (data && data.title) {
    unreadCount.value++
    notifItems.value.unshift(data)
    if (notifItems.value.length > 10) notifItems.value.pop()
  }
}

const menuItems = [
  { path: '/dashboard', title: '总览',     icon: 'Odometer',      desc: '账户概览与运行状态' },
  { path: '/market',    title: '行情',     icon: 'TrendCharts',   desc: '实时K线与市场数据' },
  {
    path: '/strategy',
    title: '策略',
    icon: 'Setting',
    desc: '策略管理与参数配置',
    children: [
      { path: '/strategy/list', title: '策略管理', icon: 'Operation' },
      { path: '/strategy/robots', title: '量化机器人', icon: 'Promotion' },
      { path: '/strategy/ai-war-room', title: 'AI作战室', icon: 'Cpu' },
    ]
  },
  { path: '/backtest',  title: '回测',     icon: 'DataAnalysis',  desc: '历史回测与绩效分析' },
  { path: '/monitor',    title: '监控',     icon: 'Monitor',       desc: '系统状态与日志监控' },
  { path: '/trade',     title: '交易',     icon: 'Switch',        desc: '持仓管理与交易执行' },
  { path: '/settings',  title: '设置',     icon: 'Tools',         desc: 'API与风控参数配置' },
  { path: '/admin',     title: '管理',     icon: 'Lock',          desc: '管理后台（管理员）', adminOnly: true },
]

const expandedMenus = ref([])

function toggleSubmenu(path) {
  const idx = expandedMenus.value.indexOf(path)
  if (idx >= 0) {
    expandedMenus.value.splice(idx, 1)
  } else {
    expandedMenus.value.push(path)
  }
}

function handleParentMenuClick(item) {
  // 折叠状态下点击父菜单，导航到第一个子菜单
  if (isCollapsed.value && item.children && item.children.length > 0) {
    router.push(item.children[0].path)
  } else {
    // 非折叠状态，只展开/折叠子菜单
    toggleSubmenu(item.path)
  }
}

function isChildActive(item) {
  if (!item.children) return false
  return item.children.some(c => currentRoute.value === c.path)
}

const currentRoute = computed(() => route.path)
const filteredMenu = computed(() => {
  return menuItems.filter(m => {
    if (m.adminOnly && currentUser.value?.role !== 'admin') return false
    return true
  })
})
const currentTitle = computed(() => {
  // 先精确匹配
  const item = menuItems.find((m) => m.path === route.path)
  if (item) return item.title
  // 再匹配子菜单
  for (const m of menuItems) {
    if (m.children) {
      const child = m.children.find(c => c.path === route.path)
      if (child) return child.title
    }
  }
  return 'BTC Quant'
})

const currentDesc = computed(() => {
  const item = menuItems.find((m) => m.path === route.path)
  if (item) return item.desc || ''
  for (const m of menuItems) {
    if (m.children) {
      const child = m.children.find(c => c.path === route.path)
      if (child) return m.desc || ''
    }
  }
  return ''
})

// ─── WebSocket 实时 BTC 价格 ───
function onWsTicker(data) {
  if (data && data.price) {
    if (data.symbol === 'BTC-USDT') btcPrice.value = data.price
    if (data.symbol === 'ETH-USDT') ethPrice.value = data.price
  }
}

async function loadSandboxConfig() {
  try {
    const res = await api.get('/settings/api')
    isSandbox.value = res.sandbox
  } catch { /* ignore */ }
}

let refreshTimer = null

onMounted(async () => {
  loadTheme()
  loadUser()
  startLoginCountdown()  // 未登录用户3秒后跳转
  checkMobile()
  fetchSiteSettings()  // 加载站点配置
  fetchAnnouncements()  // 加载公告
  window.addEventListener('resize', checkMobile)
  window.addEventListener('storage', onStorageChange)

  // 自动展开当前子菜单所在的父级
  for (const item of menuItems) {
    if (item.children && item.children.some(c => route.path === c.path)) {
      if (!expandedMenus.value.includes(item.path)) {
        expandedMenus.value.push(item.path)
      }
    }
  }

  // 加载平台数据
  fetchPlatformStats()

  try {
    const [btcRes, ethRes] = await Promise.all([
      api.get('/market/ticker', { params: { symbol: 'BTC-USDT' } }).catch(() => ({})),
      api.get('/market/ticker', { params: { symbol: 'ETH-USDT' } }).catch(() => ({})),
    ])
    if (btcRes.price) btcPrice.value = btcRes.price
    if (ethRes.price) ethPrice.value = ethRes.price
  } catch { /* ignore */ }
  await loadSandboxConfig()

  refreshTimer = setInterval(async () => {
    if (!wsConnected.value) {
      try {
        const [btcRes, ethRes] = await Promise.all([
          api.get('/market/ticker', { params: { symbol: 'BTC-USDT' } }).catch(() => ({})),
          api.get('/market/ticker', { params: { symbol: 'ETH-USDT' } }).catch(() => ({})),
        ])
        if (btcRes.price) btcPrice.value = btcRes.price
        if (ethRes.price) ethPrice.value = ethRes.price
      } catch { /* ignore */ }
    }
    await loadSandboxConfig()
  }, 60000)

  wsOn('ticker', onWsTicker)
  wsOn('notification', onWsNotification)
  loadNotifications()
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (announcementTimer) clearInterval(announcementTimer)
  if (loginTimer) clearInterval(loginTimer)
  wsOff('ticker', onWsTicker)
  wsOff('notification', onWsNotification)
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('storage', onStorageChange)
})
</script>

<style>
/* ===== 全局重置 ===== */
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* ===== 未登录提示条 ===== */
.login-hint-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  z-index: 9999;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.hint-text {
  color: #fff;
  font-size: 14px;
}

.hint-text strong {
  font-size: 18px;
  margin: 0 4px;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

/* ===== 主容器 ===== */
.app-container { height: 100vh; overflow: hidden; }

/* ===== 侧边栏 ===== */
.app-aside {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow: 1px 0 4px rgba(0, 0, 0, 0.3);
}

.logo-area {
  height: 65px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 1px solid var(--border-secondary);
}

.logo-badge {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.logo-img {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  object-fit: contain;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-sub {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 导航列表 */
.nav-list {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-active-text);
  font-weight: 600;
}

.nav-group {
  display: flex;
  flex-direction: column;
}

.nav-arrow {
  margin-left: auto;
  transition: transform 0.2s;
}

.nav-arrow.expanded {
  transform: rotate(90deg);
}

.nav-submenu {
  display: flex;
  flex-direction: column;
  padding-left: 36px;
  overflow: hidden;
}

.nav-subitem {
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 12px;
  color: var(--sidebar-text);
  text-decoration: none;
  border-radius: 6px;
  margin: 2px 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-subitem:hover {
  background: var(--sidebar-hover-bg);
}

.nav-subitem.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-active-text);
  font-weight: 500;
}

.nav-subicon {
  margin-right: 8px;
  flex-shrink: 0;
}

.nav-icon-wrap {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-label {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
}

.nav-active-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
  box-shadow: 0 0 6px rgba(59,130,246,0.5);
}

/* 侧边栏底部 */
.aside-footer {
  padding: 8px 10px 12px;
  border-top: 1px solid var(--border-secondary);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.collapse-label {
  font-size: 13px;
  white-space: nowrap;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--red);
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 4px;
}

.logout-btn:hover {
  background: var(--red-light);
}

.logout-label {
  font-size: 13px;
  white-space: nowrap;
}

/* ===== 主内容区 ===== */
.main-container {
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 65px !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.page-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* 主题切换按钮 */
.theme-toggle-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s;
}
.app-container.dark .theme-toggle-btn {
  background: rgba(255,255,255,0.06);
  color: #a3a3a3;
}
.app-container.dark .theme-toggle-btn:hover {
  background: rgba(255,255,255,0.12);
  color: #fff;
}
.app-container.light .theme-toggle-btn {
  background: rgba(0,0,0,0.04);
  color: #737373;
}
.app-container.light .theme-toggle-btn:hover {
  background: rgba(0,0,0,0.08);
  color: #111;
}

.crypto-ticker {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: var(--accent-light);
  border-radius: 20px;
  border: 1px solid rgba(59,130,246,0.15);
}
.crypto-ticker.eth {
  background: var(--blue-light);
  border-color: rgba(59,130,246,0.15);
}
.crypto-label {
  font-size: 12px;
  color: var(--accent);
  font-weight: 500;
}
.crypto-ticker.eth .crypto-label {
  color: var(--blue);
}
.crypto-price {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
}
.crypto-ticker.eth .crypto-price {
  color: var(--blue);
}

/* 导航菜单分隔线 */
.nav-divider {
  height: 1px;
  background: var(--border-secondary);
  margin: 6px 12px;
}

/* 导航内嵌平台数据 */
.nav-stat {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 36px;
  padding: 0 12px;
  border-radius: 8px;
}

.nav-stat-icon {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  flex-shrink: 0;
}

.nav-stat-icon svg {
  width: 16px;
  height: 16px;
}

.nav-stat .nav-label {
  flex: 1;
  font-size: 12px;
  color: var(--text-muted);
}

.nav-stat-num {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.nav-stat-num.up { color: #10b981; }
.nav-stat-num.down { color: #ef4444; }

/* 用户头像下拉 */
.user-avatar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.edit-profile-btn {
  padding: 4px !important;
  height: 24px !important;
  min-width: 24px !important;
}
.user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  max-width: 80px;
}
.user-name {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-username {
  font-size: 11px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 公告详情弹框 */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid #ebeef5;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.close-btn {
  font-size: 20px;
  color: #909399;
  cursor: pointer;
  border: none;
  background: transparent;
  padding: 0;
  line-height: 1;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #409eff;
}

.modal-body {
  padding: 8px 20px 20px;
}

.announcement-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 10px;
  line-height: 1.4;
}

.meta-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-size: 13px;
  color: #6b7280;
}

.tag {
  background-color: #e6f0ff;
  color: #4080ff;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.announcement-content {
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
  white-space: pre-wrap;
}

/* 个人资料弹框 */
.profile-dialog {
  text-align: center;
}
.profile-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.avatar-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* 头像九宫格 */
.avatar-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 10px;
}
.avatar-item {
  aspect-ratio: 1;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: all 0.2s;
}
.avatar-item:hover {
  border-color: var(--accent);
  transform: scale(1.05);
}
.avatar-item.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent);
}
.avatar-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>

<style scoped>
.user-avatar {
  background: var(--bg-card);
  color: var(--text-muted);
}

/* 公告轮播 */
.announcement-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
  width: 340px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.2s;
}

.announcement-bar:hover {
  background: var(--bg-hover);
  border-color: var(--border-primary);
}

.announcement-emoji {
  font-size: 16px;
  flex-shrink: 0;
}

.announcement-label {
  font-size: 13px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.announcement-scroll {
  overflow: hidden;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.announcement-text {
  display: block;
  font-size: 13px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
}

.announcement-slide-enter-active,
.announcement-slide-leave-active {
  transition: all 0.4s ease;
}

.announcement-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.announcement-slide-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* WebSocket 状态指示 */
.ws-status {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 10px;
  cursor: default;
}

.ws-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  transition: background 0.3s;
}

.ws-on .ws-dot {
  background: var(--green);
  box-shadow: 0 0 6px rgba(0, 212, 170, 0.6);
}

.ws-off .ws-dot {
  background: var(--text-faint);
}

.ws-text {
  font-size: 11px;
  color: var(--text-muted);
}

.app-main {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  background: var(--bg-primary);
}

/* ===== 动画 ===== */
.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.2s ease;
}
.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}

.slide-fade-enter-active {
  transition: all 0.25s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.15s ease-in;
}
.slide-fade-enter-from {
  transform: translateX(12px);
  opacity: 0;
}
.slide-fade-leave-to {
  transform: translateX(-8px);
  opacity: 0;
}

/* ===== Element Plus 暗色全局覆盖 ===== */
.el-card {
  border-radius: var(--card-radius) !important;
  border: 1px solid var(--border-primary) !important;
  background: var(--bg-card) !important;
  box-shadow: var(--card-shadow) !important;
  color: var(--text-primary);
}

.el-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
}

.el-card__header {
  border-bottom: 1px solid var(--border-primary) !important;
  padding: 14px 20px !important;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.el-card__body {
  color: var(--text-secondary);
}

.el-table {
  --el-table-bg-color: var(--bg-card) !important;
  --el-table-tr-bg-color: var(--bg-card) !important;
  --el-table-header-bg-color: var(--bg-secondary) !important;
  --el-table-row-hover-bg-color: var(--bg-hover) !important;
  --el-table-border-color: var(--border-secondary) !important;
  --el-table-text-color: var(--text-primary) !important;
  --el-table-header-text-color: var(--text-muted) !important;
}

.el-table th.el-table__cell {
  background: var(--bg-secondary) !important;
  color: var(--text-muted) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: rgba(255,255,255,0.02) !important;
}

.el-button--primary {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}

.el-button--primary:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
}

.el-button--primary.is-plain {
  background: var(--accent-light) !important;
  border-color: rgba(59,130,246,0.3) !important;
  color: var(--accent) !important;
}

.el-button--success {
  background: var(--green) !important;
  border-color: var(--green) !important;
}

.el-button--danger {
  background: var(--red) !important;
  border-color: var(--red) !important;
}

.el-button--warning {
  background: var(--orange) !important;
  border-color: var(--orange) !important;
}

/* 输入框暗色 */
.el-input__wrapper {
  background: var(--bg-input) !important;
  box-shadow: 0 0 0 1px var(--border-primary) inset !important;
}

.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--border-focus) inset !important;
}

.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--accent) inset !important;
}

.el-input__inner {
  color: var(--text-primary) !important;
}

.el-input__inner::placeholder {
  color: var(--text-faint) !important;
}

.el-input__prefix .el-icon,
.el-input__suffix .el-icon {
  color: var(--text-muted);
}

/* Select暗色 */
.el-select .el-input__wrapper {
  background: var(--bg-input) !important;
}

/* 表单标签 */
.el-form-item__label {
  color: var(--text-secondary) !important;
}

/* Dialog暗色 */
.el-dialog {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-primary) !important;
  border-radius: 16px !important;
}

.el-dialog__header {
  border-bottom: 1px solid var(--border-secondary) !important;
}

.el-dialog__title {
  color: var(--text-primary) !important;
}

.el-dialog__body {
  color: var(--text-secondary);
}

/* Tabs暗色 */
.el-tabs__item {
  color: var(--text-secondary) !important;
}

.el-tabs__item.is-active {
  color: var(--accent) !important;
}

.el-tabs__active-bar {
  background: var(--accent) !important;
}

.el-tabs__nav-wrap::after {
  background: var(--border-secondary) !important;
}

/* Tag暗色 */
.el-tag {
  border-color: var(--border-primary) !important;
}

/* Radio Group暗色 */
.el-radio-button__inner {
  background: var(--bg-card) !important;
  border-color: var(--border-primary) !important;
  color: var(--text-secondary) !important;
}

.el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
  box-shadow: -1px 0 0 0 var(--accent) !important;
}

/* Checkbox暗色 */
.el-checkbox__label {
  color: var(--text-secondary) !important;
}

.el-checkbox__inner {
  background: var(--bg-input) !important;
  border-color: var(--border-primary) !important;
}

/* Slider暗色 */
.el-slider__runway {
  background: var(--border-primary) !important;
}

.el-slider__bar {
  background: var(--accent) !important;
}

/* Switch暗色 */
.el-switch__core {
  background: var(--text-faint) !important;
  border-color: var(--text-faint) !important;
}

.el-switch.is-checked .el-switch__core {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
}

/* Empty暗色 */
.el-empty__description p {
  color: var(--text-muted) !important;
}

/* Dropdown暗色 */
.el-dropdown-menu {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-primary) !important;
}

.el-dropdown-menu__item {
  color: var(--text-secondary) !important;
}

.el-dropdown-menu__item:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}

/* 滚动条暗色 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.08);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.15);
}

/* ===== 汉堡菜单按钮 ===== */
.hamburger {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}
.hamburger:hover {
  background: var(--bg-hover);
}

/* ===== 移动端遮罩 ===== */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 99;
  transition: opacity 0.3s;
}

/* ===== 移动端侧边栏 ===== */
.mobile-aside {
  position: fixed !important;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
  box-shadow: 4px 0 16px rgba(0, 0, 0, 0.3) !important;
}
.mobile-aside-hidden {
  transform: translateX(-100%);
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .app-main {
    padding: 16px !important;
  }
}

/* ===== 通知铃铛 ===== */
.notify-badge {
  cursor: pointer;
  line-height: 1;
}
.notify-bell {
  color: var(--text-muted);
  transition: color 0.2s;
}
.notify-bell:hover {
  color: var(--text-primary);
}

/* ===== 通知面板 ===== */
.notif-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 2000;
}
.notif-panel {
  position: fixed;
  top: 60px;
  right: 24px;
  width: 380px;
  max-height: calc(100vh - 80px);
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  z-index: 2001;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.notif-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border-primary);
}
.notif-panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
.notif-panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.notif-close {
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.2s;
}
.notif-close:hover { color: var(--text-secondary); }
.notif-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  max-height: 400px;
}
.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.notif-item:hover { background: var(--bg-hover); }
.notif-item.unread { background: var(--accent-light); }
.notif-item.unread:hover { background: rgba(59,130,246,0.15); }
.notif-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.notif-dot.info { background: var(--blue); }
.notif-dot.warn { background: var(--orange); }
.notif-dot.error { background: var(--red); }
.notif-content { flex: 1; min-width: 0; }
.notif-item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.notif-item-msg {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.notif-item-time {
  font-size: 11px;
  color: var(--text-faint);
  margin-top: 6px;
}
.notif-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: var(--text-faint);
  font-size: 13px;
}
.notif-panel-footer {
  border-top: 1px solid var(--border-primary);
  padding: 12px 20px;
  text-align: center;
  font-size: 13px;
  color: var(--accent);
  cursor: pointer;
}
.notif-panel-footer:hover { text-decoration: underline; }

.notif-fade-enter-active, .notif-fade-leave-active { transition: opacity 0.2s; }
.notif-fade-enter-from, .notif-fade-leave-to { opacity: 0; }
.notif-slide-enter-active { transition: all 0.25s ease-out; }
.notif-slide-leave-active { transition: all 0.15s ease-in; }
.notif-slide-enter-from { transform: translateX(12px); opacity: 0; }
.notif-slide-leave-to { transform: translateX(8px); opacity: 0; }

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .app-aside {
    position: fixed !important;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 100;
  }
  .app-aside.mobile-aside-hidden {
    width: 0 !important;
    overflow: hidden;
    transform: translateX(-100%);
  }
  .app-header {
    padding: 0 12px !important;
  }
  .page-title {
    font-size: 16px !important;
  }
  .app-main {
    padding: 12px !important;
  }
  .crypto-ticker {
    padding: 2px 8px !important;
  }
  .crypto-label {
    font-size: 11px !important;
  }
  .crypto-price {
    font-size: 12px !important;
  }
  .el-card__header {
    padding: 10px 14px !important;
  }
  .el-table {
    font-size: 12px !important;
  }
  .el-dialog {
    width: 92% !important;
    margin: 10px auto !important;
  }
  .notif-panel {
    left: 8px;
    right: 8px;
    width: auto;
  }
}
</style>

<style>
.announcement-detail-dialog {
  background: #ffffff !important;
  border: 1px solid #e8ecf1 !important;
  border-radius: 10px !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.02) !important;
  overflow: hidden !important;
}
.announcement-detail-dialog .el-dialog__header { padding: 0 !important; margin: 0 !important; border-bottom: none !important; }
.announcement-detail-dialog .el-dialog__body { padding: 0 !important; }
.announcement-detail-dialog .el-dialog__headerbtn { display: none !important; }
</style>
