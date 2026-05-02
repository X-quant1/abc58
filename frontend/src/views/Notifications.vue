<template>
  <div class="notif-page">
    <!-- 操作栏 -->
    <div class="page-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">通知中心</span>
        <el-tag v-if="unreadCount > 0" effect="plain" size="small" type="danger" round>
          {{ unreadCount }} 条未读
        </el-tag>
      </div>
      <div class="toolbar-right">
        <el-radio-group v-model="filterCategory" size="small" @change="loadAll">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="trade">交易</el-radio-button>
          <el-radio-button label="strategy">策略</el-radio-button>
          <el-radio-button label="system">系统</el-radio-button>
        </el-radio-group>
        <el-button type="primary" size="small" @click="loadAll" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button size="small" @click="markAllRead" :disabled="unreadCount === 0">
          全部已读
        </el-button>
      </div>
    </div>

    <!-- 通知列表 -->
    <div v-loading="loading" class="notif-list">
      <template v-if="items.length > 0">
        <div
          v-for="item in items"
          :key="item.id"
          class="notif-card"
          :class="{ unread: !item.read }"
          @click="readItem(item)"
        >
          <div class="notif-card-left">
            <div class="notif-level-dot" :class="item.level"></div>
            <el-tag size="small" :type="categoryType(item.category)" effect="plain" round>
              {{ categoryLabel(item.category) }}
            </el-tag>
          </div>
          <div class="notif-card-content">
            <div class="notif-card-title">{{ item.title }}</div>
            <div class="notif-card-msg">{{ item.message }}</div>
            <div class="notif-card-footer">
              <span class="notif-card-time">{{ formatTime(item.created_at) }}</span>
              <span v-if="item.strategy_id" class="notif-card-strategy">策略 #{{ item.strategy_id }}</span>
            </div>
          </div>
        </div>
      </template>
      <div v-else-if="!loading" class="empty-state">
        <el-icon :size="48" color="#dcdfe6"><BellFilled /></el-icon>
        <p class="empty-title">暂无通知</p>
        <p class="empty-desc">当策略执行交易或系统发生异常时，这里会收到通知</p>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadAll"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../utils/api'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const unreadCount = ref(0)
const page = ref(1)
const pageSize = 20
const filterCategory = ref('')

function categoryLabel(cat) {
  return { trade: '交易', strategy: '策略', system: '系统', alert: '告警' }[cat] || cat
}
function categoryType(cat) {
  return { trade: 'warning', strategy: 'danger', system: 'info', alert: 'danger' }[cat] || 'info'
}
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

async function loadAll() {
  loading.value = true
  try {
    const res = await api.get('/notifications', {
      params: {
        limit: pageSize,
        offset: (page.value - 1) * pageSize,
        category: filterCategory.value || undefined,
      },
    })
    items.value = res.items || []
    total.value = res.total || 0
    unreadCount.value = res.unread || 0
  } catch {}
  loading.value = false
}

async function readItem(item) {
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
    items.value.forEach(n => n.read = true)
  } catch {}
}

onMounted(() => loadAll())
</script>

<style scoped>
.notif-page {
  max-width: 800px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.toolbar-title {
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ─── 通知卡片 ─── */
.notif-list {
  min-height: 200px;
}
.notif-card {
  display: flex;
  gap: 14px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid #ebeef5;
}
.notif-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.notif-card.unread {
  background: #fffbe8;
  border-color: #ffe58f;
}

.notif-card-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding-top: 2px;
}
.notif-level-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.notif-level-dot.info { background: #3491fa; }
.notif-level-dot.warn { background: #ff7d00; }
.notif-level-dot.error { background: #f53f3f; }

.notif-card-content {
  flex: 1;
  min-width: 0;
}
.notif-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}
.notif-card-msg {
  font-size: 13px;
  color: #4e5969;
  margin-top: 6px;
  line-height: 1.5;
}
.notif-card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}
.notif-card-time {
  font-size: 12px;
  color: #c9cdd4;
}
.notif-card-strategy {
  font-size: 11px;
  color: #f7931a;
  background: #fff7e8;
  padding: 1px 8px;
  border-radius: 10px;
}

/* ─── 空状态 ─── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}
.empty-title {
  margin-top: 12px;
  font-size: 15px;
  color: #86909c;
}
.empty-desc {
  margin-top: 4px;
  font-size: 13px;
  color: #c9cdd4;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .page-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .notif-card {
    padding: 12px 14px;
  }
}
</style>
