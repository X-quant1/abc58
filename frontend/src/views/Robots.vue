<template>
  <div class="robots-page">
    <!-- 顶部提示 -->
    <div class="page-notice">
      <el-icon :size="16"><InfoFilled /></el-icon>
      <span>每个机器人初始资金 10000 USDT，采用真实信号触发，点击卡片查看详情</span>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="robots.length === 0" class="empty-state">
      <div class="empty-icon-wrap">
        <el-icon :size="48" color="#c9cdd4"><Promotion /></el-icon>
      </div>
      <p class="empty-title">暂无机器人</p>
      <p class="empty-desc">管理员尚未创建量化机器人</p>
    </div>

    <!-- 机器人卡片列表 -->
    <div v-else class="robot-grid">
      <div v-for="robot in robots" :key="robot.id"
           class="robot-card"
           :class="{ 'robot-running': robot.is_running }"
           @click="openDetail(robot)">
        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="robot-avatar" :class="robot.is_running ? 'avatar-active' : ''">
            <span class="avatar-emoji">{{ robot.is_running ? '🤖' : '⏸️' }}</span>
          </div>
          <div class="robot-info">
            <div class="robot-name">{{ robot.name }}</div>
            <div class="robot-status">
              <span class="status-dot" :class="robot.is_running ? 'dot-running' : 'dot-stopped'"></span>
              <span class="status-text">{{ robot.is_running ? '运行中' : '已停止' }}</span>
            </div>
          </div>
          <div class="robot-pnl-badge" :class="robot.total_pnl >= 0 ? 'pnl-up' : 'pnl-down'">
            <span class="pnl-arrow">{{ robot.total_pnl >= 0 ? '↑' : '↓' }}</span>
            <span class="pnl-pct">{{ calcPnlPct(robot) }}%</span>
          </div>
        </div>

        <!-- 核心数据区 -->
        <div class="card-main">
          <!-- 主要指标：当前余额 + 累计盈亏 -->
          <div class="main-metrics">
            <div class="main-metric">
              <div class="main-label">当前余额</div>
              <div class="main-value">{{ formatNum(robot.current_equity) }}U</div>
            </div>
            <div class="main-divider"></div>
            <div class="main-metric">
              <div class="main-label">累计盈亏</div>
              <div class="main-value" :class="robot.total_pnl >= 0 ? 'val-up' : 'val-down'">
                {{ robot.total_pnl >= 0 ? '+' : '' }}{{ formatNum(robot.total_pnl) }}U
              </div>
            </div>
          </div>

          <!-- 月化收益率突出显示 -->
          <div class="monthly-return-card" :class="calcMonthlyReturn(robot) >= 0 ? 'return-positive' : 'return-negative'">
            <div class="return-left">
              <div class="return-icon">
                <span class="return-arrow">{{ calcMonthlyReturn(robot) >= 0 ? '📈' : '📉' }}</span>
              </div>
              <div class="return-info">
                <div class="return-title">月化收益</div>
                <div class="return-desc">年化 {{ calcAnnualReturn(robot).toFixed(1) }}%</div>
              </div>
            </div>
            <div class="return-right">
              <span class="return-value">{{ calcMonthlyReturn(robot) >= 0 ? '+' : '' }}{{ calcMonthlyReturn(robot).toFixed(2) }}</span>
              <span class="return-unit">%</span>
            </div>
          </div>

          <!-- 次要指标网格 -->
          <div class="sub-metrics">
            <div class="sub-metric">
              <el-icon class="sub-icon"><Collection /></el-icon>
              <div class="sub-content">
                <div class="sub-value">{{ robot.strategy_count || 0 }}</div>
                <div class="sub-label">运行策略</div>
              </div>
            </div>
            <div class="sub-metric">
              <el-icon class="sub-icon"><TrendCharts /></el-icon>
              <div class="sub-content">
                <div class="sub-value">{{ robot.trade_count }}</div>
                <div class="sub-label">交易次数</div>
              </div>
            </div>
            <div class="sub-metric">
              <el-icon class="sub-icon" :class="robot.win_rate >= 70 ? 'icon-success' : ''"><Trophy /></el-icon>
              <div class="sub-content">
                <div class="sub-value" :class="robot.win_rate >= 70 ? 'val-up' : ''">{{ robot.win_rate.toFixed(1) }}%</div>
                <div class="sub-label">胜率</div>
              </div>
            </div>
            <div class="sub-metric">
              <el-icon class="sub-icon icon-danger"><ArrowDown /></el-icon>
              <div class="sub-content">
                <div class="sub-value val-down">{{ robot.max_drawdown.toFixed(1) }}%</div>
                <div class="sub-label">最大回撤</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="card-footer" @click.stop>
          <el-button type="primary" size="small" class="follow-btn" @click.stop="handleFollow(robot)">
            <el-icon><Position /></el-icon>
            一键跟随
          </el-button>
          <el-button size="small" class="record-btn" @click.stop="openDetail(robot)">
            <el-icon><Document /></el-icon>
            查看详情
          </el-button>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      width="1060px"
      destroy-on-close
      :show-close="true"
      class="robot-detail-dialog"
      top="6vh"
      :close-on-click-modal="true"
    >
      <template #header>
        <div v-if="currentRobot" class="dlg-header">
          <div class="dlg-title-row">
            <div class="dlg-robot-icon" :class="currentRobot.is_running ? 'icon-active' : ''">
              {{ currentRobot.is_running ? '🤖' : '⏸️' }}
            </div>
            <div class="dlg-title-info">
              <div class="dlg-robot-name">{{ currentRobot.name }}</div>
              <div class="dlg-robot-meta">
                <span class="meta-status" :class="currentRobot.is_running ? 'status-running' : 'status-stopped'">
                  <span class="meta-dot" :class="currentRobot.is_running ? 'dot-on' : 'dot-off'"></span>
                  {{ currentRobot.is_running ? '运行中' : '已停止' }}
                </span>
                <span class="meta-sep">|</span>
                <span class="meta-strategies">
                  {{ currentRobot.strategy_count || 0 }} 个策略
                </span>
                <span class="meta-sep">|</span>
                <span class="meta-pnl" :class="currentRobot.total_pnl >= 0 ? 'pnl-green' : 'pnl-red'">
                  累计 {{ currentRobot.total_pnl >= 0 ? '+' : '' }}{{ formatNum(currentRobot.total_pnl) }}U
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-if="currentRobot" class="detail-body">
        <!-- 核心指标面板 -->
        <div class="kpi-strip">
          <div class="kpi-item">
            <div class="kpi-label">当前权益</div>
            <div class="kpi-value">{{ formatNum(currentRobot.current_equity) }}</div>
            <div class="kpi-unit">USDT</div>
          </div>
          <div class="kpi-divider"></div>
          <div class="kpi-item">
            <div class="kpi-label">总盈亏</div>
            <div class="kpi-value" :class="currentRobot.total_pnl >= 0 ? 'kv-up' : 'kv-down'">
              {{ currentRobot.total_pnl >= 0 ? '+' : '' }}{{ formatNum(currentRobot.total_pnl) }}
            </div>
            <div class="kpi-unit">USDT</div>
          </div>
          <div class="kpi-divider"></div>
          <div class="kpi-item">
            <div class="kpi-label">月化收益</div>
            <div class="kpi-value" :class="calcMonthlyReturn(currentRobot) >= 0 ? 'kv-up' : 'kv-down'">
              {{ calcMonthlyReturn(currentRobot) >= 0 ? '+' : '' }}{{ calcMonthlyReturn(currentRobot).toFixed(2) }}
            </div>
            <div class="kpi-unit">% / 年化 {{ calcAnnualReturn(currentRobot).toFixed(1) }}%</div>
          </div>
          <div class="kpi-divider"></div>
          <div class="kpi-item">
            <div class="kpi-label">胜率</div>
            <div class="kpi-value" :class="currentRobot.win_rate >= 70 ? 'kv-up' : ''">
              {{ currentRobot.win_rate.toFixed(1) }}
            </div>
            <div class="kpi-unit">%</div>
          </div>
          <div class="kpi-divider"></div>
          <div class="kpi-item">
            <div class="kpi-label">最大回撤</div>
            <div class="kpi-value kv-down">{{ currentRobot.max_drawdown.toFixed(1) }}</div>
            <div class="kpi-unit">%</div>
          </div>
          <div class="kpi-divider"></div>
          <div class="kpi-item">
            <div class="kpi-label">交易次数</div>
            <div class="kpi-value">{{ currentRobot.trade_count }}</div>
            <div class="kpi-unit">笔</div>
          </div>
        </div>

        <!-- 策略 & 配置双栏 -->
        <div class="info-row">
          <!-- 策略列表 -->
          <div class="info-block">
            <div class="block-head">
              <span class="block-title">运行策略</span>
              <span class="block-badge">{{ currentRobot.strategies?.length || 0 }}</span>
            </div>
            <div class="strategy-list" v-if="currentRobot.strategies && currentRobot.strategies.length > 0">
              <div v-for="(s, i) in currentRobot.strategies" :key="i" class="strategy-chip">
                <span class="chip-dot"></span>
                {{ formatStrategyName(typeof s === 'string' ? s : s.type) }}
              </div>
            </div>
            <div v-else class="block-empty">暂未配置策略</div>
          </div>
          <!-- 参数配置 -->
          <div class="info-block">
            <div class="block-head">
              <span class="block-title">参数配置</span>
            </div>
            <div class="param-grid">
              <div class="param-row">
                <span class="param-key">杠杆倍数</span>
                <span class="param-val highlight">{{ currentRobot.leverage || 10 }}x</span>
              </div>
              <div class="param-row">
                <span class="param-key">下单方式</span>
                <span class="param-val">{{ currentRobot.size_mode === 'percent' ? currentRobot.size_pct + '% 仓位' : '固定 ' + currentRobot.size + ' 张' }}</span>
              </div>
              <div class="param-row">
                <span class="param-key">初始资金</span>
                <span class="param-val">{{ formatNum(currentRobot.initial_capital) }} U</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 交易记录 -->
        <div class="trades-section">
          <div class="trades-head">
            <div class="trades-title-row">
              <span class="block-title">交易记录</span>
              <span class="block-badge">{{ currentRobot.trade_count }} 笔</span>
            </div>
          </div>
          <div v-if="tradesLoading" class="trades-loading">
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else-if="trades.length === 0" class="trades-empty">
            <div class="empty-illustration">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect x="4" y="8" width="40" height="32" rx="4" stroke="#333" stroke-width="1.5"/>
                <line x1="4" y1="16" x2="44" y2="16" stroke="#333" stroke-width="1.5"/>
                <line x1="12" y1="24" x2="36" y2="24" stroke="#444" stroke-width="1"/>
                <line x1="12" y1="30" x2="28" y2="30" stroke="#444" stroke-width="1"/>
              </svg>
            </div>
            <span>暂无交易记录</span>
          </div>
          <div v-else class="trades-table-wrap">
            <table class="trades-table">
              <thead>
                <tr>
                  <th class="th-strategy">策略</th>
                  <th class="th-side">方向</th>
                  <th class="th-time">开仓时间</th>
                  <th class="th-price">开仓价</th>
                  <th class="th-price">平仓价</th>
                  <th class="th-reason">平仓触发</th>
                  <th class="th-pnl">盈亏</th>
                  <th class="th-hold">持仓时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="trade in trades" :key="trade.id" :class="{ 'row-open': trade.status === 'open' }">
                  <td class="td-strategy">{{ formatStrategyName(trade.strategy_type) }}</td>
                  <td>
                    <span class="side-badge" :class="trade.side === 'long' ? 'badge-long' : 'badge-short'">
                      {{ trade.side === 'long' ? '做多' : '做空' }}
                    </span>
                  </td>
                  <td class="td-time">{{ formatTime(trade.opened_at) }}</td>
                  <td class="td-price">{{ trade.entry_price ? formatNum(trade.entry_price, 1) : '-' }}</td>
                  <td class="td-price">{{ trade.exit_price ? formatNum(trade.exit_price, 1) : '-' }}</td>
                  <td>
                    <span v-if="trade.status === 'open'" class="reason-badge reason-holding">持仓中</span>
                    <span v-else class="reason-badge" :class="reasonClass(trade.close_reason)">
                      {{ formatCloseReason(trade.close_reason) }}
                    </span>
                  </td>
                  <td class="td-pnl" :class="trade.pnl >= 0 ? 'pnl-up' : 'pnl-dn'">
                    {{ trade.pnl >= 0 ? '+' : '' }}{{ trade.pnl.toFixed(2) }}
                  </td>
                  <td class="td-hold">{{ formatHoldingTime(trade.opened_at, trade.closed_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, Promotion, Position, Document, Collection, TrendCharts, Trophy, ArrowDown } from '@element-plus/icons-vue'
import api from '../utils/api'

const robots = ref([])
const loading = ref(true)
const strategyTemplates = ref([])

// 详情弹窗
const detailVisible = ref(false)
const tradesLoading = ref(false)
const trades = ref([])
const currentRobot = ref(null)

function formatNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '--'
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

function formatTime(isoStr) {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatStrategyName(type) {
  if (!type) return '未知'
  const tpl = strategyTemplates.value.find(t => t.type === type)
  return tpl ? tpl.name : type
}

function formatCloseReason(reason) {
  const map = {
    fixed_tp: '固定止盈',
    fixed_sl: '固定止损',
    trailing: '移动止盈',
    timeout: '超时平仓',
    manual: '手动平仓',
    liquidation: '强制清算',
  }
  return map[reason] || reason || '未知'
}

function reasonClass(reason) {
  const map = {
    fixed_tp: 'reason-tp',
    fixed_sl: 'reason-sl',
    trailing: 'reason-trailing',
    timeout: 'reason-timeout',
    manual: 'reason-manual',
  }
  return map[reason] || ''
}

function formatHoldingTime(openedAt, closedAt) {
  if (!openedAt) return '-'
  const open = new Date(openedAt)
  const close = closedAt ? new Date(closedAt) : new Date()
  const hours = (close - open) / (1000 * 60 * 60)
  if (hours < 0.5) return '<30分钟'
  if (hours < 1) return `${Math.round(hours * 60)}分钟`
  if (hours < 24) return `${hours.toFixed(1)}小时`
  const days = Math.floor(hours / 24)
  const remainHours = Math.round(hours % 24)
  if (remainHours === 0) return `${days}天`
  return `${days}天${remainHours}时`
}

function calcPnlPct(robot) {
  if (!robot.initial_capital) return 0
  return ((robot.total_pnl / robot.initial_capital) * 100).toFixed(2)
}

function calcMonthlyReturn(robot) {
  if (!robot.initial_capital || !robot.created_at) return 0
  const totalReturn = (robot.total_pnl / robot.initial_capital) * 100
  const createdAt = new Date(robot.created_at)
  const now = new Date()
  const daysRunning = Math.max(1, Math.floor((now - createdAt) / (1000 * 60 * 60 * 24)))
  return (totalReturn / daysRunning) * 30
}

function calcAnnualReturn(robot) {
  return calcMonthlyReturn(robot) * 12
}

async function openDetail(robot) {
  currentRobot.value = robot
  detailVisible.value = true
  tradesLoading.value = true
  trades.value = []
  try {
    const res = await api.get(`/robots/${robot.id}/trades`)
    trades.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('Failed to fetch trades:', e)
    trades.value = []
  } finally {
    tradesLoading.value = false
  }
}

async function fetchRobots() {
  loading.value = true
  try {
    const res = await api.get('/robots')
    robots.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('Failed to fetch robots:', e)
  } finally {
    loading.value = false
  }
}

async function fetchTemplates() {
  try {
    const res = await api.get('/strategy/available')
    strategyTemplates.value = Array.isArray(res?.strategies) ? res.strategies : []
  } catch {
    strategyTemplates.value = []
  }
}

function handleFollow(robot) {
  ElMessage.info(`跟随功能开发中，机器人: ${robot.name}`)
}

onMounted(() => {
  fetchRobots()
  fetchTemplates()
})
</script>

<style scoped>
.robots-page { min-height: 100%; }

.page-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  margin-bottom: 20px;
  font-size: 13px;
  color: var(--accent);
}

.loading-wrap { padding: 40px 0; }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.empty-icon-wrap {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.empty-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.empty-desc { font-size: 13px; color: var(--text-muted); }

/* 卡片网格 */
.robot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

.robot-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s;
  cursor: pointer;
}

.robot-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.robot-card.robot-running { border-color: rgba(34, 197, 94, 0.3); }

.robot-card.robot-running::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #22c55e, #10b981);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(180deg, var(--bg-secondary), transparent);
}

.robot-avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.robot-avatar.avatar-active {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.2));
}

