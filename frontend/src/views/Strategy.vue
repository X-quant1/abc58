<template>
  <div class="strategy-page">
    <!-- 操作栏 -->
    <div class="page-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">策略管理</span>
      </div>
      <div class="toolbar-right" v-if="isAdmin">
        <el-button type="primary" size="small" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建策略
        </el-button>
      </div>
    </div>

    <!-- 状态筛选标签 -->
    <div class="status-tabs">
      <div class="status-tab status-running" :class="{ active: statusFilter === 'running' }" @click="statusFilter = 'running'">
        <span class="tab-label">运行中</span>
        <span class="tab-count">{{ strategies.filter(s => !s.is_template && s.running).length }}</span>
      </div>
      <div class="status-tab status-official" :class="{ active: statusFilter === '' || statusFilter === 'official' }" @click="statusFilter = ''">
        <span class="tab-label">官方策略</span>
        <span class="tab-count">{{ strategies.filter(s => s.is_template).length }}</span>
      </div>
      <div class="status-tab status-market" :class="{ active: statusFilter === 'market' }" @click="statusFilter = 'market'">
        <span class="tab-label">市场策略</span>
        <span class="tab-count">{{ strategies.filter(s => s.is_template && !s.is_official).length || '-' }}</span>
      </div>
    </div>

    <!-- 运行中标签：分两区显示 -->
    <template v-if="statusFilter === 'running'">
      <!-- 运行中的策略 -->
      <div v-if="runningInstances.length > 0" class="strategy-section">
        <div class="section-title">运行中</div>
        <div class="instance-grid">
          <div v-for="s in runningInstances" :key="s.id" class="inst-card">
            <!-- 左侧状态条 + 标题行 -->
            <div class="inst-header">
              <div class="inst-left-accent accent-running"></div>
              <div class="inst-title">{{ s.name }}</div>
              <div class="inst-status-dot accent-running"></div>
              <div class="inst-status-text running">运行中</div>
            </div>
            <!-- 盈亏 -->
            <div class="inst-profit" :class="getReturnClass(s._perf?.total_pnl)">
              {{ s._perf?.total_pnl || '+100.01' }}<span class="profit-unit"> USDT</span>
            </div>
            <!-- 分隔线 -->
            <div class="inst-divider"></div>
            <!-- 参数行 4列布局 -->
            <div class="inst-meta-row">
              <div class="meta-params-row">
                <div class="meta-param-item">
                  <div class="meta-param-label">平台</div>
                  <div class="meta-param-value">Bitget</div>
                </div>
                <div class="meta-param-item">
                  <div class="meta-param-label">币种</div>
                  <div class="meta-param-value">BTC</div>
                </div>
                <div class="meta-param-item">
                  <div class="meta-param-label">周期</div>
                  <div class="meta-param-value">{{ (s.params.timeframes || ['1h']).map(formatTimeframeShort).join('+') }}</div>
                </div>
                <div class="meta-param-item">
                  <div class="meta-param-label">杠杆</div>
                  <div class="meta-param-value lev">{{ s.params.leverage || 10 }}x</div>
                </div>
              </div>
            </div>
            <!-- 底部 -->
            <div class="inst-footer">
              <div class="inst-time">
                <span v-if="s._last_trade?.time" class="time-text">开仓 {{ s._last_trade.time }}</span>
                <span v-if="s._last_trade?.side" class="trade-dir" :class="s._last_trade.side">{{ s._last_trade.side === 'short' ? '做空' : '做多' }}</span>
                <span v-if="s._run_duration" class="time-text">{{ s._run_duration }}</span>
              </div>
              <div class="inst-actions">
                <el-tooltip content="暂停策略" placement="top">
                  <button class="ibtn ibtn-pause" @click.stop="stopStrategy(s.id)" :disabled="s._stopping"><el-icon><VideoPause /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="编辑策略" placement="top">
                  <button class="ibtn ibtn-edit" @click.stop="openSettingsDialog(s)"><el-icon><Edit /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="日志" placement="top">
                  <button class="ibtn ibtn-info" @click.stop="viewLogs(s)"><el-icon><Document /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="交易记录" placement="top">
                  <button class="ibtn ibtn-purple" @click.stop="viewTrades(s)"><el-icon><DataAnalysis /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <button class="ibtn ibtn-del" @click.stop="deleteInstance(s.id)"><el-icon><Delete /></el-icon></button>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- 已停止的策略 -->
      <div v-if="stoppedInstances.length > 0" class="strategy-section">
        <div class="section-title">已停止</div>
        <div class="instance-grid">
          <div v-for="s in stoppedInstances" :key="s.id" class="inst-card">
            <!-- 左侧状态条 + 标题行 -->
            <div class="inst-header">
              <div class="inst-left-accent accent-stopped"></div>
              <div class="inst-title">{{ s.name }}</div>
              <div class="inst-status-dot accent-stopped"></div>
              <div class="inst-status-text stopped">已暂停</div>
            </div>
            <!-- 盈亏 -->
            <div class="inst-profit" :class="getReturnClass(s._perf?.total_pnl)">
              {{ s._perf?.total_pnl || '+50.00' }}<span class="profit-unit"> USDT</span>
            </div>
            <!-- 分隔线 -->
            <div class="inst-divider"></div>
            <!-- 参数行 4列布局 -->
            <div class="inst-meta-row">
              <div class="meta-params-row">
                <div class="meta-param-item">
                  <div class="meta-param-label">平台</div>
                  <div class="meta-param-value">Bitget</div>
                </div>
                <div class="meta-param-item">
                  <div class="meta-param-label">币种</div>
                  <div class="meta-param-value">BTC</div>
                </div>
                <div class="meta-param-item">
                  <div class="meta-param-label">周期</div>
                  <div class="meta-param-value">{{ (s.params.timeframes || ['1h']).map(formatTimeframeShort).join('+') }}</div>
                </div>
                <div class="meta-param-item">
                  <div class="meta-param-label">杠杆</div>
                  <div class="meta-param-value lev">{{ s.params.leverage || 10 }}x</div>
                </div>
              </div>
            </div>
            <!-- 底部 -->
            <div class="inst-footer">
              <div class="inst-time">
                <span v-if="s._last_trade?.time" class="time-text">开仓 {{ s._last_trade.time }}</span>
                <span v-if="s._last_trade?.side" class="trade-dir" :class="s._last_trade.side">{{ s._last_trade.side === 'short' ? '做空' : '做多' }}</span>
                <span v-if="s._run_duration" class="time-text">{{ s._run_duration }}</span>
              </div>
              <div class="inst-actions">
                <el-tooltip content="启动策略" placement="top">
                  <button class="ibtn ibtn-start" @click.stop="startStrategy(s.id)" :disabled="s._starting"><el-icon><VideoPlay /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="编辑策略" placement="top">
                  <button class="ibtn ibtn-edit" @click.stop="openSettingsDialog(s)"><el-icon><Edit /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="日志" placement="top">
                  <button class="ibtn ibtn-info" @click.stop="viewLogs(s)"><el-icon><Document /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="交易记录" placement="top">
                  <button class="ibtn ibtn-purple" @click.stop="viewTrades(s)"><el-icon><DataAnalysis /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <button class="ibtn ibtn-del" @click.stop="deleteInstance(s.id)"><el-icon><Delete /></el-icon></button>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="runningInstances.length === 0 && stoppedInstances.length === 0" class="empty-state">
        <div class="empty-icon-wrap">
          <el-icon :size="48" color="#c9cdd4"><Operation /></el-icon>
        </div>
        <p class="empty-title">暂无运行中的策略</p>
        <p class="empty-desc">去官方策略挑选一个开始运行吧</p>
        <el-button type="primary" size="small" @click="statusFilter = ''" style="margin-top: 12px;">去官方策略看看</el-button>
      </div>
    </template>

    <!-- 非运行中标签：正常显示 -->
    <template v-else>

    <!-- 空状态 -->
    <div v-if="filteredStrategies.length === 0 && !loading" class="empty-state">
      <div class="empty-icon-wrap">
        <el-icon :size="48" color="#c9cdd4"><Operation /></el-icon>
      </div>
      <p class="empty-title">{{ getEmptyTitle }}</p>
      <p class="empty-desc">{{ getEmptyDesc }}</p>
      <el-button v-if="statusFilter === 'running'" type="primary" size="small" @click="statusFilter = ''" style="margin-top: 12px;">
        去官方策略看看
      </el-button>
    </div>

    <!-- 策略卡片列表 -->
    <div v-else class="strategy-grid">
      <div v-for="s in filteredStrategies" :key="s.id" class="strategy-card" :class="{ 'card-running': s.running }" @click="openDetailDialog(s)">
        <!-- 下架警告 -->
        <div v-if="s.unpublished_warning" class="card-warning">
          <el-icon :size="14"><WarningFilled /></el-icon>
          <span>{{ s.unpublished_warning }}</span>
        </div>

        <!-- 卡片头部 - 策略名称 + K线图 -->
        <div class="card-header" :class="getHeaderClass(s)">
          <div class="header-main">
            <div class="header-left">
              <div class="strategy-name-row">
                <span class="strategy-name">{{ s.name }}</span>
                <span v-if="s.position && s.position !== 'none'" class="pos-badge" :class="s.position === 'long' ? 'pos-long' : 'pos-short'">
                  {{ s.position === 'long' ? '持多' : '持空' }}
                </span>
                <!-- 官方策略不显示运行状态，显示"官方"标签 -->
                <span v-if="statusFilter === ''" class="pos-badge pos-official">官方</span>
                <!-- 运行中/已停止 筛选下显示运行状态 -->
                <span v-else class="status-badge" :class="s.running ? 'status-running' : 'status-stopped'">
                  {{ s.running ? '运行中' : '已停止' }}
                </span>
              </div>
              <div class="strategy-meta">
                <span class="meta-item">{{ formatInstId(s.params.inst_id) }}</span>
                <span class="meta-sep">|</span>
                <span class="meta-item" v-for="tf in (s.params.timeframes || ['1h'])" :key="tf">{{ formatTimeframeShort(tf) }}</span>
                <span class="meta-sep">|</span>
                <span class="meta-item leverage-val">{{ s.params.leverage || 10 }}x</span>
              </div>
            </div>
            <!-- 迷你K线图 -->
            <div class="mini-chart">
              <canvas :ref="el => setChartRef(s.id, el)" class="kline-canvas"></canvas>
            </div>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="card-divider"></div>

        <!-- 绩效指标区 -->
        <div class="card-body">
          <div class="perf-section">
            <!-- 第一行：月收益、胜率、最大回撤 -->
            <div class="perf-row">
              <div class="perf-item">
                <div class="perf-label">月收益</div>
                <div class="perf-value" :class="getReturnClass(s._perf?.monthly_return)">
                  {{ s._perf?.monthly_return || '+10.5%' }}
                </div>
                <div class="perf-sub">年化{{ s._perf?.annual_return || '126%' }}</div>
              </div>
              <div class="perf-divider"></div>
              <div class="perf-item">
                <div class="perf-label">胜率</div>
                <div class="perf-value" :class="getWinRateClass(s._perf?.win_rate)">
                  {{ s._perf?.win_rate || '60%' }}
                </div>
                <div class="perf-sub">{{ s._perf?.win_count || '3' }}/{{ s._perf?.total_count || '5' }}笔</div>
              </div>
              <div class="perf-divider"></div>
              <div class="perf-item">
                <div class="perf-label">最大回撤</div>
                <div class="perf-value" :class="getDrawdownClass(s._perf?.max_drawdown)">
                  {{ s._perf?.max_drawdown || '-10%' }}
                </div>
                <div class="perf-sub">{{ s._perf?.risk_level || '低风险' }}</div>
              </div>
            </div>

            <!-- 第二行：夏普比率、持仓时间、盈亏比 -->
            <div class="perf-row">
              <div class="perf-item">
                <div class="perf-label">夏普比率</div>
                <div class="perf-value" :class="getSharpeClass(s._perf?.sharpe)">
                  {{ s._perf?.sharpe || '1.85' }}
                </div>
              </div>
              <div class="perf-divider"></div>
              <div class="perf-item">
                <div class="perf-label">持仓时间</div>
                <div class="perf-value">{{ s._perf?.hold_time || '0.5h' }}</div>
              </div>
              <div class="perf-divider"></div>
              <div class="perf-item">
                <div class="perf-label">盈亏比</div>
                <div class="perf-value">{{ s._perf?.profit_ratio || '2.3:1' }}</div>
              </div>
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
          <div class="footer-left">
            <span class="strategy-type">{{ s.type_name }}</span>
          </div>
          <div class="footer-actions">
            <el-button size="small" text @click.stop="openSettingsDialog(s)">
              <el-icon><Setting /></el-icon> 设置
            </el-button>
            <!-- 手动交易按钮(仅手动测试策略且运行中) -->
            <template v-if="s.running && isManualTest(s)">
              <el-button
                type="danger"
                size="small"
                @click.stop="manualSignal(s, 'open_long')"
                :loading="s._manual_loading"
              >开多</el-button>
              <el-button
                type="success"
                size="small"
                @click.stop="manualSignal(s, 'open_short')"
                :loading="s._manual_loading"
              >开空</el-button>
              <el-button
                v-if="s.position === 'long'"
                type="warning"
                size="small"
                plain
                @click.stop="manualSignal(s, 'close_long')"
                :loading="s._manual_loading"
              >平多</el-button>
              <el-button
                v-if="s.position === 'short'"
                type="warning"
                size="small"
                plain
                @click.stop="manualSignal(s, 'close_short')"
                :loading="s._manual_loading"
              >平空</el-button>
            </template>
            <!-- 官方策略：始终显示启动按钮 -->
            <el-button
              v-if="statusFilter === ''"
              type="success"
              size="small"
              @click.stop="startFromTemplate(s)"
              :loading="s._starting"
            >
              <el-icon><VideoPlay /></el-icon> 启动
            </el-button>
            <!-- 运行中/已停止：正常显示启动/停止 -->
            <template v-else>
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
                plain
                @click.stop="stopStrategy(s.id)"
                :loading="s._stopping"
              >
                <el-icon><VideoPause /></el-icon> 停止
              </el-button>
            </template>
            <el-button size="small" text @click.stop="viewTrades(s)">
              <el-icon><List /></el-icon> 记录
            </el-button>
          </div>
        </div>
      </div>
    </div>
    </template>

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
            <el-radio value="fixed">固定数量</el-radio>
            <el-radio value="percent">仓位百分比</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="createForm.size_mode === 'fixed'" label="下单数量">
          <el-input-number v-model="createForm.size" :min="0.0001" :max="10" :step="0.0001" :precision="4" />
          <span class="hint-label">BTC 数量（最小 0.0001）</span>
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
              <el-option label="Bitget" value="bitget" />
            </el-select>
            <span class="hint-label">当前仅支持 Bitget</span>
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
                  <el-option label="Bitget" value="bitget" />
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
                  <el-radio value="fixed">按数量下单</el-radio>
                  <el-radio value="percent">按百分比下单</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="editForm.size_mode === 'fixed'" label="下单数量">
                <el-input-number v-model="editForm.size" :min="0.0001" :max="10" :step="0.0001" :precision="4" />
                <span class="hint-label">BTC 数量（最小 0.0001）</span>
              </el-form-item>
              <el-form-item v-else label="仓位比例">
                <el-input-number v-model="editForm.size_pct" :min="1" :max="100" :step="5" />
                <span class="hint-label">% 可用资金</span>
              </el-form-item>

              <el-divider content-position="left">风控参数</el-divider>
              <el-form-item label="固定止盈">
                <el-radio-group v-model="editForm.tp_mode" size="small">
                  <el-radio value="pct">按百分比</el-radio>
                  <el-radio value="points">按点数</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="editForm.tp_mode === 'pct'" label="止盈比例">
                <el-input-number v-model="editForm.take_profit_pct" :min="0" :max="100" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不设止盈）</span>
              </el-form-item>
              <el-form-item v-else label="止盈点数">
                <el-input-number v-model="editForm.take_profit_points" :min="0" :max="10000" :step="10" :precision="0" />
                <span class="hint-label">点（如300点=价格+300）</span>
              </el-form-item>
              <el-form-item label="固定止损">
                <el-radio-group v-model="editForm.sl_mode" size="small">
                  <el-radio value="pct">按百分比</el-radio>
                  <el-radio value="points">按点数</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="editForm.sl_mode === 'pct'" label="止损比例">
                <el-input-number v-model="editForm.stop_loss_pct" :min="0" :max="50" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不设止损）</span>
              </el-form-item>
              <el-form-item v-else label="止损点数">
                <el-input-number v-model="editForm.stop_loss_points" :min="0" :max="10000" :step="10" :precision="0" />
                <span class="hint-label">点（如200点=价格-200）</span>
              </el-form-item>
              <el-form-item label="移动止盈">
                <el-radio-group v-model="editForm.trail_mode" size="small">
                  <el-radio value="pct">按百分比</el-radio>
                  <el-radio value="points">按点数</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="editForm.trail_mode === 'pct'" label="移动止损比例">
                <el-input-number v-model="editForm.trailing_stop_pct" :min="0" :max="20" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不启用）</span>
              </el-form-item>
              <el-form-item v-else label="移动止损点数">
                <el-input-number v-model="editForm.trailing_stop_points" :min="0" :max="10000" :step="10" :precision="0" />
                <span class="hint-label">点（价格回撤此点数触发平仓）</span>
              </el-form-item>
              <el-form-item label="移动激活阈值">
                <el-radio-group v-model="editForm.trail_activate_mode" size="small">
                  <el-radio value="pct">按百分比</el-radio>
                  <el-radio value="points">按点数</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="editForm.trail_activate_mode === 'pct'" label="激活比例">
                <el-input-number v-model="editForm.trail_activate_pct" :min="0" :max="10" :step="0.1" :precision="2" />
                <span class="hint-label">%（盈利达到此比例激活移动止盈）</span>
              </el-form-item>
              <el-form-item v-else label="激活点数">
                <el-input-number v-model="editForm.trail_activate_points" :min="0" :max="10000" :step="10" :precision="0" />
                <span class="hint-label">点（价格涨跌此点数激活移动止盈）</span>
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
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, Loading, WarningFilled, TrendCharts, DataLine, Connection, Odometer, Histogram, ArrowUp, ArrowDown, Remove, VideoPause, VideoPlay, Edit, Document, DataAnalysis, Delete } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'

