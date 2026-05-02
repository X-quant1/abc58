<template>
  <div class="backtest-page">
    <!-- 回测配置 -->
    <el-card shadow="hover" class="panel-card">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">回测配置</span>
        </div>
      </template>
      <el-form :model="form" label-width="100px" class="backtest-form">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="策略类型">
              <el-select v-model="form.strategy_type" style="width: 100%;">
                <el-option
                  v-for="s in availableStrategies"
                  :key="s.type"
                  :label="s.name"
                  :value="s.type"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="交易对">
              <el-select v-model="form.symbol" style="width: 100%;">
                <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
                <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
                <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="5">
            <el-form-item label="K线周期">
              <el-select v-model="form.timeframe" style="width: 100%;">
                <el-option label="5分钟" value="5m" />
                <el-option label="15分钟" value="15m" />
                <el-option label="1小时" value="1h" />
                <el-option label="4小时" value="4h" />
                <el-option label="1天" value="1d" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="5">
            <el-form-item label="初始资金">
              <el-input-number v-model="form.initial_capital" :min="100" :step="1000" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="5">
            <el-form-item label="杠杆">
              <el-input-number v-model="form.leverage" :min="1" :max="125" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="下单方式">
              <el-radio-group v-model="form.params.size_mode">
                <el-radio value="fixed">固定张数</el-radio>
                <el-radio value="percent">仓位比例</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col v-if="form.params.size_mode === 'fixed'" :span="4">
            <el-form-item label="张数">
              <el-input-number v-model="form.params.size" :min="1" :max="1000" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col v-else :span="4">
            <el-form-item label="仓位%">
              <el-input-number v-model="form.params.size_pct" :min="1" :max="100" :step="5" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="5">
            <el-form-item label="止盈(%)">
              <el-input-number v-model="form.params.take_profit_pct" :min="0" :max="100" :step="0.5" :precision="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="5">
            <el-form-item label="止损(%)">
              <el-input-number v-model="form.params.stop_loss_pct" :min="0" :max="50" :step="0.5" :precision="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="5">
            <el-form-item label="移动止损%">
              <el-input-number v-model="form.params.trailing_stop_pct" :min="0" :max="20" :step="0.5" :precision="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="手续费%">
              <el-input-number v-model="form.fee_rate" :min="0" :max="1" :step="0.01" :precision="3" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="滑点%">
              <el-input-number v-model="form.slippage" :min="0" :max="1" :step="0.01" :precision="3" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <!-- 策略特有参数 -->
        <el-divider content-position="left">策略参数</el-divider>
        <el-row :gutter="20">
          <template v-if="form.strategy_type === 'ma_cross'">
            <el-col :span="5">
              <el-form-item label="短均线">
                <el-input-number v-model="form.params.fast_period" :min="2" :max="100" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item label="长均线">
                <el-input-number v-model="form.params.slow_period" :min="5" :max="200" style="width: 100%;" />
              </el-form-item>
            </el-col>
          </template>
          <template v-if="form.strategy_type === 'rsi'">
            <el-col :span="5">
              <el-form-item label="RSI周期">
                <el-input-number v-model="form.params.period" :min="2" :max="100" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item label="超卖线">
                <el-input-number v-model="form.params.oversold" :min="10" :max="40" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item label="超买线">
                <el-input-number v-model="form.params.overbought" :min="60" :max="90" style="width: 100%;" />
              </el-form-item>
            </el-col>
          </template>
          <template v-if="form.strategy_type === 'bollinger'">
            <el-col :span="5">
              <el-form-item label="周期">
                <el-input-number v-model="form.params.period" :min="5" :max="100" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item label="标准差">
                <el-input-number v-model="form.params.std_dev" :min="1" :max="4" :step="0.1" :precision="1" style="width: 100%;" />
              </el-form-item>
            </el-col>
          </template>
          <template v-if="form.strategy_type === 'macd'">
            <el-col :span="5"><el-form-item label="快线"><el-input-number v-model="form.params.fast_period" :min="5" :max="50" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="慢线"><el-input-number v-model="form.params.slow_period" :min="10" :max="100" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="信号线"><el-input-number v-model="form.params.signal_period" :min="3" :max="30" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'ema_volume'">
            <el-col :span="5"><el-form-item label="短EMA"><el-input-number v-model="form.params.fast_period" :min="5" :max="50" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="长EMA"><el-input-number v-model="form.params.slow_period" :min="10" :max="100" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="量均周期"><el-input-number v-model="form.params.volume_ma_period" :min="5" :max="60" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="量比阈值"><el-input-number v-model="form.params.volume_ratio" :min="1" :max="3" :step="0.1" :precision="1" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'supertrend'">
            <el-col :span="5"><el-form-item label="ATR周期"><el-input-number v-model="form.params.atr_period" :min="5" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="ATR倍数"><el-input-number v-model="form.params.multiplier" :min="1" :max="6" :step="0.5" :precision="1" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'kdj'">
            <el-col :span="4"><el-form-item label="K周期"><el-input-number v-model="form.params.k_period" :min="5" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="K平滑"><el-input-number v-model="form.params.k_smooth" :min="1" :max="10" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="D平滑"><el-input-number v-model="form.params.d_smooth" :min="1" :max="10" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="超卖线"><el-input-number v-model="form.params.oversold" :min="10" :max="40" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="超买线"><el-input-number v-model="form.params.overbought" :min="60" :max="90" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'dual_ema'">
            <el-col :span="5"><el-form-item label="趋势EMA"><el-input-number v-model="form.params.trend_period" :min="20" :max="100" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="快EMA"><el-input-number v-model="form.params.fast_period" :min="3" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="慢EMA"><el-input-number v-model="form.params.slow_period" :min="10" :max="50" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'ma_ribbon'">
            <el-col :span="4"><el-form-item label="MA1"><el-input-number v-model="form.params.period1" :min="3" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MA2"><el-input-number v-model="form.params.period2" :min="5" :max="50" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MA3"><el-input-number v-model="form.params.period3" :min="10" :max="80" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MA4"><el-input-number v-model="form.params.period4" :min="20" :max="120" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'cci'">
            <el-col :span="5"><el-form-item label="CCI周期"><el-input-number v-model="form.params.period" :min="5" :max="50" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="超卖线"><el-input-number v-model="form.params.oversold" :min="-200" :max="-50" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="超买线"><el-input-number v-model="form.params.overbought" :min="50" :max="200" style="width:100%;" /></el-form-item></el-col>
          </template>
          <!-- 多指标组合策略 -->
          <template v-if="form.strategy_type === 'trend_break'">
            <el-col :span="4"><el-form-item label="趋势EMA"><el-input-number v-model="form.params.ema_period" :min="5" :max="60" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="布林周期"><el-input-number v-model="form.params.boll_period" :min="5" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="标准差"><el-input-number v-model="form.params.boll_std" :min="0.5" :max="4" :step="0.1" :precision="1" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="量均周期"><el-input-number v-model="form.params.vol_ma_period" :min="5" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="量比"><el-input-number v-model="form.params.vol_ratio" :min="0.5" :max="3" :step="0.1" :precision="1" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'rsi_macd'">
            <el-col :span="4"><el-form-item label="RSI周期"><el-input-number v-model="form.params.rsi_period" :min="2" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="超卖"><el-input-number v-model="form.params.oversold" :min="10" :max="40" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="超买"><el-input-number v-model="form.params.overbought" :min="60" :max="90" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MACD快"><el-input-number v-model="form.params.macd_fast" :min="3" :max="20" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MACD慢"><el-input-number v-model="form.params.macd_slow" :min="10" :max="40" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="信号线"><el-input-number v-model="form.params.macd_signal" :min="3" :max="15" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'st_kdj'">
            <el-col :span="4"><el-form-item label="ATR周期"><el-input-number v-model="form.params.atr_period" :min="3" :max="20" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="ATR倍数"><el-input-number v-model="form.params.multiplier" :min="1" :max="6" :step="0.5" :precision="1" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="K周期"><el-input-number v-model="form.params.k_period" :min="3" :max="20" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="K平滑"><el-input-number v-model="form.params.k_smooth" :min="1" :max="10" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="D平滑"><el-input-number v-model="form.params.d_smooth" :min="1" :max="10" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="超卖"><el-input-number v-model="form.params.oversold" :min="10" :max="40" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="超买"><el-input-number v-model="form.params.overbought" :min="60" :max="90" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'ribbon_macd'">
            <el-col :span="4"><el-form-item label="MA1"><el-input-number v-model="form.params.period1" :min="3" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MA2"><el-input-number v-model="form.params.period2" :min="5" :max="50" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MA3"><el-input-number v-model="form.params.period3" :min="10" :max="80" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MA4"><el-input-number v-model="form.params.period4" :min="20" :max="120" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MACD快"><el-input-number v-model="form.params.macd_fast" :min="3" :max="20" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="MACD慢"><el-input-number v-model="form.params.macd_slow" :min="10" :max="40" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="4"><el-form-item label="信号线"><el-input-number v-model="form.params.macd_signal" :min="3" :max="15" style="width:100%;" /></el-form-item></el-col>
          </template>
          <template v-if="form.strategy_type === 'vol_break'">
            <el-col :span="5"><el-form-item label="回望周期"><el-input-number v-model="form.params.lookback" :min="5" :max="60" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="量均周期"><el-input-number v-model="form.params.vol_ma_period" :min="5" :max="30" style="width:100%;" /></el-form-item></el-col>
            <el-col :span="5"><el-form-item label="量比"><el-input-number v-model="form.params.vol_ratio" :min="1" :max="5" :step="0.1" :precision="1" style="width:100%;" /></el-form-item></el-col>
          </template>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="runBacktest" :loading="running">
            <el-icon><VideoPlay /></el-icon> 开始回测
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 回测结果 -->
    <template v-if="backtestResult">
      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="8">
          <el-card shadow="hover" class="panel-card">
            <template #header>
              <div class="panel-header">
                <span class="panel-title">绩效指标</span>
              </div>
            </template>
            <div class="metrics-list">
              <div class="metric-item">
                <span class="metric-label">总收益率</span>
                <span class="metric-value" :style="{ color: backtestResult.total_return >= 0 ? '#f53f3f' : '#00b42a' }">
                  {{ backtestResult.total_return >= 0 ? '+' : '' }}{{ backtestResult.total_return }}%
                </span>
              </div>
              <div class="metric-item">
                <span class="metric-label">最终权益</span>
                <span class="metric-value">{{ backtestResult.final_capital?.toFixed(2) }} USDT</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">最大回撤</span>
                <span class="metric-value" style="color:#f53f3f">-{{ backtestResult.max_drawdown }}%</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">夏普比率</span>
                <span class="metric-value">{{ backtestResult.sharpe_ratio }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">胜率</span>
                <span class="metric-value" :style="{ color: backtestResult.win_rate >= 50 ? '#f53f3f' : '#00b42a' }">
                  {{ backtestResult.win_rate }}%
                </span>
              </div>
              <div class="metric-item">
                <span class="metric-label">交易次数</span>
                <span class="metric-value">{{ backtestResult.trade_count }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">盈利/亏损</span>
                <span class="metric-value">
                  <span style="color:#f53f3f">{{ backtestResult.win_count }}</span> / <span style="color:#00b42a">{{ backtestResult.lose_count }}</span>
                </span>
              </div>
              <div v-if="backtestResult.profit_factor" class="metric-item">
                <span class="metric-label">盈亏比</span>
                <span class="metric-value">{{ backtestResult.profit_factor }}</span>
              </div>
              <div v-if="backtestResult.total_fees" class="metric-item">
                <span class="metric-label">累计手续费</span>
                <span class="metric-value" style="color:#86909c">{{ backtestResult.total_fees?.toFixed(2) }} USDT</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">杠杆</span>
                <span class="metric-value">{{ backtestResult.leverage }}x</span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card shadow="hover" class="panel-card">
            <template #header>
              <div class="panel-header">
                <span class="panel-title">资金曲线</span>
              </div>
            </template>
            <div ref="equityChart" style="height: 360px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 交易明细 -->
      <el-card shadow="hover" class="panel-card" style="margin-top: 20px;">
        <template #header>
          <div class="panel-header">
            <span class="panel-title">交易明细（{{ backtestTrades.length }} 笔）</span>
          </div>
        </template>
        <el-table :data="backtestTrades" stripe style="width: 100%" max-height="400">
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.time) }}</template>
          </el-table-column>
          <el-table-column label="方向" width="100">
            <template #default="{ row }">
              <el-tag :type="row.side.includes('long') ? 'danger' : 'success'" size="small">
                {{ sideLabel(row.side) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="价格" align="right">
            <template #default="{ row }">{{ row.price?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="sz" label="张数" align="right" width="80">
            <template #default="{ row }">{{ row.sz || '--' }}</template>
          </el-table-column>
          <el-table-column label="保证金" align="right">
            <template #default="{ row }">{{ row.margin?.toFixed(2) || '--' }}</template>
          </el-table-column>
          <el-table-column label="盈亏" align="right">
            <template #default="{ row }">
              <span v-if="row.pnl !== undefined" :style="{ color: row.pnl >= 0 ? '#f53f3f' : '#00b42a', fontWeight: 600 }">
                {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl.toFixed(4) }}
              </span>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column label="手续费" align="right" width="90">
            <template #default="{ row }">
              <span v-if="row.fee" style="color:#86909c">{{ row.fee?.toFixed(4) }}</span>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="平仓原因" width="100" />
        </el-table>
      </el-card>
    </template>

    <!-- 历史回测记录 -->
    <el-card shadow="hover" class="panel-card" style="margin-top: 20px;">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">历史回测记录</span>
          <el-button text size="small" type="primary" @click="loadHistory">刷新</el-button>
        </div>
      </template>
      <el-table :data="historyResults" stripe empty-text="暂无回测记录" style="width: 100%">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="strategy_display_name" label="策略" width="120" />
        <el-table-column prop="symbol" label="交易对" width="140" />
        <el-table-column prop="timeframe" label="周期" width="70" />
        <el-table-column label="总收益率" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.total_return >= 0 ? '#f53f3f' : '#00b42a', fontWeight: 600 }">
              {{ row.total_return >= 0 ? '+' : '' }}{{ row.total_return }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最大回撤" align="right">
          <template #default="{ row }">
            <span style="color:#f53f3f">-{{ row.max_drawdown }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="sharpe_ratio" label="夏普" align="right" />
        <el-table-column label="胜率" align="right">
          <template #default="{ row }">{{ row.win_rate }}%</template>
        </el-table-column>
        <el-table-column prop="trade_count" label="交易数" align="right" width="80" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="danger" size="small" text @click="deleteResult(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import api from '../utils/api'

const availableStrategies = ref([])
const running = ref(false)
const backtestResult = ref(null)
const backtestTrades = ref([])
const historyResults = ref([])
const equityChart = ref(null)
let chartInstance = null

const form = reactive({
  strategy_type: 'ma_cross',
  symbol: 'BTC-USDT-SWAP',
  timeframe: '1h',
  initial_capital: 10000,
  leverage: 10,
  fee_rate: 0.05,      // taker 0.05%
  slippage: 0.05,      // 0.05%
  params: {
    fast_period: 7,
    slow_period: 25,
    period: 14,
    oversold: 30,
    overbought: 70,
    std_dev: 2.0,
    size_mode: 'fixed',
    size: 1,
    size_pct: 10,
    take_profit_pct: 0,
    stop_loss_pct: 5,
    trailing_stop_pct: 0,
    timeframe: '1h',
  },
})

// 加载可用策略类型
async function loadAvailable() {
  try {
    const res = await api.get('/strategy/available')
    availableStrategies.value = res.strategies || []
  } catch { /* ignore */ }
}

// 加载历史回测记录
async function loadHistory() {
  try {
    const res = await api.get('/backtest/results')
    historyResults.value = res.results || []
  } catch { /* ignore */ }
}

// 运行回测
async function runBacktest() {
  running.value = true
  backtestResult.value = null
  backtestTrades.value = []
  try {
    // 发送请求，手续费/滑点从前端百分比转为后端小数
    const payload = {
      ...form,
      fee_rate: form.fee_rate / 100,       // 0.05% → 0.0005
      slippage: form.slippage / 100,       // 0.05% → 0.0005
    }
    const res = await api.post('/backtest/run', payload)
    if (res.ok) {
      backtestResult.value = res
      backtestTrades.value = res.trades || []
      ElMessage.success('回测完成')
      loadHistory()
      // 渲染资金曲线
      await nextTick()
      renderEquityCurve(res.equity_curve || [], res.trades || [])
    } else {
      ElMessage.error(res.msg || '回测失败')
    }
  } catch (e) {
    ElMessage.error('回测失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    running.value = false
  }
}

// 渲染资金曲线
function renderEquityCurve(curve, trades) {
  if (!equityChart.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(equityChart.value)

  const times = curve.map(p => new Date(p.time).toLocaleString('zh-CN'))
  const values = curve.map(p => p.equity)

  // 标注买卖点
  const buyPoints = []
  const sellPoints = []
  trades.forEach(t => {
    const idx = curve.findIndex(p => p.time === t.time)
    if (idx >= 0) {
      if (t.side.includes('open_long')) {
        buyPoints.push({ coord: [idx, values[idx]], value: '开多' })
      } else if (t.side.includes('open_short')) {
        sellPoints.push({ coord: [idx, values[idx]], value: '开空' })
      } else if (t.side.includes('close')) {
        sellPoints.push({ coord: [idx, values[idx]], value: '平仓' })
      }
    }
  })

  chartInstance.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}<br/>权益: {c} USDT' },
    grid: { top: 30, right: 30, bottom: 30, left: 80 },
    xAxis: { type: 'category', data: times, axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}' }, scale: true },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { color: '#f7931a', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(247,147,26,0.3)' },
          { offset: 1, color: 'rgba(247,147,26,0.02)' },
        ]),
      },
      markPoint: {
        data: [...buyPoints, ...sellPoints],
        symbol: 'pin',
        symbolSize: 30,
        label: { fontSize: 9 },
        itemStyle: { color: '#f7931a' },
      },
    }],
  })
  window.addEventListener('resize', () => chartInstance?.resize())
}

