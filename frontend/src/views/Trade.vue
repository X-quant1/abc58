<template>
  <div class="trade-page">
    <!-- 账户概览 -->
    <div class="account-grid">
      <div class="account-card">
        <span class="account-label">账户余额</span>
        <span class="account-value">{{ balanceInfo.total_equity?.toFixed(2) || '--' }} <small>USDT</small></span>
      </div>
      <div class="account-card">
        <span class="account-label">未实现盈亏</span>
        <span class="account-value" :style="{ color: unrealizedPnl >= 0 ? '#f53f3f' : '#00b42a' }">
          {{ unrealizedPnl !== null ? (unrealizedPnl >= 0 ? '+' : '') + unrealizedPnl.toFixed(4) : '--' }} <small>USDT</small>
        </span>
      </div>
      <div class="account-card">
        <span class="account-label">持仓数</span>
        <span class="account-value">{{ positions.length }}</span>
      </div>
      <div class="account-card">
        <span class="account-label">未成交委托</span>
        <span class="account-value">{{ orders.length }}</span>
      </div>
    </div>

    <!-- 持仓 + 委托 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="14">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">当前持仓</span>
              <el-button type="danger" size="small" @click="closeAll" :loading="closingAll" :disabled="positions.length === 0">
                一键平仓
              </el-button>
            </div>
          </template>
          <el-table :data="positions" stripe empty-text="暂无持仓" style="width: 100%">
            <el-table-column prop="symbol" label="交易对" width="140" />
            <el-table-column prop="side" label="方向" width="70">
              <template #default="{ row }">
                <el-tag :type="row.side === 'long' ? 'danger' : 'success'" size="small">
                  {{ row.side === 'long' ? '多' : '空' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="数量" align="right">
              <template #default="{ row }">{{ row.size }}</template>
            </el-table-column>
            <el-table-column label="开仓价" align="right">
              <template #default="{ row }">{{ row.avg_price?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="标记价" align="right">
              <template #default="{ row }">{{ row.mark_price?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="浮动盈亏" align="right">
              <template #default="{ row }">
                <span :style="{ color: row.unrealized_pnl >= 0 ? '#f53f3f' : '#00b42a', fontWeight: 600 }">
                  {{ row.unrealized_pnl >= 0 ? '+' : '' }}{{ row.unrealized_pnl?.toFixed(4) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="盈亏%" align="right" width="80">
              <template #default="{ row }">
                <span :style="{ color: row.unrealized_pnl_ratio >= 0 ? '#f53f3f' : '#00b42a' }">
                  {{ (row.unrealized_pnl_ratio * 100)?.toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="leverage" label="杠杆" width="60" align="center" />
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" size="small" text @click="closeOne(row)">平仓</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">当前委托</span>
              <el-button text size="small" type="primary" @click="loadOrders">刷新</el-button>
            </div>
          </template>
          <el-table :data="orders" stripe empty-text="暂无委托" style="width: 100%">
            <el-table-column prop="instId" label="交易对" width="140" />
            <el-table-column prop="side" label="方向" width="60">
              <template #default="{ row }">
                <el-tag :type="row.side === 'buy' ? 'danger' : 'success'" size="small">
                  {{ row.side === 'buy' ? '买' : '卖' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="px" label="委托价" align="right" />
            <el-table-column prop="sz" label="数量" align="right" />
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ row }">
                <el-button type="danger" size="small" text @click="cancelOrder(row)">撤单</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 成交流水 -->
    <el-card shadow="hover" class="panel-card" style="margin-top: 20px;">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">成交流水</span>
          <el-button text size="small" type="primary" @click="loadFills">刷新</el-button>
        </div>
      </template>
      <el-table :data="fills" stripe empty-text="暂无成交记录" style="width: 100%">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.fillTime || row.ts) }}</template>
        </el-table-column>
        <el-table-column prop="instId" label="交易对" width="140" />
        <el-table-column prop="side" label="方向" width="60">
          <template #default="{ row }">
            <el-tag :type="row.side === 'buy' ? 'danger' : 'success'" size="small">
              {{ row.side === 'buy' ? '买' : '卖' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fillPx" label="成交价" align="right" />
        <el-table-column prop="fillSz" label="数量" align="right" />
        <el-table-column prop="fee" label="手续费" align="right" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'

const { on: wsOn, off: wsOff } = useWebSocket()

const balanceInfo = ref({})
const positions = ref([])
const orders = ref([])
const fills = ref([])
const closingAll = ref(false)

const unrealizedPnl = computed(() => {
  const val = balanceInfo.value.total_unrealized_pnl
  return val !== undefined ? val : null
})

// ─── WebSocket 实时数据 ───

function onWsAccount(data) {
  if (data) {
    balanceInfo.value = data
  }
}

function onWsPosition(data) {
  if (data && data.positions) {
    positions.value = data.positions
  }
}

function onWsTrade(data) {
  if (data) {
    // 成交通知，刷新持仓和成交记录
    loadFills()
    loadOrders()
  }
}

function onWsSignal(data) {
  if (data && (data.signal === 'open_long' || data.signal === 'open_short' ||
      data.signal === 'close_long' || data.signal === 'close_short')) {
    // 策略信号后刷新数据
    setTimeout(() => {
      loadPositions()
      loadBalance()
    }, 3000)
  }
}

// ─── 数据加载 ───

async function loadBalance() {
  try {
    balanceInfo.value = await api.get('/trade/balance')
  } catch { /* ignore */ }
}

async function loadPositions() {
  try {
    const res = await api.get('/trade/positions')
    positions.value = res.positions || []
  } catch { /* ignore */ }
}

async function loadOrders() {
  try {
    const res = await api.get('/trade/orders')
    orders.value = res.orders || []
  } catch { /* ignore */ }
}

async function loadFills() {
  try {
    const res = await api.get('/trade/fills')
    fills.value = res.fills || []
  } catch { /* ignore */ }
}

// ─── 交易操作 ───

async function closeOne(row) {
  try {
    await ElMessageBox.confirm(
      `确定平仓 ${row.symbol} (${row.side === 'long' ? '多' : '空'}) ？`,
      '确认平仓',
      { type: 'warning' }
    )
    await api.post('/trade/close', {
      inst_id: row.symbol,
      mgn_mode: row.mgn_mode || 'cross',
      pos_side: row.side || 'net',
    })
    ElMessage.success('平仓指令已发送')
    setTimeout(() => { loadPositions(); loadBalance() }, 2000)
  } catch { /* cancel */ }
}

async function closeAll() {
  try {
    await ElMessageBox.confirm(
      '确定一键平掉所有持仓？此操作不可撤销！',
      '⚠️ 一键平仓确认',
      { type: 'error', confirmButtonText: '确认平仓', cancelButtonText: '取消' }
    )
    closingAll.value = true
    const res = await api.post('/trade/close-all')
    ElMessage.success(`已平仓 ${res.closed}/${res.total} 个持仓`)
    setTimeout(() => { loadPositions(); loadBalance() }, 2000)
  } catch { /* cancel */ }
  finally {
    closingAll.value = false
  }
}

async function cancelOrder(row) {
  try {
    await api.post('/trade/cancel', null, {
      params: { inst_id: row.instId, ord_id: row.ordId }
    })
    ElMessage.success('撤单指令已发送')
    setTimeout(loadOrders, 1500)
  } catch (e) {
    ElMessage.error('撤单失败')
  }
}

function formatTime(ts) {
  if (!ts) return '--'
  const d = new Date(Number(ts))
  return d.toLocaleString('zh-CN')
}

// 定时刷新（降低频率，WS 负责实时推送，这里做兜底）
let timer = null
onMounted(() => {
  loadBalance()
  loadPositions()
  loadOrders()
  loadFills()
  // 兜底轮询，频率从 15s 降到 60s
  timer = setInterval(() => {
    loadBalance()
    loadPositions()
  }, 60000)

  // 注册 WebSocket
  wsOn('account', onWsAccount)
  wsOn('position', onWsPosition)
  wsOn('trade', onWsTrade)
  wsOn('signal', onWsSignal)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  wsOff('account', onWsAccount)
  wsOff('position', onWsPosition)
  wsOff('trade', onWsTrade)
  wsOff('signal', onWsSignal)
})
</script>

<style scoped>
.account-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.account-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow 0.2s;
}

.account-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.account-label {
  font-size: 13px;
  color: #86909c;
  font-weight: 500;
}

.account-value {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.account-value small {
  font-size: 13px;
  font-weight: 400;
  color: #86909c;
  margin-left: 2px;
}

.panel-card { border-radius: 10px; }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}
</style>