.avatar-emoji { font-size: 24px; }
.robot-info { flex: 1; min-width: 0; }

.robot-name { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }

.robot-status { display: flex; align-items: center; gap: 6px; }

.status-dot { width: 6px; height: 6px; border-radius: 50%; }

.dot-running {
  background: #22c55e;
  box-shadow: 0 0 6px #22c55e;
  animation: pulse 2s infinite;
}

.dot-stopped { background: #94a3b8; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text { font-size: 12px; color: var(--text-muted); }

.robot-pnl-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  flex-shrink: 0;
}

.pnl-up { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.pnl-down { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.pnl-arrow { font-size: 14px; }
.pnl-pct { font-size: 14px; font-weight: 700; }

/* 主要指标区 */
.card-main { padding: 0 16px 16px; }

.main-metrics {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-secondary);
  margin-bottom: 12px;
}

.main-metric { flex: 1; text-align: center; }
.main-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }

.main-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.main-divider { width: 1px; height: 32px; background: var(--border-secondary); }

/* 月化收益卡片 */
.monthly-return-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: 12px;
  margin-bottom: 12px;
}

.return-positive {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.12), rgba(16, 185, 129, 0.08));
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.return-negative {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(248, 113, 113, 0.08));
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.return-left { display: flex; align-items: center; gap: 12px; }

