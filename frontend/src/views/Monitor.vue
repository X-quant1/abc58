<template>
  <div class="monitor">
    <!-- 概览卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">运行中策略</div>
            <div class="stat-value">{{ dashboard.strategies?.running || 0 }}</div>
            <div class="stat-sub">共 {{ dashboard.strategies?.total || 0 }} 个策略</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">今日盈亏</div>
            <div class="stat-value" :class="dashboard.today?.pnl >= 0 ? 'profit' : 'loss'">
              {{ dashboard.today?.pnl >= 0 ? '+' : '' }}{{ dashboard.today?.pnl || 0 }} USDT
            </div>
            <div class="stat-sub">{{ dashboard.today?.trades || 0 }} 笔交易</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">总盈亏</div>
            <div class="stat-value" :class="dashboard.total?.pnl >= 0 ? 'profit' : 'loss'">
              {{ dashboard.total?.pnl >= 0 ? '+' : '' }}{{ dashboard.total?.pnl || 0 }} USDT
            </div>
            <div class="stat-sub">胜率 {{ dashboard.total?.win_rate || 0 }}%</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-label">当前持仓</div>
            <div class="stat-value">{{ dashboard.position_count || 0 }}</div>
            <div class="stat-sub">个仓位</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 策略表现表格 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略表现</span>
          <el-button @click="loadPerformance">刷新</el-button>
        </div>
      </template>

      <el-table :data="strategies" v-loading="loading">
        <el-table-column prop="name" label="策略名称" width="200" />
        <el-table-column prop="running" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.running ? 'success' : 'info'" size="small">
              {{ row.running ? '运行中' : '已停止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="position" label="持仓" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.position !== 'none'" :type="row.position === 'long' ? 'success' : 'danger'" size="small">
              {{ row.position === 'long' ? '多' : '空' }}
            </el-tag>
            <span v-else class="text-muted">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="pnl" label="盈亏" width="120">
          <template #default="{ row }">
            <span :class="row.pnl >= 0 ? 'profit' : 'loss'">
              {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl }} USDT
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="trades" label="交易次数" width="100" />
        <el-table-column prop="win_rate" label="胜率" width="100">
          <template #default="{ row }">
            {{ row.win_rate }}%
          </template>
        </el-table-column>
        <el-table-column prop="avg_holding_time" label="平均持仓" width="120">
          <template #default="{ row }">
            {{ row.avg_holding_time }} 小时
          </template>
        </el-table-column>
        <el-table-column prop="max_loss" label="最大亏损" width="120">
          <template #default="{ row }">
            <span class="loss">{{ row.max_loss }} USDT</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="showTrades(row)">交易记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 交易记录对话框 -->
    <el-dialog v-model="tradesDialogVisible" :title="`${currentStrategy?.name} - 交易记录`" width="800px">
      <el-table :data="trades" v-loading="tradesLoading">
        <el-table-column prop="side" label="方向" width="80">
          <template #default="{ row }">
            <el-tag :type="row.side === 'buy' ? 'success' : 'danger'" size="small">
              {{ row.side === 'buy' ? '买' : '卖' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="数量" width="100" />
        <el-table-column prop="entry_price" label="开仓价" width="120" />
        <el-table-column prop="exit_price" label="平仓价" width="120" />
        <el-table-column prop="pnl" label="盈亏" width="120">
          <template #default="{ row }">
            <span :class="row.pnl >= 0 ? 'profit' : 'loss'">
              {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl }} USDT
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="opened_at" label="开仓时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.opened_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="closed_at" label="平仓时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.closed_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const dashboard = ref({})
const strategies = ref([])
const trades = ref([])
const loading = ref(false)
const tradesLoading = ref(false)
const tradesDialogVisible = ref(false)
const currentStrategy = ref(null)

// 加载概览数据
async function loadDashboard() {
  try {
    const data = await axios.get('/monitor/dashboard')
    dashboard.value = data
  } catch (e) {
    ElMessage.error('加载概览数据失败')
  }
}

// 加载策略表现
async function loadPerformance() {
  loading.value = true
  try {
    const data = await axios.get('/monitor/strategies/performance')
    strategies.value = data.strategies
  } catch (e) {
    ElMessage.error('加载策略表现失败')
  }
  loading.value = false
}

// 显示交易记录
async function showTrades(strategy) {
  currentStrategy.value = strategy
  tradesDialogVisible.value = true
  tradesLoading.value = true
  
  try {
    const data = await axios.get(`/monitor/strategies/${strategy.id}/trades`)
    trades.value = data.trades
  } catch (e) {
    ElMessage.error('加载交易记录失败')
  }
  
  tradesLoading.value = false
}

// 格式化时间
function formatTime(time) {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDashboard()
  loadPerformance()
})
</script>

<style scoped>
.monitor {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mb-4 {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-sub {
  font-size: 12px;
  color: #999;
}

.profit {
  color: #67c23a;
}

.loss {
  color: #f56c6c;
}

.text-muted {
  color: #999;
}
</style>