// 删除回测记录
async function deleteResult(id) {
  try {
    await ElMessageBox.confirm('确定删除此回测记录？', '确认', { type: 'warning' })
    await api.delete(`/backtest/result/${id}`)
    ElMessage.success('已删除')
    loadHistory()
  } catch { /* cancel */ }
}

function sideLabel(side) {
  const map = {
    open_long: '开多', open_short: '开空',
    close_long: '平多', close_short: '平空',
  }
  return map[side] || side
}

function formatTime(ts) {
  if (!ts) return '--'
  const d = new Date(Number(ts))
  if (isNaN(d.getTime())) return ts
  return d.toLocaleString('zh-CN')
}

onMounted(() => {
  loadAvailable()
  loadHistory()
})

// 监听策略类型变化，更新参数默认值
watch(() => form.strategy_type, (type) => {
  const found = availableStrategies.value.find(s => s.type === type)
  if (found) {
    Object.assign(form.params, found.default_params)
    form.params.take_profit_pct = 0
    form.params.stop_loss_pct = 5
    form.params.trailing_stop_pct = 0
    form.params.size_mode = 'fixed'
    form.params.size = 1
    form.params.size_pct = 10
  }
})
</script>

<style scoped>
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

.backtest-form {
  padding: 4px 0;
}

/* 指标列表 */
.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px 0;
}

.metric-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid #f2f3f5;
}

.metric-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.metric-label {
  font-size: 13px;
  color: #86909c;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
</style>