const { on: wsOn, off: wsOff } = useWebSocket()

const loading = ref(false)
const strategies = ref([])
const statusFilter = ref('running')
const availableStrategies = ref([])
const showCreateDialog = ref(false)
const creating = ref(false)
const showSettingsDialog = ref(false)
const saving = ref(false)
const isAdmin = ref(false)
const editingStrategyId = ref(null)
const editFormRunning = ref(false)
const showTradesDialog = ref(false)

// 筛选后的策略列表
const filteredStrategies = computed(() => {
  if (!statusFilter.value) {
    // 官方策略：只显示模板
    return strategies.value.filter(s => s.is_template)
  }
  if (statusFilter.value === 'running') {
    // 运行中：只显示实例
    return strategies.value.filter(s => !s.is_template && s.running)
  }
  if (statusFilter.value === 'stopped') {
    // 已停止：只显示实例
    return strategies.value.filter(s => !s.is_template && !s.running)
  }
  if (statusFilter.value === 'official') {
    return strategies.value.filter(s => s.is_template && s.is_official)
  }
  if (statusFilter.value === 'market') {
    return strategies.value.filter(s => s.is_template && !s.is_official)
  }
  return strategies.value
})

// 运行中的实例
const runningInstances = computed(() => {
  return strategies.value.filter(s => !s.is_template && s.running)
})

