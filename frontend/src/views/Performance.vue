<template>
  <div class="performance-page">
    <!-- 时间范围选择 -->
    <el-card shadow="hover" class="panel-card" style="margin-bottom: 20px;">
      <div class="filter-bar">
        <el-radio-group v-model="dateRange" size="small" @change="loadAll">
          <el-radio-button label="7">近 7 天</el-radio-button>
          <el-radio-button label="30">近 30 天</el-radio-button>
          <el-radio-button label="90">近 90 天</el-radio-button>
          <el-radio-button label="365">近 1 年</el-radio-button>
        </el-radio-group>
        <el-button type="primary" size="small" @click="loadAll" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </el-card>

    <!-- 概览指标 -->
    <div class="metrics-grid">
      <div v-for="m in overviewCards" :key="m.label" class="metric-card">
        <div class="metric-top">
          <span class="metric-label">{{ m.label }}</span>
          <div class="metric-icon" :style="{ background: m.bgColor }">
            <el-icon :size="16" :color="m.color"><component :is="m.icon" /></el-icon>
          </div>
        </div>
        <div class="metric-value" :style="{ color: m.valueColor || '#1d2129' }">{{ m.value }}</div>
        <div class="metric-sub" v-if="m.sub">{{ m.sub }}</div>
      </div>
    </div>

    <!-- 图表区 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">盈亏曲线</span>
              <el-radio-group v-model="curveType" size="small">
                <el-radio-button label="daily">每日</el-radio-button>
                <el-radio-button label="cumulative">累计</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="pnlChartRef" style="height: 350px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">盈亏分布</span>
            </div>
          </template>
          <div ref="distChartRef" style="height: 350px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 月度收益 + 策略对比 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="14">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">月度收益</span>
            </div>
          </template>
          <div ref="monthlyChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">策略对比</span>
            </div>
          </template>
          <el-table :data="strategyData" stripe empty-text="暂无策略数据" size="small" style="width: 100%">
            <el-table-column prop="strategy_name" label="策略" min-width="120" show-overflow-tooltip />
            <el-table-column label="盈亏" align="right" width="100">
              <template #default="{ row }">
                <span :style="{ color: row.pnl >= 0 ? '#f53f3f' : '#00b42a', fontWeight: 600 }">
                  {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl.toFixed(4) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="胜率" align="right" width="70">
              <template #default="{ row }">{{ row.win_rate }}%</template>
            </el-table-column>
            <el-table-column prop="count" label="交易数" align="right" width="70" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 交易明细 -->
    <el-card shadow="hover" class="panel-card" style="margin-top: 20px;">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">交易明细</span>
          <el-select v-model="strategyFilter" size="small" placeholder="全部策略" clearable style="width: 160px; margin-right: 8px;">
            <el-option v-for="s in strategyOptions" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
      </template>
      <el-table :data="tradeList" stripe empty-text="暂无交易记录" style="width: 100%" max-height="400">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="strategy_name" label="策略" width="120" show-overflow-tooltip />
        <el-table-column prop="symbol" label="交易对" width="140" />
        <el-table-column label="方向" width="80">
          <template #default="{ row }">
            <el-tag :type="directionType(row.direction || row.side)" size="small" effect="plain">
              {{ directionLabel(row.direction || row.side) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="价格" align="right">
          <template #default="{ row }">{{ row.price?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="数量" align="right" />
        <el-table-column label="盈亏" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.pnl >= 0 ? '#f53f3f' : '#00b42a', fontWeight: 600 }">
              {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl?.toFixed(4) || '0' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="手续费" align="right">
          <template #default="{ row }">{{ row.fee?.toFixed(4) || '0' }}</template>
        </el-table-column>
        <el-table-column label="净盈亏" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.net_pnl >= 0 ? '#f53f3f' : '#00b42a', fontWeight: 600 }">
              {{ row.net_pnl >= 0 ? '+' : '' }}{{ row.net_pnl?.toFixed(4) || '0' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import api from '../utils/api'

const dateRange = ref('30')
const curveType = ref('daily')
const loading = ref(false)
const strategyFilter = ref('')

const overview = ref({})
const dailyPnl = ref([])
const monthlyPnl = ref([])
const strategyData = ref([])
const pnlDist = ref([])
const tradeList = ref([])
const strategyOptions = ref([])

const pnlChartRef = ref(null)
const distChartRef = ref(null)
const monthlyChartRef = ref(null)
let pnlChart = null
let distChart = null
let monthlyChart = null

// ─── 概览卡片 ───

const overviewCards = computed(() => {
  const d = overview.value
  if (!d.has_data) {
    return [
      { label: '总盈亏', value: '$0.00', color: '#f7931a', bgColor: '#fff7e8', icon: 'Coin' },
      { label: '净盈亏', value: '$0.00', color: '#00b42a', bgColor: '#e8ffea', icon: 'Wallet' },
      { label: '胜率', value: '--', color: '#3491fa', bgColor: '#e8f3ff', icon: 'Trophy' },
      { label: '交易次数', value: '0', color: '#ff7d00', bgColor: '#fff7e8', icon: 'ShoppingCart' },
      { label: '夏普比率', value: '--', color: '#722ed1', bgColor: '#f5e8ff', icon: 'TrendCharts' },
      { label: '最大回撤', value: '--', color: '#f53f3f', bgColor: '#ffece8', icon: 'Bottom' },
      { label: '手续费', value: '$0.00', color: '#86909c', bgColor: '#f2f3f5', icon: 'Coin' },
      { label: '盈亏比', value: '--', color: '#0fc6c2', bgColor: '#e8fffb', icon: 'ScaleToOriginal' },
    ]
  }
  const pnlColor = d.total_pnl >= 0 ? '#f53f3f' : '#00b42a'
  const netColor = d.net_pnl >= 0 ? '#f53f3f' : '#00b42a'
  return [
    { label: '总盈亏', value: fmtPnl(d.total_pnl), color: '#f7931a', bgColor: '#fff7e8', icon: 'Coin', valueColor: pnlColor },
    { label: '净盈亏', value: fmtPnl(d.net_pnl), color: '#00b42a', bgColor: '#e8ffea', icon: 'Wallet', valueColor: netColor, sub: `盈 ${d.win_count} / 亏 ${d.lose_count}` },
    { label: '胜率', value: d.win_rate + '%', color: '#3491fa', bgColor: '#e8f3ff', icon: 'Trophy', valueColor: d.win_rate >= 50 ? '#f53f3f' : '#00b42a' },
    { label: '交易次数', value: String(d.trade_count), color: '#ff7d00', bgColor: '#fff7e8', icon: 'ShoppingCart', sub: `多 ${d.long_count} / 空 ${d.short_count}` },
    { label: '夏普比率', value: String(d.sharpe_ratio), color: '#722ed1', bgColor: '#f5e8ff', icon: 'TrendCharts' },
    { label: '最大回撤', value: '-' + d.max_drawdown + '%', color: '#f53f3f', bgColor: '#ffece8', icon: 'Bottom' },
    { label: '手续费', value: '$' + (d.total_fee || 0).toFixed(4), color: '#86909c', bgColor: '#f2f3f5', icon: 'Coin' },
    { label: '盈亏比', value: d.profit_factor >= 999 ? 'N/A' : String(d.profit_factor), color: '#0fc6c2', bgColor: '#e8fffb', icon: 'ScaleToOriginal' },
  ]
})

function fmtPnl(v) {
  if (v === undefined || v === null) return '$0.00'
  const sign = v >= 0 ? '+' : ''
  return sign + '$' + Math.abs(v).toFixed(4)
}

// ─── 数据加载 ───

async function loadAll() {
  loading.value = true
  const days = parseInt(dateRange.value)
  try {
    const [ov, daily, monthly, strat, dist, trades] = await Promise.all([
      api.get('/performance/overview', { params: { days } }),
      api.get('/performance/daily-pnl', { params: { days } }),
      api.get('/performance/monthly-pnl', { params: { months: Math.ceil(days / 30) } }),
      api.get('/performance/strategy-comparison'),
      api.get('/performance/pnl-distribution'),
      api.get('/performance/trades', { params: { days, limit: 200, strategy_id: strategyFilter.value || 0 } }),
    ])
    overview.value = ov
    dailyPnl.value = daily.data || []
    monthlyPnl.value = monthly.data || []
    strategyData.value = strat.data || []
    pnlDist.value = dist.data || []
    tradeList.value = trades.trades || []

    // 策略选项
    strategyOptions.value = strat.data?.map(s => ({ id: s.strategy_id, name: s.strategy_name })) || []

    await nextTick()
    renderPnlChart()
    renderDistChart()
    renderMonthlyChart()
  } catch (e) {
    console.error('Performance load error:', e)
  } finally {
    loading.value = false
  }
}

// ─── 图表渲染 ───

function renderPnlChart() {
  if (!pnlChartRef.value) return
  if (!pnlChart) pnlChart = echarts.init(pnlChartRef.value)

  const data = dailyPnl.value
  if (!data.length) {
    pnlChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#c9cdd4', fontSize: 14 } },
      xAxis: { show: false }, yAxis: { show: false }, series: []
    })
    return
  }

  const dates = data.map(d => d.date)
  if (curveType.value === 'daily') {
    const values = data.map(d => d.pnl)
    pnlChart.setOption({
      tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}<br/>盈亏: <b>${p[0].value >= 0 ? '+' : ''}${p[0].value.toFixed(4)}</b>` },
      grid: { left: 70, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: v => v.toFixed(2) }, splitLine: { lineStyle: { color: '#f2f3f5' } } },
      series: [{
        type: 'bar',
        data: values.map(v => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#f53f3f' : '#00b42a' }
        })),
        barMaxWidth: 20,
      }]
    }, true)
  } else {
    const values = data.map(d => d.cumulative_pnl)
    pnlChart.setOption({
      tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}<br/>累计: <b>${p[0].value >= 0 ? '+' : ''}${p[0].value.toFixed(4)}</b>` },
      grid: { left: 70, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: v => v.toFixed(2) }, splitLine: { lineStyle: { color: '#f2f3f5' } } },
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
    }, true)
  }
}