.return-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.return-positive .return-icon { background: rgba(34, 197, 94, 0.2); }
.return-negative .return-icon { background: rgba(239, 68, 68, 0.2); }

.return-info { display: flex; flex-direction: column; gap: 2px; }
.return-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.return-desc { font-size: 11px; color: var(--text-muted); }
.return-right { display: flex; align-items: baseline; gap: 2px; }

.return-value {
  font-size: 28px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.return-positive .return-value { color: #22c55e; }
.return-negative .return-value { color: #ef4444; }
.return-unit { font-size: 14px; font-weight: 600; color: var(--text-muted); }

/* 次要指标网格 */
.sub-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.sub-metric {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.sub-icon { font-size: 14px; color: var(--text-muted); }
.icon-success { color: #22c55e; }
.icon-danger { color: #ef4444; }
.sub-content { flex: 1; min-width: 0; }

.sub-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.sub-label { font-size: 10px; color: var(--text-muted); }

/* 底部按钮 */
.card-footer {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-secondary);
}

.card-footer .el-button { flex: 1; }

.follow-btn {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
}

.follow-btn:hover { background: linear-gradient(135deg, #2563eb, #7c3aed); }

.record-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
}

.record-btn:hover { border-color: var(--accent); color: var(--accent); }

/* 数值颜色 */
.val-up { color: #22c55e !important; }
.val-down { color: #ef4444 !important; }

/* 响应式 */
@media (max-width: 768px) {
  .robot-grid { grid-template-columns: 1fr; }
  .sub-metrics { grid-template-columns: repeat(2, 1fr); }
}
</style>

<style>
/* 弹窗全局样式 - el-dialog 通过 teleport 渲染在 body 下，scoped 样式无法生效 */

/* === 弹窗容器 === */
.robot-detail-dialog {
  --el-dialog-bg-color: var(--bg-card);
  --el-dialog-border-radius: 18px;
  border: 1px solid var(--border-secondary);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6), 0 0 1px rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.robot-detail-dialog .el-dialog__header {
  padding: 20px 28px 12px;
  margin-right: 0;
  border-bottom: 1px solid var(--border-primary);
}

.robot-detail-dialog .el-dialog__body {
  padding: 20px 28px 28px;
}

.robot-detail-dialog .el-dialog__headerbtn {
  top: 18px;
  right: 20px;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  transition: all 0.2s;
}

.robot-detail-dialog .el-dialog__headerbtn:hover {
  background: var(--bg-hover);
  border-color: var(--border-secondary);
}

.robot-detail-dialog .el-dialog__headerbtn .el-dialog__close {
  color: var(--text-muted);
  font-size: 14px;
}

.robot-detail-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: var(--text-primary);
}

.robot-detail-dialog .el-overlay {
  backdrop-filter: blur(4px);
  background: rgba(0, 0, 0, 0.5);
}

/* === 弹窗头部 === */
.dlg-header { padding: 0; }

.dlg-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.dlg-robot-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.dlg-robot-icon.icon-active {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.25);
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.1);
}

.dlg-title-info { flex: 1; }

.dlg-robot-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.dlg-robot-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.meta-status { display: flex; align-items: center; gap: 5px; }
.meta-dot { width: 6px; height: 6px; border-radius: 50%; }
.dot-on { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.5); animation: pulse 2s infinite; }
.dot-off { background: #64748b; }
.status-running { color: #22c55e; }
.status-stopped { color: #64748b; }
.meta-sep { color: var(--border-secondary); }
.meta-strategies { color: var(--text-muted); }
.meta-pnl { font-weight: 600; }
.pnl-green { color: #22c55e; }
.pnl-red { color: #ef4444; }

/* === 弹窗主体 === */
.detail-body {
  padding: 0;
  margin-top: -8px;
}

/* === KPI 指标条 === */
.kpi-strip {
  display: flex;
  align-items: stretch;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  padding: 18px 24px;
  margin-bottom: 18px;
  gap: 0;
}

.kpi-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.kpi-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 6px;
  letter-spacing: 0.3px;
}

.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary) !important;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.kv-up { color: #22c55e !important; }
.kv-down { color: #ef4444 !important; }

.kpi-unit {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 4px;
  white-space: nowrap;
}

.kpi-divider {
  width: 1px;
  background: var(--border-secondary);
  margin: 4px 0;
  flex-shrink: 0;
}

/* === 信息双栏 === */
.info-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 18px;
}

.info-block {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 14px;
  padding: 16px 20px;
}

.block-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.block-badge {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-light);
  padding: 2px 8px;
  border-radius: 10px;
}

.block-empty {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 8px 0;
}

/* 策略列表 */
.strategy-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.strategy-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.strategy-chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.chip-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

/* 参数网格 */
.param-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.param-row + .param-row {
  border-top: 1px solid var(--border-primary);
}

.param-key {
  font-size: 12px;
  color: var(--text-muted);
}

.param-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.param-val.highlight {
  color: var(--accent);
}

/* === 交易记录区 === */
.trades-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 14px;
  padding: 16px 20px;
}

.trades-head { margin-bottom: 14px; }

.trades-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trades-loading,
.trades-empty {
  padding: 32px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.empty-illustration {
  margin-bottom: 10px;
  opacity: 0.4;
}

.trades-table-wrap {
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  background: var(--bg-card);
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  white-space: nowrap;
}

.trades-table thead { background: var(--bg-secondary); }

.trades-table th {
  padding: 11px 14px;
  text-align: left;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 11px;
  border-bottom: 1px solid var(--border-primary);
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.trades-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-primary);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.trades-table tbody tr:last-child td { border-bottom: none; }
.trades-table tbody tr:hover { background: var(--bg-hover); }
.trades-table tbody tr.row-open { background: rgba(59, 130, 246, 0.04); }

.td-strategy { color: var(--text-primary); font-weight: 500; }
.td-time { color: var(--text-muted); font-size: 11px; }
.td-price { color: var(--text-secondary); }
.td-pnl { font-weight: 700; }
.td-pnl.pnl-up { color: #22c55e !important; }
.td-pnl.pnl-dn { color: #ef4444 !important; }
.td-hold { color: var(--text-muted); font-size: 11px; }

/* 方向徽章 */
.side-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.badge-long { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
.badge-short { background: rgba(34, 197, 94, 0.1); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.2); }

/* 平仓原因徽章 */
.reason-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid transparent;
}

.reason-holding { background: rgba(59, 130, 246, 0.1); color: #60a5fa; border-color: rgba(59, 130, 246, 0.2); }
.reason-tp { background: rgba(239, 68, 68, 0.08); color: #f87171; border-color: rgba(239, 68, 68, 0.15); }
.reason-sl { background: rgba(34, 197, 94, 0.08); color: #4ade80; border-color: rgba(34, 197, 94, 0.15); }
.reason-trailing { background: rgba(59, 130, 246, 0.08); color: #60a5fa; border-color: rgba(59, 130, 246, 0.15); }
.reason-timeout { background: rgba(245, 158, 11, 0.08); color: #fbbf24; border-color: rgba(245, 158, 11, 0.15); }
.reason-manual { background: rgba(148, 163, 184, 0.08); color: #94a3b8; border-color: rgba(148, 163, 184, 0.15); }

/* 响应式 */
@media (max-width: 768px) {
  .kpi-strip { flex-wrap: wrap; gap: 12px; padding: 14px 16px; }
  .kpi-divider { display: none; }
  .kpi-item { flex: 0 0 calc(33% - 8px); }
  .info-row { grid-template-columns: 1fr; }
}
</style>