// 已停止的实例
const stoppedInstances = computed(() => {
  return strategies.value.filter(s => !s.is_template && !s.running)
})

const getEmptyTitle = computed(() => {
  if (statusFilter.value === 'running') return '暂无运行中的策略'
  if (statusFilter.value === 'stopped') return '暂无已停止的策略'
  if (statusFilter.value === 'market') return '暂无市场策略'
  return '暂无策略'
})

const getEmptyDesc = computed(() => {
  if (statusFilter.value === 'running') return '去官方策略挑选一个开始运行吧'
  if (statusFilter.value === 'stopped') return '所有策略都在运行中'
  if (statusFilter.value === 'market') return '暂无用户分享的策略'
  if (strategies.value.length === 0) return '管理员尚未创建任何策略'
  return '没有符合条件的策略'
})

const tradesList = ref([])
const tradesStrategyName = ref('')
const tradesStrategyId = ref(null)

// 策略详情弹窗
const showDetailDialog = ref(false)
const detailStrategy = ref(null)
const backtestStats = ref(null)
const loadingStats = ref(false)

// 迷你K线图Canvas引用
const chartRefs = {}

function setChartRef(strategyId, el) {
  if (el) {
    chartRefs[strategyId] = el
  }
}

// 绘制策略净值曲线（面积图）
function drawMiniKline(strategyId) {
  const canvas = chartRefs[strategyId]
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const width = 120
  const height = 36

  // 高清屏幕适配
  canvas.width = width * dpr
  canvas.height = height * dpr
  canvas.style.width = width + 'px'
  canvas.style.height = height + 'px'
  ctx.scale(dpr, dpr)

  // 生成模拟净值数据（30个点）
  const values = []
  let nav = 1.0 // 初始净值
  const trend = Math.random() > 0.4 ? 1 : -1 // 60%概率上涨
  for (let i = 0; i < 30; i++) {
    const change = (Math.random() - 0.45) * 0.03 * trend
    nav = Math.max(0.5, nav * (1 + change)) // 防止净值过低
    values.push(nav)
  }

  // 计算范围
  const minVal = Math.min(...values) * 0.98
  const maxVal = Math.max(...values) * 1.02
  const range = maxVal - minVal || 1

  // 清空画布
  ctx.clearRect(0, 0, width, height)

  // 计算点的位置
  const padding = 4
  const chartWidth = width - padding * 2
  const chartHeight = height - padding * 2
  const points = values.map((v, i) => ({
    x: padding + (i / (values.length - 1)) * chartWidth,
    y: padding + (1 - (v - minVal) / range) * chartHeight
  }))

  // 绘制渐变填充区域
  const isUp = values[values.length - 1] >= values[0]
  const grad = ctx.createLinearGradient(0, 0, 0, height)
  if (isUp) {
    grad.addColorStop(0, 'rgba(34, 197, 94, 0.3)')
    grad.addColorStop(1, 'rgba(34, 197, 94, 0.02)')
  } else {
    grad.addColorStop(0, 'rgba(239, 68, 68, 0.3)')
    grad.addColorStop(1, 'rgba(239, 68, 68, 0.02)')
  }

  // 绘制填充区域
  ctx.beginPath()
  ctx.moveTo(points[0].x, height - padding)
  points.forEach(p => ctx.lineTo(p.x, p.y))
  ctx.lineTo(points[points.length - 1].x, height - padding)
  ctx.closePath()
  ctx.fillStyle = grad
  ctx.fill()

  // 绘制曲线
  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length; i++) {
    // 使用贝塞尔曲线平滑
    const xc = (points[i].x + points[i - 1].x) / 2
    const yc = (points[i].y + points[i - 1].y) / 2
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc)
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y)
  ctx.strokeStyle = isUp ? '#22c55e' : '#ef4444'
  ctx.lineWidth = 1.5
  ctx.stroke()

  // 绘制终点圆点
  const lastPoint = points[points.length - 1]
  ctx.beginPath()
  ctx.arc(lastPoint.x, lastPoint.y, 3, 0, Math.PI * 2)
  ctx.fillStyle = isUp ? '#22c55e' : '#ef4444'
  ctx.fill()
  ctx.strokeStyle = '#fff'
  ctx.lineWidth = 1
  ctx.stroke()
}