function renderDistChart() {
  if (!distChartRef.value) return
  if (!distChart) distChart = echarts.init(distChartRef.value)

  const data = pnlDist.value
  if (!data.length) {
    distChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#c9cdd4', fontSize: 14 } },
      xAxis: { show: false }, yAxis: { show: false }, series: []
    })
    return
  }

  const ranges = data.map(d => d.range)
  const counts = data.map(d => d.count)
  const colors = ['#00b42a', '#4cd964', '#86c166', '#f7931a', '#f53f3f', '#d43030']

  distChart.setOption({
    tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}<br/>交易笔数: <b>${p[0].value}</b>` },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: ranges, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#f2f3f5' } } },
    series: [{
      type: 'bar',
      data: counts.map((v, i) => ({ value: v, itemStyle: { color: colors[i] || '#f7931a' } })),
      barMaxWidth: 36,
    }]
  }, true)
}

function renderMonthlyChart() {
  if (!monthlyChartRef.value) return
  if (!monthlyChart) monthlyChart = echarts.init(monthlyChartRef.value)

  const data = monthlyPnl.value
  if (!data.length) {
    monthlyChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#c9cdd4', fontSize: 14 } },
      xAxis: { show: false }, yAxis: { show: false }, series: []
    })
    return
  }

  const months = data.map(d => d.month)
  const values = data.map(d => d.pnl)

  monthlyChart.setOption({
    tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}<br/>月度盈亏: <b>${p[0].value >= 0 ? '+' : ''}${p[0].value.toFixed(4)}</b>` },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: months, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { formatter: v => v.toFixed(2) }, splitLine: { lineStyle: { color: '#f2f3f5' } } },
    series: [{
      type: 'bar',
      data: values.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? '#f53f3f' : '#00b42a' }
      })),
      barMaxWidth: 32,
    }]
  }, true)
}

