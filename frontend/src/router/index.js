import { createRouter, createWebHistory } from 'vue-router'

// Layout 包裹（侧边栏+顶栏+通知）
const Layout = () => import('../views/Layout.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '总览', icon: 'DataBoard' },
      },
      {
        path: 'market',
        name: 'Market',
        component: () => import('../views/Market.vue'),
        meta: { title: '行情', icon: 'TrendCharts' },
      },
      {
        path: 'strategy',
        redirect: '/strategy/list',
      },
      {
        path: 'strategy/list',
        name: 'Strategy',
        component: () => import('../views/Strategy.vue'),
        meta: { title: '策略管理', icon: 'Operation' },
      },
      {
        path: 'strategy/robots',
        name: 'Robots',
        component: () => import('../views/Robots.vue'),
        meta: { title: '量化机器人', icon: 'Monitor' },
      },
      {
        path: 'backtest',
        name: 'Backtest',
        component: () => import('../views/Backtest.vue'),
        meta: { title: '回测', icon: 'DataAnalysis' },
      },
      {
        path: 'performance',
        name: 'Performance',
        component: () => import('../views/Performance.vue'),
        meta: { title: '绩效', icon: 'Histogram' },
      },
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('../views/Monitor.vue'),
        meta: { title: '监控', icon: 'Monitor' },
      },
      {
        path: 'trade',
        name: 'Trade',
        component: () => import('../views/Trade.vue'),
        meta: { title: '交易', icon: 'ShoppingCart' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue'),
        meta: { title: '设置', icon: 'Setting' },
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('../views/Admin.vue'),
        meta: { title: '管理', icon: 'Lock' },
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('../views/Notifications.vue'),
        meta: { title: '通知', icon: 'Bell' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ─── 路由守卫：未登录跳转登录页 ───
router.beforeEach((to, _from, next) => {
  // 公开页面直接放行
  if (to.meta.public) {
    const token = localStorage.getItem('token')
    if (token && to.name === 'Login') {
      return next('/dashboard')
    }
    return next()
  }

  // 非公开页面需要 token
  const token = localStorage.getItem('token')
  if (!token) {
    return next('/login')
  }

  next()
})

export default router