// 批量绘制所有策略的K线
function drawAllMiniKlines() {
  // 只绘制当前显示的策略
  filteredStrategies.value.forEach(s => {
    setTimeout(() => drawMiniKline(s.id), 50)
  })
}

// 监听筛选变化，重新绘制净值曲线
watch(statusFilter, () => {
  nextTick(() => {
    setTimeout(() => drawAllMiniKlines(), 100)
  })
})

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

// ─── 手动交易信号 ───

function isManualTest(strategy) {
  return strategy.name?.includes('手动测试') || strategy.name?.includes('手动') || strategy.type === 'manual_test'
}

async function manualSignal(strategy, signal) {
  const signalMap = {
    open_long: '开多', open_short: '开空',
    close_long: '平多', close_short: '平空',
  }
  const label = signalMap[signal] || signal

  try {
    await ElMessageBox.confirm(
      `确认对策略「${strategy.name}」执行${label}操作？`,
      '手动交易确认',
      { confirmButtonText: '确认执行', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户取消
  }

  strategy._manual_loading = true
  try {
    const res = await api.post(`/strategy/${strategy.id}/manual-signal`, { signal })
    if (res.ok) {
      ElMessage.success(`${label}信号已执行`)
      // 刷新策略列表以同步持仓状态
      setTimeout(() => {
        loadStrategies()
        // 如果记录弹窗已打开，刷新交易记录
        if (showTradesDialog.value && tradesStrategyId.value === strategy.id) {
          loadTradesList(strategy)
        }
      }, 1500)
    } else {
      ElMessage.error(res.detail || `${label}执行失败`)
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || `${label}请求失败`)
  } finally {
    strategy._manual_loading = false
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
  return `${params.size ?? 0.0001} BTC`
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

// 格式化止盈止损（支持百分比/点数模式）
function formatTpSl(params, type) {
  if (type === 'tp') {
    const mode = params.tp_mode || 'pct'
    if (mode === 'points') {
      return (params.take_profit_points || 0) + '点'
    }
    return (params.take_profit_pct || 0) + '%'
  } else {
    const mode = params.sl_mode || 'pct'
    if (mode === 'points') {
      return (params.stop_loss_points || 0) + '点'
    }
    return (params.stop_loss_pct || 0) + '%'
  }
}

// 获取策略图标
function getStrategyIcon(type) {
  const iconMap = {
    ma_cross: TrendCharts,
    rsi: Histogram,
    bollinger: DataLine,
    macd: Odometer,
    macd_divergence: Connection,
    vol_break: Histogram,
    ema_volume: TrendCharts,
    supertrend: ArrowUp,
    kdj: Histogram,
    dual_ema: TrendCharts,
    ma_ribbon: DataLine,
  }
  return iconMap[type] || TrendCharts
}

// 获取策略图标样式类
function getStrategyIconClass(type) {
  const trendTypes = ['ma_cross', 'ema_volume', 'dual_ema', 'supertrend']
  const oscillatorTypes = ['rsi', 'kdj']
  const divergenceTypes = ['macd_divergence', 'macd']
  if (trendTypes.includes(type)) return 'icon-trend'
  if (oscillatorTypes.includes(type)) return 'icon-oscillator'
  if (divergenceTypes.includes(type)) return 'icon-divergence'
  return ''
}

// 获取卡片头部样式
function getHeaderClass(s) {
  if (!s.running) return 'header-stopped'
  if (s.position === 'long') return 'header-long'
  if (s.position === 'short') return 'header-short'
  return 'header-running'
}

// 绩效颜色
// 月收益：正→绿，负→红
function getReturnClass(val) {
  if (!val) return 'perf-positive'
  const s = String(val)
  if (s.startsWith('-')) return 'perf-negative'
  return 'perf-positive'
}

// 胜率：>50%→绿，≤50%→黑
function getWinRateClass(val) {
  if (!val) return ''
  const num = parseFloat(String(val).replace('%', ''))
  if (isNaN(num) || num <= 50) return 'perf-neutral'
  return 'perf-positive'
}

// 最大回撤：<10%→黑，≥10%→红
function getDrawdownClass(val) {
  if (!val) return 'perf-neutral'
  const num = parseFloat(String(val).replace('%', '').replace('-', ''))
  if (isNaN(num) || num < 10) return 'perf-neutral'
  return 'perf-negative'
}

// 夏普比率：>2→绿，1-2→橙，<1→红
function getSharpeClass(val) {
  if (!val) return ''
  const num = parseFloat(String(val))
  if (isNaN(num)) return ''
  if (num >= 2) return 'perf-positive'
  if (num >= 1) return 'perf-warning'
  return 'perf-negative'
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
  size: 0.0001,
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
  platform: 'bitget',
  inst_id: 'BTC-USDT-SWAP',
  size_mode: 'percent',
  size: 1,
  size_pct: 10,
  leverage: 10,
  tp_mode: 'pct',
  take_profit_pct: 5,
  take_profit_points: 0,
  sl_mode: 'pct',
  stop_loss_pct: 3,
  stop_loss_points: 0,
  trail_mode: 'pct',
  trailing_stop_pct: 0,
  trailing_stop_points: 0,
  trail_activate_mode: 'pct',
  trail_activate_pct: 0,
  trail_activate_points: 0,
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
    // 加载策略模板
    const res = await api.get('/strategy/list')
    const templates = (res.strategies || []).map(s => ({
      ...s,
      _starting: false,
      _stopping: false,
      is_template: true,
    }))

    // 加载策略实例
    let instances = []
    try {
      const instRes = await api.get('/strategy-instance/list')
      instances = (instRes.instances || []).map(s => ({
        ...s,
        _starting: false,
        _stopping: false,
        is_template: false,
      }))
    } catch { /* 实例API可能还未完全实现 */ }

    // 合并：模板 + 实例
    strategies.value = [...templates, ...instances]
    isAdmin.value = res.is_admin || false

    // 加载完成后绘制K线
    nextTick(() => drawAllMiniKlines())
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
  editForm.platform = 'bitget'  // 强制使用 Bitget，忽略数据库旧值
  editForm.inst_id = s.params.inst_id || 'BTC-USDT-SWAP'
  editForm.size_mode = s.params.size_mode || 'percent'
  editForm.size = s.params.size ?? 0.0001
  editForm.size_pct = s.params.size_pct || 10
  editForm.leverage = s.params.leverage || 10
  editForm.tp_mode = s.params.tp_mode || 'pct'
  editForm.take_profit_pct = s.params.take_profit_pct || 0
  editForm.take_profit_points = s.params.take_profit_points || 0
  editForm.sl_mode = s.params.sl_mode || 'pct'
  editForm.stop_loss_pct = s.params.stop_loss_pct || 0
  editForm.stop_loss_points = s.params.stop_loss_points || 0
  editForm.trail_mode = s.params.trail_mode || 'pct'
  editForm.trailing_stop_pct = s.params.trailing_stop_pct || 0
  editForm.trailing_stop_points = s.params.trailing_stop_points || 0
  editForm.trail_activate_mode = s.params.trail_activate_mode || 'pct'
  editForm.trail_activate_pct = s.params.trail_activate_pct || 0
  editForm.trail_activate_points = s.params.trail_activate_points || 0
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
      tp_mode: editForm.tp_mode,
      take_profit_pct: editForm.take_profit_pct,
      take_profit_points: editForm.take_profit_points,
      sl_mode: editForm.sl_mode,
      stop_loss_pct: editForm.stop_loss_pct,
      stop_loss_points: editForm.stop_loss_points,
      trail_mode: editForm.trail_mode,
      trailing_stop_pct: editForm.trailing_stop_pct,
      trailing_stop_points: editForm.trailing_stop_points,
      trail_activate_mode: editForm.trail_activate_mode,
      trail_activate_pct: editForm.trail_activate_pct,
      trail_activate_points: editForm.trail_activate_points,
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
    const detail = e.response?.data?.detail || e.message
    if (detail.includes('already running')) {
      // 策略已在运行，直接标记为运行中（可能是线程还活着但列表未更新）
      ElMessage.warning('策略已在运行中')
      await loadStrategies()
    } else {
      ElMessage.error('启动失败: ' + detail)
    }
  } finally {
    if (s) s._starting = false
  }
}

// 从模板创建实例并启动
async function startFromTemplate(template) {
  template._starting = true
  try {
    // 创建实例
    const res = await api.post('/strategy-instance/create', {
      strategy_id: template.id,
      name: `${template.name}-实例`,
      params: template.params,
    })
    const instanceId = res.instance_id

    // 启动实例
    await api.post(`/strategy-instance/${instanceId}/start`)
    ElMessage.success('策略实例已启动')
    // 切换到运行中标签
    statusFilter.value = 'running'
    await loadStrategies()
  } catch (e) {
    ElMessage.error('启动失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    template._starting = false
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
  tradesStrategyId.value = s.id
  showTradesDialog.value = true
  await loadTradesList(s)
}

function viewLogs(s) {
  ElMessage.info('日志功能开发中')
}

async function deleteInstance(id) {
  try {
    await ElMessageBox.confirm('确定要删除该策略实例吗？', '确认删除', {
      type: 'warning'
    })
    await api.delete(`/strategy-instance/${id}`)
    ElMessage.success('删除成功')
    await loadStrategies()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

async function loadTradesList(s) {
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
/* ===== 实例卡片（暗色协调风格） ===== */
.instance-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 1400px) {
  .instance-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 1000px) {
  .instance-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .instance-grid { grid-template-columns: 1fr; }
}

.inst-card {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 10px;
  padding: 14px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
  position: relative;
}

.inst-card:hover {
  border-color: rgba(16, 185, 129, 0.4);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}

/* 标题行 */
.inst-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.inst-left-accent {
  width: 3px;
  height: 20px;
  border-radius: 2px;
  flex-shrink: 0;
}

.accent-running { background: var(--green); }
.accent-stopped { background: var(--text-muted); }

.inst-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.inst-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.inst-status-dot.accent-running { background: var(--green); }
.inst-status-dot.accent-stopped { background: var(--text-muted); }

.inst-status-text {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.inst-status-text.running { color: var(--green); }
.inst-status-text.stopped { color: var(--text-muted); }

/* 盈亏 */
.inst-profit {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.5px;
  font-family: 'SF Mono', 'Roboto Mono', monospace;
}

.inst-profit.perf-positive { color: var(--green); }
.inst-profit.perf-negative { color: var(--red); }

.profit-unit {
  font-size: 12px;
  font-weight: 500;
  opacity: 0.6;
  font-family: var(--font-family);
  letter-spacing: 0;
}

/* 分隔线 */
.inst-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 0 -2px;
}

/* 参数区域 - 带背景的盒子 */
.inst-meta-row {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 12px;
}

.meta-params-row {
  display: flex;
  justify-content: space-between;
}

.meta-param-item {
  text-align: center;
  flex: 1;
}

.meta-param-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 3px;
  font-weight: 500;
}

.meta-param-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.meta-param-value.lev {
  color: var(--orange);
}

/* 底部 */
.inst-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.inst-time {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.time-text {
  font-size: 11px;
  color: var(--text-muted);
}

.trade-dir {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
}

.trade-dir.long {
  background: rgba(244, 63, 94, 0.12);
  color: var(--red);
}

.trade-dir.short {
  background: rgba(16, 185, 129, 0.12);
  color: var(--green);
}

/* 图标按钮 */
.inst-actions {
  display: flex;
  gap: 4px;
}

.ibtn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  padding: 0;
}

.ibtn:hover {
  transform: scale(1.12);
  filter: brightness(1.2);
}

.ibtn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  transform: none;
  filter: none;
}

.ibtn .el-icon {
  font-size: 13px;
  color: #fff;
}

.ibtn-start { background: rgba(16, 185, 129, 0.9); }
.ibtn-pause { background: rgba(245, 158, 11, 0.9); }
.ibtn-edit  { background: rgba(80, 80, 80, 0.9); }
.ibtn-info  { background: rgba(59, 130, 246, 0.9); }
.ibtn-purple{ background: rgba(161, 104, 247, 0.9); }
.ibtn-del   { background: rgba(244, 63, 94, 0.85); }

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
  margin-bottom: 16px;
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

/* 状态筛选标签 */
.status-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.strategy-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-left: 4px;
}

.status-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-tab:hover {
  border-color: var(--text-muted);
}

.status-tab.active {
  border-color: var(--accent);
  background: var(--accent-light);
}

.status-tab.status-running.active {
  border-color: var(--green);
  background: var(--green-light);
}

.status-tab.status-stopped.active {
  border-color: var(--text-muted);
  background: rgba(153, 153, 153, 0.1);
}

.status-tab.status-official.active {
  border-color: var(--orange);
  background: var(--orange-light);
}

.status-tab.status-market.active {
  border-color: var(--blue);
  background: var(--blue-light);
}

.tab-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.status-tab.active .tab-label {
  color: var(--text-primary);
  font-weight: 600;
}

.tab-count {
  padding: 2px 8px;
  background: rgba(128, 128, 128, 0.2);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.status-tab.active .tab-count {
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent);
}

.status-tab.status-running.active .tab-count {
  background: rgba(16, 185, 129, 0.2);
  color: var(--green);
}

.status-tab.status-stopped.active .tab-count {
  background: rgba(153, 153, 153, 0.2);
  color: var(--text-muted);
}

.status-tab.status-official.active .tab-count {
  background: rgba(245, 158, 11, 0.2);
  color: var(--orange);
}

.status-tab.status-market.active .tab-count {
  background: rgba(59, 130, 246, 0.2);
  color: var(--blue);
}

/* ===== 空状态 ===== */
.empty-state {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 80px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.empty-icon-wrap {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-muted);
  max-width: 280px;
}

.empty-state .el-button {
  margin-top: 20px;
  padding: 12px 28px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--green) 0%, #059669 100%);
  border: none;
  color: #fff;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
  transition: all 0.2s ease;
}

.empty-state .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
}

/* ===== 策略卡片网格 ===== */
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

@media (max-width: 1600px) {
  .strategy-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 1200px) {
  .strategy-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 800px) {
  .strategy-grid { grid-template-columns: 1fr; }
}

/* ===== 策略卡片 ===== */
.strategy-card {
  background: var(--bg-card);
  border-radius: 10px;
  border: 1px solid var(--border-secondary);
  padding: 0;
  transition: all 0.2s ease;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.strategy-card:hover {
  transform: translateY(-2px);
  border-color: rgba(16, 185, 129, 0.5);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.12);
}

.strategy-card.card-running {
  border-color: rgba(16, 185, 129, 0.4);
}

/* 下架警告 */
.card-warning {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  background: var(--orange-light);
  color: var(--orange);
  font-size: 11px;
  font-weight: 600;
}

/* ─── 卡片头部 ─── */
.card-header {
  padding: 12px 14px 10px;
  position: relative;
}

.card-header.header-running { background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, transparent 100%); }
.card-header.header-long { background: linear-gradient(135deg, rgba(244, 63, 94, 0.08) 0%, transparent 100%); }
.card-header.header-short { background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, transparent 100%); }
.card-header.header-stopped { background: linear-gradient(135deg, rgba(153, 153, 153, 0.05) 0%, transparent 100%); }

