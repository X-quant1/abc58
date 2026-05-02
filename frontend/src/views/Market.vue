<template>
  <div class="market-page">
    <el-card shadow="hover" class="panel-card">
      <template #header>
        <div class="panel-header">
          <div class="header-controls">
            <el-select v-model="symbol" style="width: 150px;" @change="fetchKline">
              <el-option v-for="s in symbolList" :key="s.symbol" :label="s.symbol" :value="s.symbol" />
            </el-select>
            <el-radio-group v-model="timeframe" size="small" @change="fetchKline">
              <el-radio-button label="1m">1分</el-radio-button>
              <el-radio-button label="5m">5分</el-radio-button>
              <el-radio-button label="15m">15分</el-radio-button>
              <el-radio-button label="1h">1时</el-radio-button>
              <el-radio-button label="4h">4时</el-radio-button>
              <el-radio-button label="1d">日线</el-radio-button>
            </el-radio-group>
          </div>
          <div class="header-right">
            <div v-if="ticker" class="ticker-info">
              <span class="ticker-price" :class="ticker.change_24h >= 0 ? 'up' : 'down'">
                ${{ ticker.price?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
              </span>
              <span class="ticker-change" :class="ticker.change_24h >= 0 ? 'up' : 'down'">
                {{ ticker.change_24h >= 0 ? '+' : '' }}{{ ticker.change_24h }}%
              </span>
            </div>
            <el-button text size="small" @click="fetchKline" :loading="loading">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
      </template>
      <div ref="chartRef" class="chart-container" v-loading="loading && klineData.length === 0"></div>
      <div v-if="!loading && klineData.length === 0" class="chart-empty">
        <el-icon :size="40" color="#dcdfe6"><TrendCharts /></el-icon>
        <p>{{ errorMsg || '点击刷新加载K线数据' }}</p>
      </div>
    </el-card>

    <el-card shadow="hover" class="panel-card" style="margin-top: 20px;">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">实时行情</span>
          <el-button text size="small" @click="fetchMultiTickers" :loading="tickerLoading">刷新</el-button>
        </div>
      </template>
      <el-table :data="tickerList" stripe empty-text="点击刷新加载行情" style="width: 100%" v-loading="tickerLoading">
        <el-table-column prop="symbol" label="交易对" width="140">
          <template #default="{ row }">
            <span style="font-weight:600;">{{ row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="最新价" align="right">
          <template #default="{ row }">
            <span :class="row.change_24h >= 0 ? 'up' : 'down'" style="font-weight:600;">
              ${{ row.price?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="change_24h" label="24h涨跌" align="right" width="100">
          <template #default="{ row }">
            <span :class="row.change_24h >= 0 ? 'up' : 'down'" style="font-weight:600;">
              {{ row.change_24h >= 0 ? '+' : '' }}{{ row.change_24h }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="high" label="24h最高" align="right">
          <template #default="{ row }">
            ${{ row.high?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </template>
        </el-table-column>
        <el-table-column prop="low" label="24h最低" align="right">
          <template #default="{ row }">
            ${{ row.low?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </template>
        </el-table-column>
        <el-table-column prop="volume" label="24h成交量" align="right">
          <template #default="{ row }">
            {{ row.volume?.toLocaleString(undefined, {maximumFractionDigits: 2}) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { createChart, ColorType } from 'lightweight-charts'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'

const { on: wsOn, off: wsOff } = useWebSocket()

const symbol = ref('BTC-USDT')
const timeframe = ref('1h')
const loading = ref(false)
const tickerLoading = ref(false)
const klineData = ref([])
const ticker = ref(null)
const tickerList = ref([])
const errorMsg = ref('')
const chartRef = ref(null)
let chart = null
let candleSeries = null
let volumeSeries = null

const symbolList = [
  { symbol: 'BTC-USDT' }, { symbol: 'ETH-USDT' }, { symbol: 'SOL-USDT' },
  { symbol: 'XRP-USDT' }, { symbol: 'DOGE-USDT' }, { symbol: 'ADA-USDT' },
  { symbol: 'AVAX-USDT' }, { symbol: 'DOT-USDT' }, { symbol: 'LINK-USDT' },
  { symbol: 'BNB-USDT' },
]

// ─── WebSocket 实时行情 ───

function onWsTicker(data) {
  // 更新当前查看的交易对价格
  if (data && data.symbol === symbol.value) {
    ticker.value = data
  }
  // 更新行情表
  if (data && tickerList.value.length > 0) {
    const idx = tickerList.value.findIndex(t => t.symbol === data.symbol)
    if (idx >= 0) {
      tickerList.value[idx] = { ...tickerList.value[idx], ...data }
    }
  }
}

async function fetchKline() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.get('/market/kline', {
      params: { symbol: symbol.value, timeframe: timeframe.value, limit: 200 }
    })
    klineData.value = res.data || []
    if (klineData.value.length > 0) {
      await nextTick()
      renderChart()
    }
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '获取K线数据失败，请稍后重试'
    klineData.value = []
  } finally {
    loading.value = false
  }
  fetchTicker()
}

async function fetchTicker() {
  try {
    const res = await api.get('/market/ticker', { params: { symbol: symbol.value } })
    ticker.value = res
  } catch { /* ignore */ }
}

async function fetchMultiTickers() {
  tickerLoading.value = true
  try {
    const res = await api.get('/market/tickers')
    tickerList.value = res.data || []
  } catch { /* ignore */ }
  finally { tickerLoading.value = false }
}

function renderChart() {
  if (!chartRef.value || klineData.value.length === 0) return

  if (!chart) {
    chart = createChart(chartRef.value, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#86909c',
      },
      grid: {
        vertLines: { color: '#f2f3f5' },
        horzLines: { color: '#f2f3f5' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: '#e5e6eb',
        scaleMargins: { top: 0.1, bottom: 0.3 },
      },
      timeScale: {
        borderColor: '#e5e6eb',
        timeVisible: true,
      },
      width: chartRef.value.clientWidth,
      height: chartRef.value.clientHeight,
    })

    candleSeries = chart.addCandlestickSeries({
      upColor: '#ef5350',
      downColor: '#26a69a',
      borderUpColor: '#ef5350',
      borderDownColor: '#26a69a',
      wickUpColor: '#ef5350',
      wickDownColor: '#26a69a',
    })

    volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    })
  }

  const candleData = klineData.value.map(d => ({
    time: Math.floor(d.timestamp / 1000),
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }))

  const volumeData = klineData.value.map(d => ({
    time: Math.floor(d.timestamp / 1000),
    value: d.volume,
    color: d.close >= d.open ? '#ef535033' : '#26a69a33',
  }))

  candleSeries.setData(candleData)
  volumeSeries.setData(volumeData)
  chart.timeScale().fitContent()
}

function onResize() {
  if (chart && chartRef.value) {
    chart.applyOptions({
      width: chartRef.value.clientWidth,
      height: chartRef.value.clientHeight,
    })
  }
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await fetchKline()
  await fetchMultiTickers()

  // 注册 WebSocket 实时行情
  wsOn('ticker', onWsTicker)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.remove()
  chart = null
  wsOff('ticker', onWsTicker)
})
</script>

<style scoped>
.panel-card { border-radius: 10px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; }
.header-controls { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.panel-title { font-size: 15px; font-weight: 600; color: #1d2129; }

.ticker-info { display: flex; align-items: baseline; gap: 6px; }
.ticker-price { font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }
.ticker-change { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
.up { color: #ef5350; }
.down { color: #26a69a; }

.chart-container { height: 450px; min-height: 300px; }
.chart-empty { height: 450px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #c9cdd4; }
.chart-empty p { margin-top: 10px; font-size: 13px; }
</style>