// ─── 工具函数 ───

function directionLabel(d) {
  const map = {
    open_long: '开多', open_short: '开空', close_long: '平多', close_short: '平空',
    buy: '买入', sell: '卖出',
  }
  return map[d] || d
}

function directionType(d) {
  if (d === 'open_long' || d === 'close_short' || d === 'buy') return 'danger'
  if (d === 'open_short' || d === 'close_long' || d === 'sell') return 'success'
  return 'info'
}

function formatTime(ts) {
  if (!ts) return '--'
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts
  return d.toLocaleString('zh-CN')
}

// ─── 生命周期 ───

watch(curveType, () => renderPnlChart())
watch(strategyFilter, () => loadTrades())

async function loadTrades() {
  try {
    const res = await api.get('/performance/trades', {
      params: { days: parseInt(dateRange.value), limit: 200, strategy_id: strategyFilter.value || 0 }
    })
    tradeList.value = res.trades || []
  } catch { /* ignore */ }
}

function handleResize() {
  pnlChart?.resize()
  distChart?.resize()
  monthlyChart?.resize()
}

onMounted(async () => {
  await loadAll()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pnlChart?.dispose()
  distChart?.dispose()
  monthlyChart?.dispose()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 18px;
  transition: box-shadow 0.2s;
}

.metric-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.metric-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.metric-label {
  font-size: 13px;
  color: #86909c;
  font-weight: 500;
}

.metric-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.metric-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #86909c;
}

.panel-card { border-radius: 10px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; }
.panel-title { font-size: 15px; font-weight: 600; color: #1d2129; }

/* 响应式 */
@media (max-width: 1200px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
  .metric-value { font-size: 18px; }
  .el-row .el-col { max-width: 100% !important; flex: 0 0 100% !important; }
}
</style>
