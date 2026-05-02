<template>
  <div class="strategy-page">
    <!-- 操作栏 -->
    <div class="page-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">策略管理</span>
        <el-tag effect="plain" size="small" round>{{ strategies.length }} 个策略</el-tag>
      </div>
      <div class="toolbar-right" v-if="isAdmin">
        <el-button type="primary" size="small" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建策略
        </el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="strategies.length === 0 && !loading" class="empty-state">
      <div class="empty-icon-wrap">
        <el-icon :size="48" color="#c9cdd4"><Operation /></el-icon>
      </div>
      <p class="empty-title">暂无策略</p>
      <p class="empty-desc">管理员尚未创建任何策略</p>
    </div>

    <!-- 策略卡片列表 -->
    <div v-else class="strategy-grid">
      <div v-for="s in strategies" :key="s.id" class="strategy-card" @click="openDetailDialog(s)">
        <!-- 下架警告 -->
        <div v-if="s.unpublished_warning" class="card-warning">
          <el-icon :size="14"><WarningFilled /></el-icon>
          <span>{{ s.unpublished_warning }}</span>
        </div>

        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="header-left">
            <div class="strategy-name-row">
              <span class="strategy-name">{{ s.name }}</span>
              <span v-if="s.position && s.position !== 'none'" class="badge" :class="s.position === 'long' ? 'badge-long' : 'badge-short'">
                {{ s.position === 'long' ? '持多' : '持空' }}
              </span>
              <span class="badge" :class="s.running ? 'badge-running' : 'badge-stopped'">
                {{ s.running ? '运行中' : '已停止' }}
              </span>
            </div>
            <div class="strategy-info-row">
              <span class="info-item">{{ formatInstId(s.params.inst_id) }}</span>
              <span class="info-sep">·</span>
              <span class="info-item" v-for="tf in (s.params.timeframes || ['1h'])" :key="tf">{{ formatTimeframeShort(tf) }}</span>
              <span class="info-sep">·</span>
              <span class="info-item leverage">{{ s.params.leverage || 10 }}x</span>
            </div>
          </div>
          <div class="header-type">
            <span class="type-tag">{{ s.type_name }}</span>
          </div>
        </div>

        <!-- 卡片指标区 -->
        <div class="card-body">
          <div class="metrics-row">
            <div class="metric-item">
              <div class="metric-label">交易对</div>
              <div class="metric-value">{{ formatInstId(s.params.inst_id) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">下单</div>
              <div class="metric-value">{{ formatSizeInfo(s.params) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">杠杆</div>
              <div class="metric-value" :class="getLeverageClass(s.params.leverage)">{{ s.params.leverage || 10 }}x</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">运行周期</div>
              <div class="metric-value">
                <span v-for="tf in (s.params.timeframes || ['1h'])" :key="tf" class="tf-tag">{{ formatTimeframeShort(tf) }}</span>
              </div>
            </div>
          </div>

          <!-- 止盈止损 -->
          <div class="tp-sl-row">
            <div class="tp-sl-item tp">
              <span class="tp-sl-label">止盈</span>
              <span class="tp-sl-value">{{ s.params.take_profit_pct || 0 }}%</span>
            </div>
            <div class="tp-sl-item sl">
              <span class="tp-sl-label">止损</span>
              <span class="tp-sl-value">{{ s.params.stop_loss_pct || 0 }}%</span>
            </div>
            <div v-if="s.params.trailing_stop_pct > 0" class="tp-sl-item trail">
              <span class="tp-sl-label">移动止损</span>
              <span class="tp-sl-value">{{ s.params.trailing_stop_pct }}%</span>
            </div>
          </div>

          <!-- 实时信号 -->
          <div v-if="s.running && strategyStatus[s.id]" class="signal-section">
            <div class="signal-row">
              <span class="signal-label">当前信号</span>
              <span class="signal-value" :class="{
                'signal-long': strategyStatus[s.id].signal === 'open_long',
                'signal-short': strategyStatus[s.id].signal === 'open_short',
                'signal-close': strategyStatus[s.id].signal?.startsWith('close'),
                'signal-hold': strategyStatus[s.id].signal === 'hold',
              }">{{ getStrategySignal(s.id) }}</span>
            </div>
            <div v-if="strategyStatus[s.id]?.kline_close" class="signal-row">
              <span class="signal-label">最新价</span>
              <span class="signal-price">${{ strategyStatus[s.id].kline_close?.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <!-- 卡片底部操作 -->
        <div class="card-footer">
          <div class="footer-info">
            <span class="footer-desc">{{ s.params.description || s.type_name }}</span>
          </div>
          <div class="footer-actions">
            <el-button size="small" text @click.stop="openSettingsDialog(s)">
              <el-icon><Setting /></el-icon> 设置
            </el-button>
            <el-button
              v-if="!s.running"
              type="success"
              size="small"
              @click.stop="startStrategy(s.id)"
              :loading="s._starting"
            >
              <el-icon><VideoPlay /></el-icon> 启动
            </el-button>
            <el-button
              v-else
              type="danger"
              size="small"
              @click.stop="stopStrategy(s.id)"
              :loading="s._stopping"
            >
              <el-icon><VideoPause /></el-icon> 停止
            </el-button>
            <el-button size="small" text @click.stop="viewTrades(s)">
              <el-icon><List /></el-icon> 记录
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建策略弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建策略" width="620px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="110px" class="create-form">
        <el-form-item label="策略名称">
          <el-input v-model="createForm.name" placeholder="如：BTC双均线策略" />
        </el-form-item>
        <el-form-item label="策略类型">
          <el-select v-model="createForm.type" style="width: 100%;" @change="onStrategyTypeChange">
            <el-option
              v-for="s in availableStrategies"
              :key="s.type"
              :label="s.name + ' - ' + s.desc"
              :value="s.type"
            />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">交易参数</el-divider>
        <el-form-item label="交易币种">
          <el-select v-model="createForm.inst_id" style="width: 100%;">
            <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
            <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
            <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
          </el-select>
        </el-form-item>
        <el-form-item label="下单方式">
          <el-radio-group v-model="createForm.size_mode">
            <el-radio value="fixed">固定张数</el-radio>
            <el-radio value="percent">仓位百分比</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="createForm.size_mode === 'fixed'" label="下单张数">
          <el-input-number v-model="createForm.size" :min="0.01" :max="1000" :step="0.01" :precision="2" />
          <span class="hint-label">合约张数（最小0.01）</span>
        </el-form-item>
        <el-form-item v-else label="仓位比例">
          <el-input-number v-model="createForm.size_pct" :min="1" :max="100" :step="5" />
          <span class="hint-label">% 可用资金</span>
        </el-form-item>
        <el-form-item label="杠杆倍数">
          <el-slider v-model="createForm.leverage" :min="1" :max="125" :step="1" show-input />
        </el-form-item>
        <el-form-item label="保证金模式">
          <el-radio-group v-model="createForm.td_mode">
            <el-radio value="cross">全仓</el-radio>
            <el-radio value="isolated">逐仓</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="市场状态过滤">
          <el-switch v-model="createForm.use_regime_filter" active-text="震荡市不开仓" inactive-text="不过滤" />
          <span class="hint-label">开启后震荡市自动过滤开仓信号</span>
        </el-form-item>
        <el-form-item label="运行周期">
          <el-checkbox-group v-model="createForm.timeframes">
            <div style="display: flex; flex-wrap: wrap; gap: 8px 24px;">
              <el-checkbox value="5m">5分钟</el-checkbox>
              <el-checkbox value="10m">10分钟</el-checkbox>
              <el-checkbox value="15m">15分钟</el-checkbox>
              <el-checkbox value="30m">30分钟</el-checkbox>
              <el-checkbox value="1h">1小时</el-checkbox>
              <el-checkbox value="4h">4小时</el-checkbox>
            </div>
          </el-checkbox-group>
          <span class="hint-label">可多选，每个周期独立运行</span>
        </el-form-item>

        <el-divider content-position="left">风控参数</el-divider>
        <el-form-item label="固定止盈(%)">
          <el-input-number v-model="createForm.take_profit_pct" :min="0" :max="100" :step="0.5" :precision="1" />
          <span class="hint-label">0 = 不限</span>
        </el-form-item>
        <el-form-item label="固定止损(%)">
          <el-input-number v-model="createForm.stop_loss_pct" :min="0" :max="50" :step="0.5" :precision="1" />
          <span class="hint-label">0 = 不限</span>
        </el-form-item>
        <el-form-item label="移动止损(%)">
          <el-input-number v-model="createForm.trailing_stop_pct" :min="0" :max="20" :step="0.5" :precision="1" />
          <span class="hint-label">回调比例，0 = 不启用</span>
        </el-form-item>

        <el-divider content-position="left">策略参数</el-divider>
        <template v-if="createForm.type === 'ma_cross'">
          <el-form-item label="短均线周期">
            <el-input-number v-model="createForm.params.fast_period" :min="2" :max="100" />
          </el-form-item>
          <el-form-item label="长均线周期">
            <el-input-number v-model="createForm.params.slow_period" :min="5" :max="200" />
          </el-form-item>
        </template>
        <template v-if="createForm.type === 'rsi'">
          <el-form-item label="RSI周期">
            <el-input-number v-model="createForm.params.period" :min="2" :max="100" />
          </el-form-item>
          <el-form-item label="超卖线">
            <el-input-number v-model="createForm.params.oversold" :min="10" :max="40" />
          </el-form-item>
          <el-form-item label="超买线">
            <el-input-number v-model="createForm.params.overbought" :min="60" :max="90" />
          </el-form-item>
        </template>
        <template v-if="createForm.type === 'bollinger'">
          <el-form-item label="布林带周期">
            <el-input-number v-model="createForm.params.period" :min="5" :max="100" />
          </el-form-item>
          <el-form-item label="标准差倍数">
            <el-input-number v-model="createForm.params.std_dev" :min="1" :max="4" :step="0.1" :precision="1" />
          </el-form-item>
        </template>
        <template v-if="createForm.type === 'trend_break'">
          <el-form-item label="趋势EMA周期"><el-input-number v-model="createForm.params.ema_period" :min="5" :max="60" /></el-form-item>
          <el-form-item label="布林带周期"><el-input-number v-model="createForm.params.boll_period" :min="5" :max="30" /></el-form-item>
          <el-form-item label="布林标准差"><el-input-number v-model="createForm.params.boll_std" :min="0.5" :max="4" :step="0.1" :precision="1" /></el-form-item>
          <el-form-item label="量均周期"><el-input-number v-model="createForm.params.vol_ma_period" :min="5" :max="30" /></el-form-item>
          <el-form-item label="量比阈值"><el-input-number v-model="createForm.params.vol_ratio" :min="0.5" :max="3" :step="0.1" :precision="1" /></el-form-item>
        </template>
        <template v-if="createForm.type === 'rsi_macd'">
          <el-form-item label="RSI周期"><el-input-number v-model="createForm.params.rsi_period" :min="2" :max="30" /></el-form-item>
          <el-form-item label="超卖线"><el-input-number v-model="createForm.params.oversold" :min="10" :max="40" /></el-form-item>
          <el-form-item label="超买线"><el-input-number v-model="createForm.params.overbought" :min="60" :max="90" /></el-form-item>
          <el-form-item label="MACD快线"><el-input-number v-model="createForm.params.macd_fast" :min="3" :max="20" /></el-form-item>
          <el-form-item label="MACD慢线"><el-input-number v-model="createForm.params.macd_slow" :min="10" :max="40" /></el-form-item>
          <el-form-item label="MACD信号线"><el-input-number v-model="createForm.params.macd_signal" :min="3" :max="15" /></el-form-item>
        </template>
        <template v-if="createForm.type === 'st_kdj'">
          <el-form-item label="ATR周期"><el-input-number v-model="createForm.params.atr_period" :min="3" :max="20" /></el-form-item>
          <el-form-item label="ATR倍数"><el-input-number v-model="createForm.params.multiplier" :min="1" :max="6" :step="0.5" :precision="1" /></el-form-item>
          <el-form-item label="K周期"><el-input-number v-model="createForm.params.k_period" :min="3" :max="20" /></el-form-item>
          <el-form-item label="K平滑"><el-input-number v-model="createForm.params.k_smooth" :min="1" :max="10" /></el-form-item>
          <el-form-item label="D平滑"><el-input-number v-model="createForm.params.d_smooth" :min="1" :max="10" /></el-form-item>
          <el-form-item label="超卖线"><el-input-number v-model="createForm.params.oversold" :min="10" :max="40" /></el-form-item>
          <el-form-item label="超买线"><el-input-number v-model="createForm.params.overbought" :min="60" :max="90" /></el-form-item>
        </template>
        <template v-if="createForm.type === 'ribbon_macd'">
          <el-form-item label="MA1"><el-input-number v-model="createForm.params.period1" :min="3" :max="30" /></el-form-item>
          <el-form-item label="MA2"><el-input-number v-model="createForm.params.period2" :min="5" :max="50" /></el-form-item>
          <el-form-item label="MA3"><el-input-number v-model="createForm.params.period3" :min="10" :max="80" /></el-form-item>
          <el-form-item label="MA4"><el-input-number v-model="createForm.params.period4" :min="20" :max="120" /></el-form-item>
          <el-form-item label="MACD快线"><el-input-number v-model="createForm.params.macd_fast" :min="3" :max="20" /></el-form-item>
          <el-form-item label="MACD慢线"><el-input-number v-model="createForm.params.macd_slow" :min="10" :max="40" /></el-form-item>
          <el-form-item label="MACD信号线"><el-input-number v-model="createForm.params.macd_signal" :min="3" :max="15" /></el-form-item>
        </template>
        <template v-if="createForm.type === 'vol_break'">
          <el-form-item label="回望周期"><el-input-number v-model="createForm.params.lookback" :min="5" :max="60" /></el-form-item>
          <el-form-item label="量均周期"><el-input-number v-model="createForm.params.vol_ma_period" :min="5" :max="30" /></el-form-item>
          <el-form-item label="量比阈值"><el-input-number v-model="createForm.params.vol_ratio" :min="1" :max="5" :step="0.1" :precision="1" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createStrategy" :loading="creating">创建策略</el-button>
      </template>
    </el-dialog>

    <!-- 设置/编辑策略弹窗 -->
    <el-dialog v-model="showSettingsDialog" :title="editForm.name + ' - 策略设置'" width="720px" :close-on-click-modal="false">
      <!-- 简易版/专业版切换 -->
      <template #header>
        <div class="settings-header">
          <span>{{ editForm.name }} - 策略设置</span>
          <div class="mode-switch">
            <el-button :type="settingsMode === 'simple' ? 'primary' : 'default'" size="small" @click="settingsMode = 'simple'">简易版</el-button>
            <el-button :type="settingsMode === 'pro' ? 'primary' : 'default'" size="small" @click="settingsMode = 'pro'">专业版</el-button>
          </div>
        </div>
      </template>

      <!-- 简易版 -->
      <div v-if="settingsMode === 'simple'" class="simple-settings">
        <el-form :model="editForm" label-width="100px" class="create-form">
          <el-form-item label="开仓平台">
            <el-select v-model="editForm.platform" style="width: 100%;" disabled>
              <el-option label="OKX" value="okx" />
            </el-select>
            <span class="hint-label">当前仅支持 OKX</span>
          </el-form-item>
          <el-form-item label="交易币种">
            <el-select v-model="editForm.inst_id" style="width: 100%;" :disabled="editFormRunning">
              <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
              <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
              <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
            </el-select>
          </el-form-item>
          <el-form-item label="开仓杠杆">
            <el-slider v-model="editForm.leverage" :min="1" :max="125" :step="1" show-input />
          </el-form-item>
          <el-form-item label="开仓百分比">
            <el-input-number v-model="editForm.size_pct" :min="1" :max="100" :step="5" />
            <span class="hint-label">% 可用资金</span>
          </el-form-item>
        </el-form>
        <div class="simple-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>其他参数使用管理员预设值，如需调整请切换到专业版</span>
        </div>
      </div>

      <!-- 专业版 -->
      <div v-else class="pro-settings">
        <el-tabs v-model="proActiveTab" type="border-card">
          <!-- Tab 1: 策略配置 -->
          <el-tab-pane label="策略配置" name="config">
            <el-form :model="editForm" label-width="100px" class="tab-form">
              <el-form-item label="开仓平台">
                <el-select v-model="editForm.platform" style="width: 100%;" disabled>
                  <el-option label="OKX" value="okx" />
                </el-select>
              </el-form-item>
              <el-form-item label="交易币种">
                <el-select v-model="editForm.inst_id" style="width: 100%;" :disabled="editFormRunning">
                  <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
                  <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
                  <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
                </el-select>
              </el-form-item>
              <el-form-item label="开仓杠杆">
                <el-slider v-model="editForm.leverage" :min="1" :max="125" :step="1" show-input />
              </el-form-item>
              <el-form-item label="开仓模式">
                <el-radio-group v-model="editForm.position_mode">
                  <el-radio value="both">多空双开</el-radio>
                  <el-radio value="long_only">仅开多</el-radio>
                  <el-radio value="short_only">仅开空</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="运行周期">
                <el-checkbox-group v-model="editForm.timeframes">
                  <div style="display: flex; flex-wrap: wrap; gap: 8px 24px;">
                    <el-checkbox value="5m">5分钟</el-checkbox>
                    <el-checkbox value="15m">15分钟</el-checkbox>
                    <el-checkbox value="30m">30分钟</el-checkbox>
                    <el-checkbox value="1h">1小时</el-checkbox>
                    <el-checkbox value="4h">4小时</el-checkbox>
                  </div>
                </el-checkbox-group>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- Tab 2: 仓位控制 -->
          <el-tab-pane label="仓位控制" name="position">
            <el-form :model="editForm" label-width="100px" class="tab-form">
              <el-form-item label="下单方式">
                <el-radio-group v-model="editForm.size_mode">
                  <el-radio value="fixed">按张数下单</el-radio>
                  <el-radio value="percent">按百分比下单</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="editForm.size_mode === 'fixed'" label="下单张数">
                <el-input-number v-model="editForm.size" :min="0.01" :max="1000" :step="0.01" :precision="2" />
                <span class="hint-label">合约张数（最小0.01）</span>
              </el-form-item>
              <el-form-item v-else label="仓位比例">
                <el-input-number v-model="editForm.size_pct" :min="1" :max="100" :step="5" />
                <span class="hint-label">% 可用资金</span>
              </el-form-item>

              <el-divider content-position="left">风控参数</el-divider>
              <el-form-item label="固定止盈">
                <el-input-number v-model="editForm.take_profit_pct" :min="0" :max="100" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不设止盈）</span>
              </el-form-item>
              <el-form-item label="固定止损">
                <el-input-number v-model="editForm.stop_loss_pct" :min="0" :max="50" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不设止损）</span>
              </el-form-item>
              <el-form-item label="移动止盈">
                <el-input-number v-model="editForm.trailing_stop_pct" :min="0" :max="20" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不启用）</span>
              </el-form-item>
              <el-form-item label="移动激活阈值">
                <el-input-number v-model="editForm.trail_activate_pct" :min="0" :max="10" :step="0.1" :precision="2" />
                <span class="hint-label">%（盈利达到此比例激活移动止盈）</span>
              </el-form-item>
              <el-form-item label="回调点数">
                <el-input-number v-model="editForm.trail_callback_points" :min="0" :max="1000" :step="1" />
                <span class="hint-label">点（价格回调此点数触发平仓）</span>
              </el-form-item>
              <el-form-item label="冷却时间">
                <el-input-number v-model="editForm.cooldown_minutes" :min="0" :max="1440" :step="5" />
                <span class="hint-label">分钟（开仓后冷却时间，0=不限制）</span>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- Tab 3: 策略指标参数 -->
          <el-tab-pane label="策略指标参数" name="indicator">
            <el-form :model="editForm" label-width="100px" class="tab-form">
              <template v-if="editForm.type === 'ma_cross'">
                <el-form-item label="短均线周期"><el-input-number v-model="editForm.params.fast_period" :min="2" :max="100" /></el-form-item>
                <el-form-item label="长均线周期"><el-input-number v-model="editForm.params.slow_period" :min="5" :max="200" /></el-form-item>
              </template>
              <template v-if="editForm.type === 'rsi'">
                <el-form-item label="RSI周期"><el-input-number v-model="editForm.params.period" :min="2" :max="100" /></el-form-item>
                <el-form-item label="超卖线"><el-input-number v-model="editForm.params.oversold" :min="10" :max="40" /></el-form-item>
                <el-form-item label="超买线"><el-input-number v-model="editForm.params.overbought" :min="60" :max="90" /></el-form-item>
              </template>
              <template v-if="editForm.type === 'bollinger'">
                <el-form-item label="布林带周期"><el-input-number v-model="editForm.params.period" :min="5" :max="100" /></el-form-item>
                <el-form-item label="标准差倍数"><el-input-number v-model="editForm.params.std_dev" :min="1" :max="4" :step="0.1" :precision="1" /></el-form-item>
              </template>
              <template v-if="editForm.type === 'macd_divergence'">
                <el-form-item label="MACD快线"><el-input-number v-model="editForm.params.macd_fast" :min="3" :max="20" /></el-form-item>
                <el-form-item label="MACD慢线"><el-input-number v-model="editForm.params.macd_slow" :min="10" :max="40" /></el-form-item>
                <el-form-item label="MACD信号线"><el-input-number v-model="editForm.params.macd_signal" :min="3" :max="15" /></el-form-item>
                <el-form-item label="峰值窗口"><el-input-number v-model="editForm.params.peak_window" :min="2" :max="20" /></el-form-item>
              </template>
              <template v-if="editForm.type === 'trend_break'">
                <el-form-item label="趋势EMA周期"><el-input-number v-model="editForm.params.ema_period" :min="5" :max="60" /></el-form-item>
                <el-form-item label="布林带周期"><el-input-number v-model="editForm.params.boll_period" :min="5" :max="30" /></el-form-item>
                <el-form-item label="布林标准差"><el-input-number v-model="editForm.params.boll_std" :min="0.5" :max="4" :step="0.1" :precision="1" /></el-form-item>
                <el-form-item label="量均周期"><el-input-number v-model="editForm.params.vol_ma_period" :min="5" :max="30" /></el-form-item>
                <el-form-item label="量比阈值"><el-input-number v-model="editForm.params.vol_ratio" :min="0.5" :max="3" :step="0.1" :precision="1" /></el-form-item>
              </template>
              <template v-if="editForm.type === 'rsi_macd'">
                <el-form-item label="RSI周期"><el-input-number v-model="editForm.params.rsi_period" :min="2" :max="30" /></el-form-item>
                <el-form-item label="超卖线"><el-input-number v-model="editForm.params.oversold" :min="10" :max="40" /></el-form-item>
                <el-form-item label="超买线"><el-input-number v-model="editForm.params.overbought" :min="60" :max="90" /></el-form-item>
                <el-form-item label="MACD快线"><el-input-number v-model="editForm.params.macd_fast" :min="3" :max="20" /></el-form-item>
                <el-form-item label="MACD慢线"><el-input-number v-model="editForm.params.macd_slow" :min="10" :max="40" /></el-form-item>
                <el-form-item label="MACD信号线"><el-input-number v-model="editForm.params.macd_signal" :min="3" :max="15" /></el-form-item>
              </template>
              <template v-if="editForm.type === 'vol_break'">
                <el-form-item label="回望周期"><el-input-number v-model="editForm.params.lookback" :min="5" :max="60" /></el-form-item>
                <el-form-item label="量均周期"><el-input-number v-model="editForm.params.vol_ma_period" :min="5" :max="30" /></el-form-item>
                <el-form-item label="量比阈值"><el-input-number v-model="editForm.params.vol_ratio" :min="1" :max="5" :step="0.1" :precision="1" /></el-form-item>
              </template>
              <template v-if="!['ma_cross', 'rsi', 'bollinger', 'macd_divergence', 'trend_break', 'rsi_macd', 'vol_break'].includes(editForm.type)">
                <div class="no-params-tip">该策略无额外指标参数</div>
              </template>
            </el-form>
          </el-tab-pane>

          <!-- Tab 4: 运行时间 -->
          <el-tab-pane label="运行时间" name="schedule">
            <el-form label-width="100px" class="tab-form">
              <el-form-item label="运行星期">
                <el-checkbox-group v-model="editForm.run_days">
                  <div style="display: flex; flex-wrap: wrap; gap: 8px 16px;">
                    <el-checkbox :value="1">周一</el-checkbox>
                    <el-checkbox :value="2">周二</el-checkbox>
                    <el-checkbox :value="3">周三</el-checkbox>
                    <el-checkbox :value="4">周四</el-checkbox>
                    <el-checkbox :value="5">周五</el-checkbox>
                    <el-checkbox :value="6">周六</el-checkbox>
                    <el-checkbox :value="0">周日</el-checkbox>
                  </div>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item label="每日时间段">
                <div class="time-range-row">
                  <el-time-select v-model="editForm.run_start_time" placeholder="开始时间" start="00:00" step="00:30" end="23:30" style="width: 120px;" />
                  <span class="time-sep">至</span>
                  <el-time-select v-model="editForm.run_end_time" placeholder="结束时间" start="00:00" step="00:30" end="23:30" style="width: 120px;" />
                </div>
              </el-form-item>
              <div class="schedule-tip">
                <el-icon><InfoFilled /></el-icon>
                <span>策略仅在选定的星期和时间段内运行，默认全天候运行</span>
              </div>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <el-button @click="showSettingsDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSettings" :loading="saving">保存设置</el-button>
      </template>
    </el-dialog>

    <!-- 交易记录弹窗 -->
    <el-dialog v-model="showTradesDialog" :title="tradesStrategyName + ' - 交易记录'" width="700px">
      <el-table :data="tradesList" stripe empty-text="暂无交易记录" style="width: 100%">
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="symbol" label="交易对" width="140" />
        <el-table-column prop="direction" label="方向" width="90">
          <template #default="{ row }">
            <el-tag :type="directionTagType(row.direction)" size="small">
              {{ directionLabel(row.direction) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" align="right">
          <template #default="{ row }">{{ row.price?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="数量" align="right" />
        <el-table-column prop="pnl" label="盈亏" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.pnl > 0 ? '#f53f3f' : row.pnl < 0 ? '#00b42a' : '' }">
              {{ row.pnl ? row.pnl.toFixed(4) : '--' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 策略详情弹窗 -->
    <el-dialog v-model="showDetailDialog" title="策略详情" width="620px" :close-on-click-modal="false">
      <div v-if="detailStrategy" class="detail-content">
        <!-- 策略基本信息 -->
        <div class="detail-header">
          <div class="detail-title-row">
            <span class="detail-name">{{ detailStrategy.name }}</span>
            <span class="detail-type">{{ detailStrategy.type_name }}</span>
          </div>
          <div class="detail-desc">{{ detailStrategy.params?.description || '暂无策略说明' }}</div>
        </div>

        <!-- 回测数据 -->
        <div class="backtest-section">
          <div class="section-title">
            <span>回测数据</span>
            <span v-if="backtestStats?.need_update" class="update-hint">（数据超过3天，建议更新）</span>
          </div>
          
          <div v-if="loadingStats" class="loading-wrap">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          
          <div v-else-if="!backtestStats?.has_data" class="no-data">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ backtestStats?.message || '暂无回测数据' }}</span>
          </div>
          
          <div v-else class="stats-grid">
            <div class="stat-item">
              <div class="stat-label">年化收益率</div>
              <div class="stat-value" :class="backtestStats.annual_return >= 0 ? 'positive' : 'negative'">
                {{ formatPercent(backtestStats.annual_return) }}
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-label">总收益率</div>
              <div class="stat-value" :class="backtestStats.total_return >= 0 ? 'positive' : 'negative'">
                {{ formatPercent(backtestStats.total_return) }}
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-label">胜率</div>
              <div class="stat-value">{{ formatNumber(backtestStats.win_rate) }}%</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">最大回撤</div>
              <div class="stat-value negative">{{ formatNumber(backtestStats.max_drawdown) }}%</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">总交易次数</div>
              <div class="stat-value">{{ backtestStats.trade_count }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">夏普比率</div>
              <div class="stat-value">{{ formatNumber(backtestStats.sharpe_ratio) }}</div>
            </div>
          </div>
          
          <div v-if="backtestStats?.has_data" class="backtest-meta">
            <span>回测周期: {{ backtestStats.timeframe }}</span>
            <span>交易对: {{ backtestStats.symbol }}</span>
            <span>更新时间: {{ formatDate(backtestStats.last_updated) }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, Loading, WarningFilled } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'

const { on: wsOn, off: wsOff } = useWebSocket()

const loading = ref(false)
const strategies = ref([])
const availableStrategies = ref([])
const showCreateDialog = ref(false)
const creating = ref(false)
const showSettingsDialog = ref(false)
const saving = ref(false)
const isAdmin = ref(false)
const editingStrategyId = ref(null)
const editFormRunning = ref(false)
const showTradesDialog = ref(false)
const tradesList = ref([])
const tradesStrategyName = ref('')

// 策略详情弹窗
const showDetailDialog = ref(false)
const detailStrategy = ref(null)
const backtestStats = ref(null)
const loadingStats = ref(false)

// 策略设置模式：simple=简易版, pro=专业版
const settingsMode = ref('simple')
const proActiveTab = ref('config')

// 策略实时状态 (strategy_id → { signal, position, last_update })
const strategyStatus = ref({})

// ─── WebSocket 策略状态推送 ───

function onWsStrategyStatus(data) {
  if (data && data.strategy_id) {
    strategyStatus.value[data.strategy_id] = {
      signal: data.signal,
      position: data.position,
      kline_time: data.kline_time,
      kline_close: data.kline_close,
      last_update: Date.now(),
    }
    
    const s = strategies.value.find(x => x.id === data.strategy_id)
    if (s) {
      if (data.published === false && data.running === false) {
        strategies.value = strategies.value.filter(x => x.id !== data.strategy_id)
        return
      }
      if (data.running !== undefined) s.running = data.running
      if (data.enabled !== undefined) s.enabled = data.enabled
      if (data.published !== undefined) s.published = data.published
      if (data.position !== undefined) s.position = data.position
    }
  }
}

function onWsSignal(data) {
  if (data && (data.signal === 'open_long' || data.signal === 'open_short' ||
      data.signal === 'close_long' || data.signal === 'close_short')) {
    const signalMap = {
      open_long: '开多', open_short: '开空',
      close_long: '平多', close_short: '平空',
    }
    ElMessage({
      type: data.signal.startsWith('close') ? 'warning' : 'success',
      message: `策略信号: ${signalMap[data.signal] || data.signal} - ${data.inst_id}`,
      duration: 5000,
    })
  }
}

function onWsTrade(data) {
  if (data) {
    if (showTradesDialog.value) {
      const sid = data.strategy_id
      if (sid) {
        api.get(`/strategy/${sid}/trades`).then(res => {
          tradesList.value = res.trades || []
        }).catch(() => {})
      }
    }
  }
}

// ─── 格式化辅助 ───

function getStrategySignal(id) {
  const status = strategyStatus.value[id]
  if (!status) return ''
  const signalMap = {
    open_long: '开多', open_short: '开空',
    close_long: '平多', close_short: '平空',
    hold: '持仓观望', none: '等待信号',
  }
  return signalMap[status.signal] || status.signal
}

function formatInstId(instId) {
  if (!instId) return 'BTC-USDT'
  return instId.replace('-SWAP', '')
}

function formatSizeInfo(params) {
  if (params.size_mode === 'percent') {
    return `${params.size_pct ?? 10}% 仓位`
  }
  return `${params.size ?? 1} 张`
}

function formatTimeframes(timeframes) {
  if (!timeframes || timeframes.length === 0) return '1h'
  const labels = {
    '5m': '5分钟', '10m': '10分钟', '15m': '15分钟',
    '30m': '30分钟', '1h': '1小时', '4h': '4小时',
  }
  return timeframes.map(tf => labels[tf] || tf).join(', ')
}

function formatTimeframeShort(tf) {
  const labels = {
    '5m': '5分', '10m': '10分', '15m': '15分',
    '30m': '30分', '1h': '1时', '4h': '4时',
  }
  return labels[tf] || tf
}

function getLeverageClass(leverage) {
  if (leverage >= 100) return 'leverage-high'
  if (leverage >= 50) return 'leverage-mid'
  return 'leverage-low'
}

function directionLabel(dir) {
  const map = {
    open_long: '开多', open_short: '开空',
    close_long: '平多', close_short: '平空',
    buy: '买入', sell: '卖出',
  }
  return map[dir] || dir || '--'
}

function directionTagType(dir) {
  if (!dir) return 'info'
  if (dir.includes('long') || dir === 'buy') return 'danger'
  if (dir.includes('short') || dir === 'sell') return 'success'
  return 'info'
}

// ─── 创建策略表单 ───

const createForm = reactive({
  name: '',
  type: 'ma_cross',
  inst_id: 'BTC-USDT-SWAP',
  size_mode: 'fixed',
  size: 1,
  size_pct: 10,
  leverage: 10,
  take_profit_pct: 5,
  stop_loss_pct: 3,
  trailing_stop_pct: 0,
  td_mode: 'cross',
  use_regime_filter: true,
  timeframes: ['1h'],
  params: {
    fast_period: 7,
    slow_period: 25,
    period: 14,
    oversold: 30,
    overbought: 70,
    std_dev: 2.0,
  },
})

// ─── 编辑策略表单 ───

const editForm = reactive({
  name: '',
  type: '',
  platform: 'okx',
  inst_id: 'BTC-USDT-SWAP',
  size_mode: 'percent',
  size: 1,
  size_pct: 10,
  leverage: 10,
  take_profit_pct: 5,
  stop_loss_pct: 3,
  trailing_stop_pct: 0,
  trail_activate_pct: 0,
  trail_callback_points: 0,
  cooldown_minutes: 0,
  td_mode: 'cross',
  position_mode: 'both', // both=多空双开, long_only=仅开多, short_only=仅开空
  timeframes: ['1h'],
  run_days: [1, 2, 3, 4, 5, 6, 0], // 默认周一到周日都运行
  run_start_time: '00:00',
  run_end_time: '23:59',
  description: '',
  params: {},
})

// ─── 策略操作 ───

async function loadStrategies() {
  loading.value = true
  try {
    const res = await api.get('/strategy/list')
    strategies.value = (res.strategies || []).map(s => ({
      ...s,
      _starting: false,
      _stopping: false,
    }))
    isAdmin.value = res.is_admin || false
  } catch (e) {
    ElMessage.error('加载策略失败')
  } finally {
    loading.value = false
  }
}

async function loadAvailable() {
  try {
    const res = await api.get('/strategy/available')
    availableStrategies.value = res.strategies || []
  } catch { /* ignore */ }
}

function openCreateDialog() {
  createForm.name = ''
  createForm.type = 'ma_cross'
  createForm.inst_id = 'BTC-USDT-SWAP'
  createForm.size_mode = 'fixed'
  createForm.size = 1
  createForm.size_pct = 10
  createForm.leverage = 10
  createForm.take_profit_pct = 5
  createForm.stop_loss_pct = 3
  createForm.trailing_stop_pct = 0
  createForm.td_mode = 'cross'
  createForm.use_regime_filter = true
  createForm.params = { fast_period: 7, slow_period: 25, timeframe: '1h', period: 14, oversold: 30, overbought: 70, std_dev: 2.0 }
  showCreateDialog.value = true
}

function onStrategyTypeChange(type) {
  const found = availableStrategies.value.find(s => s.type === type)
  if (found) {
    createForm.params = { ...found.default_params }
  }
}

function openSettingsDialog(s) {
  editingStrategyId.value = s.id
  editFormRunning.value = s.running
  editForm.name = s.name
  editForm.type = s.type
  editForm.platform = s.params.platform || 'okx'
  editForm.inst_id = s.params.inst_id || 'BTC-USDT-SWAP'
  editForm.size_mode = s.params.size_mode || 'percent'
  editForm.size = s.params.size ?? 1
  editForm.size_pct = s.params.size_pct || 10
  editForm.leverage = s.params.leverage || 10
  editForm.take_profit_pct = s.params.take_profit_pct || 0
  editForm.stop_loss_pct = s.params.stop_loss_pct || 0
  editForm.trailing_stop_pct = s.params.trailing_stop_pct || 0
  editForm.trail_activate_pct = s.params.trail_activate_pct || 0
  editForm.trail_callback_points = s.params.trail_callback_points || 0
  editForm.cooldown_minutes = s.params.cooldown_minutes || 0
  editForm.td_mode = s.params.td_mode || 'cross'
  editForm.position_mode = s.params.position_mode || 'both'
  editForm.timeframes = s.params.timeframes || ['1h']
  editForm.run_days = s.params.run_days || [1, 2, 3, 4, 5, 6, 0]
  editForm.run_start_time = s.params.run_start_time || '00:00'
  editForm.run_end_time = s.params.run_end_time || '23:59'
  editForm.description = s.params.description || ''
  const strategyKeys = {
    ma_cross: ['fast_period', 'slow_period', 'timeframe'],
    rsi: ['period', 'oversold', 'overbought', 'timeframe'],
    bollinger: ['period', 'std_dev', 'timeframe'],
    macd: ['fast_period', 'slow_period', 'signal_period', 'timeframe'],
    macd_divergence: ['macd_fast', 'macd_slow', 'macd_signal', 'peak_window'],
    ema_volume: ['fast_period', 'slow_period', 'volume_ma_period', 'volume_ratio', 'timeframe'],
    supertrend: ['atr_period', 'multiplier', 'timeframe'],
    kdj: ['k_period', 'k_smooth', 'd_smooth', 'oversold', 'overbought', 'timeframe'],
    dual_ema: ['trend_period', 'fast_period', 'slow_period', 'timeframe'],
    ma_ribbon: ['period1', 'period2', 'period3', 'period4', 'timeframe'],
    cci: ['period', 'oversold', 'overbought', 'timeframe'],
    trend_break: ['ema_period', 'boll_period', 'boll_std', 'vol_ma_period', 'vol_ratio', 'timeframe'],
    rsi_macd: ['rsi_period', 'oversold', 'overbought', 'macd_fast', 'macd_slow', 'macd_signal', 'timeframe'],
    st_kdj: ['atr_period', 'multiplier', 'k_period', 'k_smooth', 'd_smooth', 'oversold', 'overbought', 'timeframe'],
    ribbon_macd: ['period1', 'period2', 'period3', 'period4', 'macd_fast', 'macd_slow', 'macd_signal', 'timeframe'],
    vol_break: ['lookback', 'vol_ma_period', 'vol_ratio', 'timeframe'],
  }
  const keys = strategyKeys[s.type] || []
  const paramsCopy = {}
  for (const k of keys) {
    paramsCopy[k] = s.params[k] ?? (availableStrategies.value.find(x => x.type === s.type)?.default_params || {})[k]
  }
  editForm.params = paramsCopy
  // 重置设置模式为简易版
  settingsMode.value = 'simple'
  proActiveTab.value = 'config'
  showSettingsDialog.value = true
}

async function createStrategy() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入策略名称')
    return
  }
  creating.value = true
  try {
    await api.post('/strategy/create', createForm)
    ElMessage.success('策略创建成功')
    showCreateDialog.value = false
    await loadStrategies()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const body = {
      platform: editForm.platform,
      inst_id: editForm.inst_id,
      leverage: editForm.leverage,
      size_mode: editForm.size_mode,
      size: editForm.size,
      size_pct: editForm.size_pct,
      position_mode: editForm.position_mode,
      timeframes: editForm.timeframes,
      run_days: editForm.run_days,
      run_start_time: editForm.run_start_time,
      run_end_time: editForm.run_end_time,
      take_profit_pct: editForm.take_profit_pct,
      stop_loss_pct: editForm.stop_loss_pct,
      trailing_stop_pct: editForm.trailing_stop_pct,
      trail_activate_pct: editForm.trail_activate_pct,
      trail_callback_points: editForm.trail_callback_points,
      cooldown_minutes: editForm.cooldown_minutes,
      td_mode: editForm.td_mode,
      description: editForm.description,
      params: editForm.params,
    }
    await api.put(`/strategy/${editingStrategyId.value}`, body)
    ElMessage.success('设置已保存')
    showSettingsDialog.value = false
    await loadStrategies()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function startStrategy(id) {
  const s = strategies.value.find(x => x.id === id)
  if (s) s._starting = true
  try {
    await api.post(`/strategy/${id}/start`)
    ElMessage.success('策略已启动')
    await loadStrategies()
  } catch (e) {
    ElMessage.error('启动失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    if (s) s._starting = false
  }
}

async function stopStrategy(id) {
  const s = strategies.value.find(x => x.id === id)
  if (!s) return

  if (s.published === false) {
    try {
      await ElMessageBox.confirm(
        '该策略已被下架，停止后将自动消失。确定要停止吗？',
        '提示',
        { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }

  if (s) s._stopping = true
  try {
    const res = await api.post(`/strategy/${id}/stop`)
    if (res.published === false) {
      ElMessage.success('策略已停止，即将从列表中消失')
      strategies.value = strategies.value.filter(x => x.id !== id)
    } else {
      ElMessage.success('策略已停止')
      s.running = false
      s.enabled = false
    }
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    if (detail.includes('not running')) {
      ElMessage.warning('策略已停止')
      if (s.published === false) {
        strategies.value = strategies.value.filter(x => x.id !== id)
      } else {
        s.running = false
        s.enabled = false
      }
    } else {
      ElMessage.error('停止失败: ' + detail)
    }
  } finally {
    if (s) s._stopping = false
  }
}

async function deleteStrategy(id) {
  try {
    await ElMessageBox.confirm('确定要删除此策略吗？', '确认', { type: 'warning' })
    await api.delete(`/strategy/${id}`)
    ElMessage.success('已删除')
    await loadStrategies()
  } catch { /* cancel */ }
}

async function viewTrades(s) {
  tradesStrategyName.value = s.name
  showTradesDialog.value = true
  try {
    const res = await api.get(`/strategy/${s.id}/trades`)
    tradesList.value = res.trades || []
  } catch {
    tradesList.value = []
  }
}

// ─── 策略详情弹窗 ───

async function openDetailDialog(s) {
  detailStrategy.value = s
  showDetailDialog.value = true
  loadingStats.value = true
  backtestStats.value = null
  
  try {
    const res = await api.get(`/backtest/strategy/${s.type}/stats`)
    backtestStats.value = res
  } catch (e) {
    console.error('获取回测数据失败:', e)
    const errMsg = e.response?.data?.detail || e.message || '获取回测数据失败'
    backtestStats.value = { has_data: false, message: errMsg }
  } finally {
    loadingStats.value = false
  }
}

function formatPercent(value) {
  if (value === null || value === undefined) return '--'
  return (value > 0 ? '+' : '') + value.toFixed(2) + '%'
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '--'
  return value.toFixed(decimals)
}

function formatDate(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN')
}

function formatTime(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN')
}

onMounted(() => {
  loadStrategies()
  loadAvailable()
  wsOn('strategy_status', onWsStrategyStatus)
  wsOn('signal', onWsSignal)
  wsOn('trade', onWsTrade)
})

onBeforeUnmount(() => {
  wsOff('strategy_status', onWsStrategyStatus)
  wsOff('signal', onWsSignal)
  wsOff('trade', onWsTrade)
})
</script>

<style scoped>
/* ===== 页面容器（颜色变量继承全局主题） ===== */
.strategy-page {
  min-height: 100%;
}

/* ===== 页面工具栏 ===== */
.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

/* ===== 空状态 ===== */
.empty-state {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon-wrap {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-desc {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

/* ===== 策略卡片网格 ===== */
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

/* ===== 策略卡片（参考 zxlh.pro 三段式） ===== */
.strategy-card {
  background: var(--bg-card);
  border-radius: 12px;
  border: 2px solid var(--border-primary);
  padding: 0;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  will-change: transform;
}

.strategy-card:hover {
  transform: translateY(-2px);
  border-color: var(--card-hover-border);
  box-shadow: var(--card-hover-shadow);
}

/* 下架警告 */
.card-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--orange-light);
  color: var(--orange);
  font-size: 12px;
  font-weight: 500;
}

/* ─── 卡片头部 ─── */
.card-header {
  padding: 14px 16px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.header-left {
  flex: 1;
  min-width: 0;
}

.strategy-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.strategy-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 徽章（参考 zxlh.pro badge 样式） */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}

.badge-long {
  background: var(--red-light);
  color: var(--red);
  border: 1px solid rgba(245, 63, 63, 0.2);
}

.badge-short {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid rgba(0, 180, 42, 0.2);
}

.badge-running {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid rgba(0, 180, 42, 0.2);
}

.badge-stopped {
  background: var(--accent-light);
  color: var(--text-muted);
  border: 1px solid var(--border-secondary);
}

/* 信息行 */
.strategy-info-row {
  display: flex;
  align-items: center;
  gap: 0;
  font-size: 11px;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.info-item {
  white-space: nowrap;
}

.info-item.leverage {
  color: var(--accent);
  font-weight: 600;
}

.info-sep {
  margin: 0 6px;
  color: var(--text-disabled);
}

/* 类型标签 */
.header-type {
  flex-shrink: 0;
}

.type-tag {
  display: inline-block;
  padding: 3px 10px;
  background: var(--accent-light);
  color: var(--accent);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid rgba(247, 147, 26, 0.2);
  white-space: nowrap;
}

/* ─── 卡片主体 ─── */
.card-body {
  padding: 14px 16px;
  flex: 1;
}

/* 指标行 */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.metric-label {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.metric-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.leverage-high { color: var(--red); }
.leverage-mid { color: var(--orange); }
.leverage-low { color: var(--green); }

/* 周期标签 */
.tf-tag {
  display: inline-block;
  padding: 1px 6px;
  background: var(--blue-light);
  color: var(--blue);
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  margin-right: 3px;
}

/* 止盈止损行 */
.tp-sl-row {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle);
}

.tp-sl-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tp-sl-label {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 500;
}

.tp-sl-value {
  font-size: 12px;
  font-weight: 600;
}

.tp-sl-item.tp .tp-sl-value { color: var(--green); }
.tp-sl-item.sl .tp-sl-value { color: var(--red); }
.tp-sl-item.trail .tp-sl-value { color: var(--orange); }

/* 信号区 */
.signal-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle);
  display: flex;
  gap: 16px;
  align-items: center;
}

.signal-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.signal-label {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 500;
}

.signal-value {
  font-size: 13px;
  font-weight: 700;
}

.signal-price {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Roboto Mono', monospace;
}

.signal-long { color: var(--red); }
.signal-short { color: var(--green); }
.signal-close { color: var(--orange); }
.signal-hold { color: var(--text-muted); }

/* ─── 卡片底部 ─── */
.card-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--bg-hover);
}

.footer-info {
  flex: 1;
  min-width: 0;
}

.footer-desc {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 100%;
}

.footer-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

/* ===== 弹窗表单 ===== */
.create-form {
  padding: 10px 20px 0;
}

.hint-label {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ===== 设置对话框 ===== */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.mode-switch {
  display: flex;
  gap: 0;
}

.mode-switch .el-button {
  border-radius: 0;
}

.mode-switch .el-button:first-child {
  border-radius: 4px 0 0 4px;
}

.mode-switch .el-button:last-child {
  border-radius: 0 4px 4px 0;
}

.simple-settings {
  padding: 10px 0;
}

/* 对话框内容区域 */
:deep(.el-dialog__body) {
  padding: 20px;
  overflow: hidden;
}

.simple-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: var(--accent-light);
  border-radius: 8px;
  color: var(--accent);
  font-size: 13px;
  margin-top: 16px;
}

.pro-settings {
  margin: 0 -20px;
  padding: 0;
}

.pro-settings :deep(.el-tabs--border-card) {
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.pro-settings :deep(.el-tabs__header) {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  margin: 0 0 0 0;
  padding: 0 20px;
}

.pro-settings :deep(.el-tabs__nav) {
  border: none;
}

.pro-settings :deep(.el-tabs__item) {
  padding: 0 20px;
  height: 40px;
  line-height: 40px;
}

.pro-settings :deep(.el-tabs__content) {
  padding: 16px 20px;
  max-height: 420px;
  overflow-y: auto;
  background: transparent;
  border: none;
}

.pro-settings :deep(.el-tab-pane) {
  overflow: visible;
}

.tab-form {
  max-width: 100%;
  padding: 0;
}

.tab-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.tab-form :deep(.el-divider) {
  margin: 16px 0;
}

.tab-form :deep(.el-input-number) {
  width: 160px;
}

.tab-form :deep(.el-slider) {
  max-width: 320px;
}

.time-range-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-sep {
  color: var(--text-muted);
  font-size: 13px;
}

.schedule-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: var(--blue-light);
  border-radius: 8px;
  color: var(--blue);
  font-size: 13px;
  margin-top: 12px;
}

.no-params-tip {
  color: var(--text-muted);
  font-size: 13px;
  padding: 20px 0;
  text-align: center;
}

/* ===== 策略详情弹窗 ===== */
.detail-content {
  padding: 0 10px;
}

.detail-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.detail-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.detail-type {
  padding: 3px 10px;
  background: var(--accent-light);
  color: var(--accent);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.detail-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.backtest-section {
  background: var(--bg-secondary);
  border-radius: 10px;
  padding: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.update-hint {
  font-size: 11px;
  color: var(--orange);
  font-weight: 400;
}

.loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 30px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 30px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Roboto Mono', monospace;
}

.stat-value.positive {
  color: var(--green);
}

.stat-value.negative {
  color: var(--red);
}

.backtest-meta {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-subtle);
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: var(--text-muted);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .strategy-grid {
    grid-template-columns: 1fr;
  }
  .page-toolbar {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .tp-sl-row {
    flex-wrap: wrap;
    gap: 8px;
  }
  .signal-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .card-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .footer-actions {
    justify-content: flex-end;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .strategy-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