.header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.strategy-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-chart {
  flex-shrink: 0;
  width: 120px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
}

.kline-canvas {
  width: 100%;
  height: 100%;
}

.pos-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

.pos-badge.pos-long {
  background: var(--red-light);
  color: var(--red);
}

.pos-badge.pos-short {
  background: var(--green-light);
  color: var(--green);
}

.pos-badge.pos-official {
  background: var(--orange-light);
  color: var(--orange);
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

.status-badge.status-running {
  background: var(--green-light);
  color: var(--green);
}

.status-badge.status-stopped {
  background: rgba(153, 153, 153, 0.15);
  color: var(--text-muted);
}

.strategy-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.meta-item { white-space: nowrap; }
.meta-sep { color: var(--text-disabled); }
.leverage-val { color: var(--accent); font-weight: 600; }

/* 分隔线 */
.card-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-secondary), transparent);
  margin: 0 14px;
}

/* ─── 绩效指标区 ─── */
.card-body {
  padding: 10px 14px;
  flex: 1;
}

.perf-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.perf-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  gap: 0;
  align-items: center;
}

.perf-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  text-align: center;
}

.perf-divider {
  width: 1px;
  height: 32px;
  background: var(--border-secondary);
  flex-shrink: 0;
}

.perf-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.perf-value {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}

.perf-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.perf-positive { color: var(--green); }
.perf-negative { color: var(--red); }
.perf-warning { color: var(--orange); }
.perf-neutral { color: var(--text-primary); }

/* 信号区 */
.signal-section {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-subtle);
  display: flex;
  gap: 14px;
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
  font-size: 12px;
  font-weight: 700;
}

.signal-price {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'SF Mono', monospace;
}

.signal-long { color: var(--red); }
.signal-short { color: var(--green); }
.signal-close { color: var(--orange); }
.signal-hold { color: var(--text-muted); }

/* ─── 卡片底部 ─── */
.card-footer {
  padding: 8px 14px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  background: var(--bg-hover);
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: auto;
}

.strategy-type {
  padding: 2px 8px;
  background: var(--accent-light);
  color: var(--accent);
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}

.footer-actions {
  display: flex;
  gap: 6px;
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
