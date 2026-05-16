<template>
  <div class="dashboard-page">
    <!-- 实时价格滚动条 -->
    <div class="price-ticker">
      <!-- 恐惧贪婪指数（固定在左边） -->
      <div class="fear-greed-fixed">
        <div class="fgi-icon">{{ fearGreedEmoji }}</div>
        <div class="fgi-content">
          <div class="fgi-value" :class="fearGreedClass">{{ fearGreedIndex }}</div>
          <div class="fgi-label">{{ fearGreedLabel }}</div>
        </div>
      </div>
      <!-- 滚动的币种价格：内容脱离 Vue 模板，由 JS 直接管理 DOM -->
      <div class="ticker-scroll-area">
        <div class="ticker-track" ref="tickerTrack"></div>
      </div>
    </div>

    <!-- 三栏布局：左中列 + 右列（热门活动跨两行） -->
    <div class="dashboard-three-col">
      <!-- 左中列容器 -->
      <div class="left-center-col">
        <!-- 第一排：个人中心 + 量化机器人收益 -->
        <el-row :gutter="20" class="pair-row">
          <el-col :span="12">
            <el-card shadow="hover" class="panel-card profit-card">
              <template #header>
                <div class="panel-header">
                  <span class="panel-title">个人中心</span>
                </div>
              </template>
              <div class="personal-center">
                <!-- 交易所绑定卡片 -->
                <div class="exchange-cards" :class="{ 'single-bound': bitgetBound }">
                  <!-- Bitget -->
                  <div class="exchange-card" :class="{ 'exchange-card--bound': bitgetBound }">
                    <div class="exchange-header">
                      <div class="exchange-logo bitget-logo">
                        <span class="logo-text">BG</span>
                      </div>
                      <div class="exchange-info">
                        <div class="exchange-name">Bitget</div>
                        <el-tag :type="bitgetBound ? 'success' : 'info'" size="small">
                          {{ bitgetBound ? '已绑定' : '未绑定' }}
                        </el-tag>
                      </div>
                    </div>
                    <!-- 已绑定：统计网格 -->
                    <div v-if="bitgetBound" class="bound-stats">
                      <div class="bound-stat">
                        <div class="bound-stat-label">UID</div>
                        <div class="bound-stat-value">{{ apiConfig.bitget_uid || '--' }}</div>
                      </div>
                      <div class="bound-stat">
                        <div class="bound-stat-label">账户余额</div>
                        <div class="bound-stat-value" :class="{ 'stat-loading': accountBalance === null }">{{ accountBalance === null ? '...' : '$' + formatNum(accountBalance) }}</div>
                      </div>
                      <div class="bound-stat">
                        <div class="bound-stat-label">策略</div>
                        <div class="bound-stat-value accent" :class="{ 'stat-loading': runningStrategies === null }">{{ runningStrategies === null ? '...' : runningStrategies + ' 个' }}</div>
                      </div>
                      <div class="bound-stat">
                        <div class="bound-stat-label">总盈亏</div>
                        <div class="bound-stat-value" :class="[totalStrategyProfit === null ? '' : (totalStrategyProfit >= 0 ? 'stat-up' : 'stat-down'), { 'stat-loading': totalStrategyProfit === null }]">
                          {{ totalStrategyProfit === null ? '...' : (totalStrategyProfit >= 0 ? '+' : '') + '$' + formatNum(totalStrategyProfit) }}
                        </div>
                      </div>
                    </div>
                    <div v-if="bitgetBound" class="bound-unbind" @click="unbindExchange('bitget')">
                      <span class="unbind-icon">❌</span>
                      <span class="unbind-text">解除绑定</span>
                    </div>
                    <div v-if="!bitgetBound" class="exchange-actions">
                      <a v-if="registerUrls.bitget" :href="registerUrls.bitget" target="_blank" class="register-btn">注册</a>
                      <el-button type="primary" size="small" @click="showBindDialog('bitget')">绑定</el-button>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" class="panel-card robot-panel">
              <template #header>
                <div class="panel-header">
                  <span class="panel-title">
                    <span class="robot-title-icon">🤖</span>
                    量化机器人收益
                  </span>
                  <router-link to="/strategy/robots" class="robot-view-all">
                    查看全部
                    <span class="view-all-arrow">→</span>
                  </router-link>
                </div>
              </template>
              <div class="robot-summary-list" v-loading="robotsLoading">
                <template v-if="robotsData.length > 0">
                  <!-- 领奖台 - 前三名 -->
                  <div class="podium-section" v-if="podiumRobots.length > 0">
                    <!-- 第一名 - 王者卡片 -->
                    <div class="podium-gold" :class="{ 'pnl-bg-up': podiumRobots[0].total_pnl >= 0, 'pnl-bg-down': podiumRobots[0].total_pnl < 0 }">
                      <div class="pg-glow"></div>
                      <div class="pg-border-shine"></div>
                      <div class="pg-top">
                        <div class="pg-left">
                          <div class="pg-avatar-box">
                            <img src="../assets/robot-icon.png" class="pg-avatar" />
                            <span class="pg-rank-badge">NO.1</span>
                            <img :src="trophyImgs[0]" class="pg-crown" />
                          </div>
                          <div class="pg-info">
                            <div class="pg-name">{{ podiumRobots[0].name }}</div>
                            <div class="pg-sub">
                              <span class="pg-chip pg-chip--gold"><i class="pg-dot pg-dot--gold"></i> {{ formatRuntime(podiumRobots[0]) }}</span>
                              <span class="pg-chip pg-chip--strat">{{ podiumRobots[0].strategy_count || 0 }} 策略</span>
                              <span v-if="podiumRobots[0].is_running" class="pg-chip pg-chip--live"><i class="pg-dot"></i> 运行中</span>
                            </div>
                          </div>
                        </div>
                        <div class="pg-right">
                          <div class="pg-pnl-wrap" :class="podiumRobots[0].total_pnl >= 0 ? 'pnl-up' : 'pnl-down'">
                            <div class="pg-pnl-sign">{{ podiumRobots[0].total_pnl >= 0 ? '+' : '-' }}</div>
                            <div class="pg-pnl-num">{{ Math.abs(podiumRobots[0].total_pnl).toFixed(2) }}</div>
                          </div>
                          <div class="pg-pnl-label">总盈亏 (USDT)</div>
                        </div>
                      </div>
                      <div class="pg-divider"></div>
                      <div class="pg-metrics">
                        <div class="gm-item">
                          <div class="gm-ring" :class="podiumRobots[0].win_rate >= 70 ? 'gm-ring--green' : 'gm-ring--blue'">
                            <svg viewBox="0 0 36 36"><circle cx="18" cy="18" r="15.5" fill="none" stroke-width="2.5" stroke="currentColor" class="gm-ring-bg"/><circle cx="18" cy="18" r="15.5" fill="none" stroke-width="2.5" :stroke-dasharray="`${podiumRobots[0].win_rate * 0.974} 97.4`" stroke-linecap="round" class="gm-ring-fg"/></svg>
                            <span class="gm-ring-val">{{ podiumRobots[0].win_rate?.toFixed(0) }}</span>
                          </div>
                          <span class="gm-text">胜率%</span>
                        </div>
                        <div class="gm-bar-item">
                          <span class="gm-bar-label">月化收益</span>
                          <div class="gm-bar-track"><div class="gm-bar-fill" :class="calcRobotMonthly(podiumRobots[0]) >= 0 ? 'gm-bar--up' : 'gm-bar--down'" :style="{ width: Math.min(Math.abs(calcRobotMonthly(podiumRobots[0])) * 2, 100) + '%' }"></div></div>
                          <span class="gm-bar-val" :class="calcRobotMonthly(podiumRobots[0]) >= 0 ? 'gm-val--green' : 'gm-val--red'">{{ calcRobotMonthly(podiumRobots[0]) >= 0 ? '+' : '' }}{{ calcRobotMonthly(podiumRobots[0]).toFixed(1) }}%</span>
                        </div>
                        <div class="gm-num-item">
                          <span class="gm-num-val">{{ podiumRobots[0].trade_count }}</span>
                          <span class="gm-num-label">交易笔数</span>
                        </div>
                        <div class="gm-num-item">
                          <span class="gm-num-val" :class="(podiumRobots[0].max_drawdown || 0) > 5 ? 'gm-val--red' : ''">{{ podiumRobots[0].max_drawdown?.toFixed(1) }}%</span>
                          <span class="gm-num-label">最大回撤</span>
                        </div>
                        <div class="gm-num-item">
                          <span class="gm-num-val">{{ podiumRobots[0].strategy_count || 0 }}</span>
                          <span class="gm-num-label">运行策略</span>
                        </div>
                        <div class="gm-num-item">
                          <span class="gm-num-val" :class="(10000 + (podiumRobots[0].total_pnl || 0)) >= 10000 ? 'gm-val--green' : 'gm-val--red'">{{ (10000 + (podiumRobots[0].total_pnl || 0)).toFixed(0) }}U</span>
                          <span class="gm-num-label">剩余资金</span>
                        </div>
                      </div>
                    </div>
                    <!-- 第二三名 -->
                    <div class="podium-row-bottom">
                      <template v-for="(robot, idx) in podiumRobots.slice(1)" :key="robot.id">
                        <div class="podium-small" :class="[idx === 0 ? 'podium-silver' : 'podium-bronze', robot.total_pnl >= 0 ? 'pnl-bg-up' : 'pnl-bg-down']">
                          <div class="ps-header">
                            <div class="ps-avatar-box">
                              <img src="../assets/robot-icon.png" class="ps-avatar" />
                              <span class="ps-rank">{{ idx === 0 ? '2' : '3' }}</span>
                              <img :src="trophyImgs[idx + 1]" class="ps-medal" />
                            </div>
                            <div class="ps-mid">
                              <div class="ps-name">{{ robot.name }}</div>
                              <div class="ps-meta-row">
                                <span class="ps-runtime"><i class="ps-clock">⏱</i> {{ formatRuntime(robot) }}</span>
                                <span v-if="robot.is_running" class="ps-live"><i class="pg-dot"></i> 运行中</span>
                              </div>
                            </div>
                            <div class="ps-pnl" :class="robot.total_pnl >= 0 ? 'pnl-up' : 'pnl-down'">
                              <span class="ps-pnl-sign">{{ robot.total_pnl >= 0 ? '+' : '' }}</span>{{ robot.total_pnl.toFixed(2) }}<span class="pnl-u">U</span>
                            </div>
                          </div>
                          <div class="ps-grid">
                            <div class="ps-cell"><span class="ps-cl">胜率</span><span class="ps-cv" :class="robot.win_rate >= 70 ? 'gm-val--green' : ''">{{ robot.win_rate?.toFixed(1) }}%</span></div>
                            <div class="ps-cell"><span class="ps-cl">月化</span><span class="ps-cv" :class="calcRobotMonthly(robot) >= 0 ? 'gm-val--green' : 'gm-val--red'">{{ calcRobotMonthly(robot) >= 0 ? '+' : '' }}{{ calcRobotMonthly(robot).toFixed(1) }}%</span></div>
                            <div class="ps-cell"><span class="ps-cl">交易</span><span class="ps-cv">{{ robot.trade_count }}笔</span></div>
                            <div class="ps-cell"><span class="ps-cl">回撤</span><span class="ps-cv">{{ robot.max_drawdown?.toFixed(1) }}%</span></div>
                            <div class="ps-cell"><span class="ps-cl">策略</span><span class="ps-cv">{{ robot.strategy_count || 0 }}个</span></div>
                            <div class="ps-cell"><span class="ps-cl">资金</span><span class="ps-cv" :class="(10000 + (robot.total_pnl || 0)) >= 10000 ? 'gm-val--green' : 'gm-val--red'">{{ (10000 + (robot.total_pnl || 0)).toFixed(0) }}U</span></div>
                          </div>
                        </div>
                      </template>
                    </div>
                  </div>

                  <!-- 其余机器人 - 列表 -->
                  <div class="robot-cards-list" v-if="restRobots.length > 0">
                    <div class="robot-card" v-for="r in restRobots" :key="r.id" :class="{ 'robot-card--running': r.is_running }">
                      <div class="rc-header">
                        <div class="rc-avatar">
                          <span class="rc-emoji">{{ r.is_running ? '🤖' : '💤' }}</span>
                          <span v-if="r.is_running" class="rc-status-dot"></span>
                        </div>
                        <div class="rc-info">
                          <div class="rc-name">{{ r.name }}</div>
                          <div class="rc-meta">
                            <span class="rc-badge">{{ r.strategy_count || 0 }} 策略</span>
                            <span class="rc-badge">⏱ {{ formatRuntime(r) }}</span>
                            <span class="rc-monthly" :class="calcRobotMonthly(r) >= 0 ? 'up' : 'down'">
                              月化 {{ calcRobotMonthly(r) >= 0 ? '+' : '' }}{{ calcRobotMonthly(r).toFixed(1) }}%
                            </span>
                          </div>
                        </div>
                        <div class="rc-pnl" :class="r.total_pnl >= 0 ? 'pnl-up' : 'pnl-down'">
                          <span class="rc-pnl-value">{{ r.total_pnl >= 0 ? '+' : '' }}{{ r.total_pnl.toFixed(2) }}</span>
                          <span class="rc-pnl-unit">U</span>
                        </div>
                      </div>
                      <div class="rc-footer">
                        <div class="rc-stat">
                          <span class="rc-stat-icon">🎯</span>
                          <span class="rc-stat-val" :class="r.win_rate >= 70 ? 'high-win' : ''">{{ r.win_rate.toFixed(1) }}%</span>
                        </div>
                        <div class="rc-stat">
                          <span class="rc-stat-icon">📊</span>
                          <span class="rc-stat-val">{{ r.trade_count }} 笔</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
                <div v-else class="placeholder-block">
                  <el-empty description="暂无机器人" :image-size="48" />
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 第二排：精选策略 + AI智能分析室 -->
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="9" style="display: flex;">
            <div class="featured-strategies-section" style="flex: 1; display: flex; flex-direction: column;">
              <div class="panel-header" style="margin-bottom: 12px;">
                <span class="panel-title">
                  <span class="featured-icon">⭐</span>
                  精选策略
                </span>
                <router-link to="/strategy" class="view-all-link">查看全部 →</router-link>
              </div>
              <div class="featured-strategies-list" v-loading="featuredStrategiesLoading" style="flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
                <template v-if="enrichedStrategies.length > 0">
                  <div class="strategy-card" v-for="(s, idx) in enrichedStrategies" :key="s.id" :class="'sc-theme-' + idx">
                    <!-- 顶部光效 -->
                    <div class="sc-glow"></div>
                    <!-- 头部：名称 + 收益率 -->
                    <div class="sc-header">
                      <div class="sc-title-row">
                        <div class="sc-icon-wrap" :class="'sc-icon-' + idx">
                          <span>{{ idx === 0 ? '📊' : '🎯' }}</span>
                        </div>
                        <div class="sc-title-info">
                          <div class="sc-name-row">
                            <span class="sc-name">{{ s.name }}</span>
                            <span class="sc-badge">官方精选</span>
                          </div>
                          <span class="sc-type-label">{{ strategyTypeLabel(s.type) }}</span>
                        </div>
                      </div>
                      <div class="sc-profit-box" :class="s.profit >= 0 ? 'profit-up' : 'profit-down'">
                        <div class="sc-profit-main">
                          <span class="sc-profit-val">{{ s.profit >= 0 ? '+' : '' }}{{ s.profit || 0 }}</span>
                          <span class="sc-profit-unit">%</span>
                        </div>
                        <span class="sc-profit-period">月化</span>
                      </div>
                    </div>
                    <!-- 策略描述 -->
                    <div class="sc-desc">{{ s.desc || '多维度技术指标，捕捉市场趋势' }}</div>
                    <!-- 数据指标网格 -->
                    <div class="sc-stats-grid">
                      <div class="sc-stat">
                        <div class="sc-stat-val" :class="{ 'text-green': (s.win_rate || 0) >= 70 }">{{ s.win_rate || '--' }}%</div>
                        <div class="sc-stat-label">胜率</div>
                      </div>
                      <div class="sc-stat">
                        <div class="sc-stat-val" :class="{ 'text-red': (s.max_drawdown || 0) > 5 }">{{ s.max_drawdown || '--' }}%</div>
                        <div class="sc-stat-label">最大回撤</div>
                      </div>
                      <div class="sc-stat">
                        <div class="sc-stat-val text-green">{{ s.sharpe || '--' }}</div>
                        <div class="sc-stat-label">夏普比率</div>
                      </div>
                      <div class="sc-stat">
                        <div class="sc-stat-val">{{ s.trades || '--' }}</div>
                        <div class="sc-stat-label">交易笔数</div>
                      </div>
                      <div class="sc-stat">
                        <div class="sc-stat-val">{{ s.users || 0 }}</div>
                        <div class="sc-stat-label">使用人数</div>
                      </div>
                      <div class="sc-stat">
                        <div class="sc-stat-val sc-rating">
                          <span class="sc-stars">{{ '★'.repeat(Math.round(s.rating || 4)) }}{{ '☆'.repeat(5 - Math.round(s.rating || 4)) }}</span>
                          <span>{{ s.rating || '4.0' }}</span>
                        </div>
                        <div class="sc-stat-label">综合评分</div>
                      </div>
                    </div>
                    <!-- 底部按钮 -->
                    <el-button type="primary" class="sc-btn" @click="useStrategy(s)">
                      <span class="sc-btn-icon">🚀</span> 立即使用
                    </el-button>
                  </div>
                </template>
                <el-empty v-else description="暂无精选策略" :image-size="48" />
              </div>
            </div>
          </el-col>

          <el-col :span="15" style="display: flex;">
            <div class="ai-chat-section" style="flex: 1;">
              <div class="panel-header" style="margin-bottom: 8px;">
                <span class="panel-title">
                  <span class="ai-chat-icon">🤖</span>
                  AI 智能分析室
                </span>
                <div class="ai-right-badges">
                  <div class="ai-current-time" v-if="aiTeamTimestamp">
                    <span class="act-label">当前分析为</span>
                    <span class="act-time">{{ formattedAnalysisTime }}</span>
                    <span class="act-period">{{ aiTeamPeriod }}周期</span>
                  </div>
                  <div class="ai-countdown" v-if="!aiTeamLoading">
                    <span class="countdown-label">⏱️ 下次</span>
                    <span class="countdown-time">{{ nextAnalysisCountdown }}</span>
                  </div>
                </div>
              </div>

              <!-- 聊天风格容器 -->
              <div class="ai-chat-window">
                <!-- 模型标识栏 -->
                <div class="ai-models-bar">
                  <span class="ai-model-tag"><span class="amt-dot"></span>GLM-5</span>
                  <span class="ai-model-tag"><span class="amt-dot"></span>Kimi-2.5</span>
                  <span class="ai-model-tag"><span class="amt-dot"></span>Minimax-2.5</span>
                  <span class="ai-model-tag judge">⚖️ DeepSeek-V3 裁决</span>
                </div>

                <!-- 两栏布局 -->
                <div class="ai-two-col" v-if="Object.keys(aiTeamOpinions).length > 0 || aiTeamJudge">
                  <!-- 左栏：分析师 -->
                  <div class="ai-col-left">
                    <div class="ai-analyst-card" v-for="(opinion, key, idx) in aiTeamOpinions" :key="key" :class="'aac-' + key" @click="goToAIWarRoom">
                      <div class="aac-color-bar"></div>
                      <div class="aac-body">
                        <div class="ai-ac-header">
                          <div class="ai-ac-avatar">
                            <img v-if="getAnalystAvatar(key)" :src="getAnalystAvatar(key)" />
                            <span v-else>{{ getAnalystEmoji(key) }}</span>
                          </div>
                          <span class="ai-ac-name">{{ getAnalystName(key) }}</span>
                          <span class="ai-ac-tag">{{ getAnalystTag(key) }}</span>
                        </div>
                        <div class="ai-ac-content" v-html="formatContent(opinion)"></div>
                      </div>
                    </div>
                  </div>

                  <!-- 右栏：裁决 -->
                  <div class="ai-col-right">
                    <div v-if="aiTeamJudge" class="ai-judge-card" @click="goToAIWarRoom">
                      <div class="ai-jc-header">
                        <span class="ai-jc-icon">🏆</span>
                        <span class="ai-jc-title">综合判断</span>
                      </div>
                      <div class="ai-jc-content" v-html="formatContent(aiTeamJudge)"></div>
                    </div>

                    <!-- 实时状态 -->
                    <div class="ai-live-panel" v-if="aiTeamJudge">
                      <div class="ai-live-title">⚡ 实时监控</div>
                      <div class="ai-live-grid">
                        <div class="ai-live-item">
                          <span class="ai-live-icon">🎯</span>
                          <span class="ai-live-val" :class="'dir-' + currentDirection">{{ currentDirection === 'long' ? '做多' : currentDirection === 'short' ? '做空' : '观望' }}</span>
                        </div>
                        <div class="ai-live-item">
                          <span class="ai-live-icon">📍</span>
                          <span class="ai-live-val">${{ currentEntry || '--' }}</span>
                        </div>
                        <div class="ai-live-item">
                          <span class="ai-live-icon">📊</span>
                          <span class="ai-live-val">${{ btcPrice || '--' }}</span>
                        </div>
                        <div class="ai-live-item" :class="livePnL >= 0 ? 'pnl-up' : 'pnl-down'">
                          <span class="ai-live-icon">💰</span>
                          <span class="ai-live-val">{{ livePnL >= 0 ? '+' : '' }}{{ livePnL || 0 }}点</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 空状态 -->
                <div v-else class="ai-empty-state">
                  <div class="ai-empty-icon">🤖</div>
                  <p class="ai-empty-title">AI 团队待命中</p>
                  <p class="ai-empty-desc">每30分钟自动分析市场</p>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>

        <!-- 第三排：最近交易 -->
        <div class="third-row-trades">
          <el-card shadow="hover" class="panel-card">
            <template #header>
              <div class="panel-header">
                <span class="panel-title">最近交易</span>
                <el-button text size="small" type="primary">查看全部</el-button>
              </div>
            </template>
            <div class="trade-list">
              <div class="trade-item" v-for="t in recentTrades" :key="t.id">
                <div class="trade-left">
                  <el-tag :type="t.side === '买入' ? 'danger' : 'success'" size="small" effect="plain" round>{{ t.side }}</el-tag>
                  <span class="trade-symbol">{{ t.symbol }}</span>
                </div>
                <div class="trade-right">
                  <span class="trade-price">{{ t.price || '--' }}</span>
                  <span class="trade-pnl" v-if="t.pnl" :class="t.pnl >= 0 ? 'pnl-up' : 'pnl-down'">{{ t.pnl >= 0 ? '+' : '' }}{{ t.pnl }}</span>
                </div>
              </div>
              <el-empty v-if="recentTrades.length === 0" description="暂无交易记录" :image-size="40" />
            </div>
          </el-card>
        </div>
      </div>

      <!-- 右列：热门活动 + 市场状态（跨两行） -->
      <div class="right-col">
        <div class="hot-activity-section">
          <div class="panel-header">
            <span class="panel-title">
              <img src="/images/fire.png" class="title-icon" alt="🔥" />
              热门活动
            </span>
          </div>
          <div class="activity-banner">
            <el-carousel v-if="activityBanners.length > 0" height="200px" :autoplay="true" :interval="4000" indicator-position="none">
              <el-carousel-item v-for="(banner, idx) in activityBanners" :key="idx">
                <img :src="banner.url" alt="活动横幅" class="banner-image" @click="banner.link && window.open(banner.link)" :style="{ cursor: banner.link ? 'pointer' : 'default' }" />
              </el-carousel-item>
            </el-carousel>
            <div v-else class="banner-placeholder">图片展示区</div>
          </div>
          <div class="activity-list" v-if="!hotActivityLoading">
            <div class="activity-item" v-for="(item, idx) in hotActivities" :key="idx">
              <div class="activity-icon">
                <img :src="item.icon" alt="" class="activity-icon-img" />
              </div>
              <div class="activity-info">
                <div class="activity-title">{{ item.title }}</div>
                <div class="activity-desc">{{ item.desc }}</div>
                <div class="activity-status" :class="item.statusType">{{ item.status }}</div>
              </div>
              <span v-if="item.badge" class="activity-badge" :class="'badge-' + item.badgeType">{{ item.badge }}</span>
            </div>
          </div>
          <div class="activity-list" v-else>
            <div class="activity-item activity-skeleton" v-for="n in 3" :key="n">
              <div class="skeleton-icon"></div>
              <div class="skeleton-info">
                <div class="skeleton-line w-60"></div>
                <div class="skeleton-line w-90"></div>
                <div class="skeleton-line w-35"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 市场状态仪表盘 -->
        <div class="market-regime-section" v-loading="regimeLoading">
          <div class="panel-header" style="margin-bottom: 10px;">
            <span class="panel-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;vertical-align:middle;margin-right:4px;">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
              </svg>
              市场状态
            </span>
            <span class="regime-update-tag">LIVE</span>
          </div>

          <!-- 仪表盘主体 -->
          <div class="regime-body" :class="'regime-body--' + regimeData.regime">
            <!-- 仪表盘 -->
            <div class="regime-gauge-wrap">
              <svg viewBox="0 0 200 130" class="regime-arc">
                <defs>
                  <linearGradient id="arcGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" :stop-color="regimeColor" stop-opacity="0.2"/>
                    <stop offset="100%" :stop-color="regimeColor" stop-opacity="1"/>
                  </linearGradient>
                  <filter id="arcGlow">
                    <feGaussianBlur stdDeviation="4" result="blur"/>
                    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                  <radialGradient id="scoreGlow" cx="50%" cy="55%" r="50%">
                    <stop offset="0%" :stop-color="regimeColor" stop-opacity="0.08"/>
                    <stop offset="100%" :stop-color="regimeColor" stop-opacity="0"/>
                  </radialGradient>
                </defs>
                <!-- 背景光晕 -->
                <circle cx="100" cy="90" r="70" fill="url(#scoreGlow)"/>
                <!-- 背景弧 -->
                <path d="M 20 120 A 80 80 0 0 1 180 120" fill="none" stroke="var(--border-secondary)" stroke-width="10" stroke-linecap="round" opacity="0.5"/>
                <!-- 前景弧 -->
                <path d="M 20 120 A 80 80 0 0 1 180 120" fill="none"
                  stroke="url(#arcGrad)" stroke-width="10" stroke-linecap="round"
                  :stroke-dasharray="251.3"
                  :stroke-dashoffset="251.3 * (1 - regimeData.score)"
                  filter="url(#arcGlow)"
                  style="transition: stroke-dashoffset 1s cubic-bezier(.4,0,.2,1)"/>
                <!-- 分数 -->
                <text x="100" y="92" text-anchor="middle" :fill="regimeColor" font-size="38" font-weight="800" class="regime-score-text">{{ Math.round(regimeData.score * 100) }}</text>
                <text x="100" y="112" text-anchor="middle" fill="currentColor" font-size="10" opacity="0.4" class="regime-score-label">趋势评分</text>
              </svg>
            </div>

            <!-- 状态标签行 -->
            <div class="regime-status-row">
              <div class="regime-badge" :class="'badge--' + regimeData.regime">{{ regimeData.regime_label }}</div>
              <div class="regime-direction" v-if="regimeData.trend_direction">
                <svg viewBox="0 0 16 16" class="dir-arrow" :class="'dir--' + regimeData.trend_direction">
                  <path :d="regimeData.trend_direction === 'up' ? 'M8 2 L13 9 L10 9 L10 14 L6 14 L6 9 L3 9 Z' : 'M8 14 L3 7 L6 7 L6 2 L10 2 L10 7 L13 7 Z'"/>
                </svg>
                <span :class="'dir-text--' + regimeData.trend_direction">{{ regimeData.trend_direction === 'up' ? '偏多' : '偏空' }}</span>
              </div>
            </div>

            <!-- 提示 -->
            <div class="regime-tip">{{ regimeHint }}</div>

            <!-- 指标条 -->
            <div class="regime-indicators">
              <div class="indicator" v-for="m in regimeIndicators" :key="m.key">
                <div class="indicator-head">
                  <span class="indicator-name">{{ m.name }}</span>
                  <span class="indicator-val">{{ m.value }}</span>
                </div>
                <div class="indicator-track">
                  <div class="indicator-fill" :style="{ width: m.pct + '%', background: regimeColor }"></div>
                </div>
              </div>
            </div>

            <!-- 底栏 -->
            <div class="regime-bar">
              <div class="bar-cell">
                <span class="bar-label">BTC</span>
                <span class="bar-price">${{ formatNum(regimeData.btc_price) }}</span>
                <span class="bar-chg" :class="regimeData.btc_change_24h >= 0 ? 'pnl-up' : 'pnl-down'">
                  {{ regimeData.btc_change_24h >= 0 ? '+' : '' }}{{ regimeData.btc_change_24h?.toFixed(2) }}%
                </span>
              </div>
              <div class="bar-divider"></div>
              <div class="bar-cell">
                <span class="bar-label">资金费率</span>
                <span class="bar-val">{{ (regimeData.funding_rate * 100).toFixed(4) }}%</span>
              </div>
              <div class="bar-divider"></div>
              <div class="bar-cell">
                <span class="bar-label">恐惧贪婪</span>
                <span class="bar-val" :style="{ color: fearGreedColor }">{{ regimeData.fear_greed || 50 }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- AI分析按钮 + 结果展示 -->
        <div class="ai-analyze-section">
          <el-button type="primary" class="ai-analyze-btn" @click="triggerAiAnalysis" :loading="aiAnalyzing" :disabled="aiAnalyzing">
            <span class="btn-icon">{{ aiAnalyzing ? '⏳' : '🤖' }}</span>
            {{ aiAnalyzing ? 'AI 分析中...' : 'AI 分析当前行情' }}
          </el-button>

          <!-- 分析中加载动画 -->
          <div class="ai-loading-overlay" v-if="aiAnalyzing && !aiQuickText">
            <div class="ai-loading-content">
              <div class="ai-loading-spinner"></div>
              <div class="ai-loading-text">AI 正在分析市场数据...</div>
              <div class="ai-loading-tips">
                <span>📊 读取K线数据</span>
                <span>📈 计算技术指标</span>
                <span>🤖 AI模型推理</span>
              </div>
            </div>
          </div>

          <!-- 分析结果简要展示 -->
          <div class="ai-quick-result" v-if="aiQuickText" :class="{ 'result-streaming': aiAnalyzing }">
            <div class="quick-text" v-html="formatContent(aiQuickText)"></div>
            <span v-if="aiAnalyzing" class="qa-cursor">|</span>
          </div>
        </div>

        <!-- AI判断追踪 -->
        <div class="ai-judge-tracker" v-if="judgeRecords.length > 0">
          <div class="tracker-title">
            <span class="tracker-icon">📈</span>
            <span>判断追踪</span>
          </div>
          <div class="tracker-list">
            <div class="tracker-item" v-for="r in judgeRecords" :key="r.id">
              <span class="tracker-time">{{ formatJudgeTime(r.created_at) }}</span>
              <span class="tracker-dir" :class="'dir-' + r.direction">
                {{ r.direction === 'long' ? '📈 多' : r.direction === 'short' ? '📉 空' : '⏸ 观' }}
              </span>
              <span class="tracker-price">${{ r.entry_price || '--' }}</span>
              <span class="tracker-result" :class="'result-' + r.result">
                <template v-if="r.result === 'correct'">✓</template>
                <template v-else-if="r.result === 'wrong'">✗</template>
                <template v-else>⏳</template>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div><!-- end dashboard-three-col -->

    <!-- OKX 绑定对话框 -->
    <el-dialog
      v-model="bindDialogVisible"
      width="380px"
      :close-on-click-modal="false"
      :show-close="true"
      class="bind-dialog"
      align-center
      destroy-on-close
    >
      <!-- 自定义标题 -->
      <template #header>
        <div class="bind-dialog-header">
          <span class="bind-title">Bitget API 登录</span>
        </div>
      </template>

      <div class="bind-dialog-content">
        <!-- 提示信息栏 -->
        <div class="bind-notice">
          交易所提供的ApiKey与Secret非常重要，请安全保管，我们不会上传您的信息，确保资产安全。
        </div>
        <!-- 表单 -->
        <el-form :model="bindForm" label-position="top" class="bind-form" :hide-required-asterisk="true">
          <el-form-item>
            <template #label>
              <span class="form-label">API Key</span>
            </template>
            <el-input 
              v-model="bindForm.key" 
              placeholder="请输入 API Key" 
              clearable 
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="form-label">Secret Key</span>
            </template>
            <el-input 
              v-model="bindForm.secret" 
              type="password" 
              placeholder="请输入 Secret Key" 
              show-password 
              clearable 
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="form-label">Passphrase</span>
            </template>
            <el-input 
              v-model="bindForm.passphrase" 
              type="password" 
              placeholder="请输入 Passphrase" 
              show-password 
              clearable 
            />
          </el-form-item>
        </el-form>
        <!-- 教程链接 -->
        <div class="bind-tutorial">
          <a href="https://www.bitget.com/zh-CN/account/newapi" target="_blank">不知道如何获取API? 查看教程</a>
        </div>
        <!-- 确认按钮 -->
        <el-button 
          type="primary" 
          class="bind-submit-btn" 
          :loading="bindLoading" 
          @click="confirmBind"
        >
          确认登录
        </el-button>
      </div>
      <template #footer>
        <span></span>
      </template>
    </el-dialog>

    <!-- 策略设置弹窗（简易版/专业版） -->
    <el-dialog
      v-model="strategyDialogVisible"
      width="720px"
      :close-on-click-modal="false"
      class="strategy-settings-dialog"
      destroy-on-close
    >
      <template #header>
        <div class="settings-header">
          <span>{{ strategyForm.name }} - 策略设置</span>
          <div class="mode-switch">
            <el-button :type="strategySettingsMode === 'simple' ? 'primary' : 'default'" size="small" @click="strategySettingsMode = 'simple'">简易版</el-button>
            <el-button :type="strategySettingsMode === 'pro' ? 'primary' : 'default'" size="small" @click="strategySettingsMode = 'pro'">专业版</el-button>
          </div>
        </div>
      </template>

      <!-- 简易版 -->
      <div v-if="strategySettingsMode === 'simple'" class="simple-settings">
        <el-form :model="strategyForm" label-width="100px" class="sqd-form">
          <el-form-item label="开仓平台">
            <el-select v-model="strategyForm.platform" style="width: 100%;" disabled>
              <el-option label="OKX" value="okx" />
            </el-select>
            <span class="hint-label">当前仅支持 OKX</span>
          </el-form-item>
          <el-form-item label="交易币种">
            <el-select v-model="strategyForm.inst_id" style="width: 100%;">
              <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
              <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
              <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
            </el-select>
          </el-form-item>
          <el-form-item label="开仓杠杆">
            <el-slider v-model="strategyForm.leverage" :min="1" :max="125" :step="1" show-input />
          </el-form-item>
          <el-form-item label="开仓百分比">
            <el-input-number v-model="strategyForm.size_pct" :min="1" :max="100" :step="5" />
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
        <el-tabs v-model="strategyProTab" type="border-card">
          <!-- Tab 1: 策略配置 -->
          <el-tab-pane label="策略配置" name="config">
            <el-form :model="strategyForm" label-width="100px" class="tab-form">
              <el-form-item label="开仓平台">
                <el-select v-model="strategyForm.platform" style="width: 100%;" disabled>
                  <el-option label="OKX" value="okx" />
                </el-select>
              </el-form-item>
              <el-form-item label="交易币种">
                <el-select v-model="strategyForm.inst_id" style="width: 100%;">
                  <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
                  <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
                  <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
                </el-select>
              </el-form-item>
              <el-form-item label="开仓杠杆">
                <el-slider v-model="strategyForm.leverage" :min="1" :max="125" :step="1" show-input />
              </el-form-item>
              <el-form-item label="开仓模式">
                <el-radio-group v-model="strategyForm.position_mode">
                  <el-radio value="both">多空双开</el-radio>
                  <el-radio value="long_only">仅开多</el-radio>
                  <el-radio value="short_only">仅开空</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="运行周期">
                <el-checkbox-group v-model="strategyForm.timeframes">
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
            <el-form :model="strategyForm" label-width="100px" class="tab-form">
              <el-form-item label="下单方式">
                <el-radio-group v-model="strategyForm.size_mode">
                  <el-radio value="fixed">按张数下单</el-radio>
                  <el-radio value="percent">按百分比下单</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="strategyForm.size_mode === 'fixed'" label="下单张数">
                <el-input-number v-model="strategyForm.size" :min="0.01" :max="1000" :step="0.01" :precision="2" />
                <span class="hint-label">合约张数（最小0.01）</span>
              </el-form-item>
              <el-form-item v-else label="仓位比例">
                <el-input-number v-model="strategyForm.size_pct" :min="1" :max="100" :step="5" />
                <span class="hint-label">% 可用资金</span>
              </el-form-item>

              <el-divider content-position="left">风控参数</el-divider>
              <el-form-item label="固定止盈">
                <el-input-number v-model="strategyForm.take_profit_pct" :min="0" :max="100" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不设止盈）</span>
              </el-form-item>
              <el-form-item label="固定止损">
                <el-input-number v-model="strategyForm.stop_loss_pct" :min="0" :max="50" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不设止损）</span>
              </el-form-item>
              <el-form-item label="移动止盈">
                <el-input-number v-model="strategyForm.trailing_stop_pct" :min="0" :max="20" :step="0.1" :precision="2" />
                <span class="hint-label">%（0=不启用）</span>
              </el-form-item>
              <el-form-item label="移动激活阈值">
                <el-input-number v-model="strategyForm.trail_activate_pct" :min="0" :max="10" :step="0.1" :precision="2" />
                <span class="hint-label">%（盈利达到此比例激活移动止盈）</span>
              </el-form-item>
              <el-form-item label="回调点数">
                <el-input-number v-model="strategyForm.trail_callback_points" :min="0" :max="1000" :step="1" />
                <span class="hint-label">点（价格回调此点数触发平仓）</span>
              </el-form-item>
              <el-form-item label="冷却时间">
                <el-input-number v-model="strategyForm.cooldown_minutes" :min="0" :max="1440" :step="5" />
                <span class="hint-label">分钟（开仓后冷却时间，0=不限制）</span>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- Tab 3: 策略指标参数 -->
          <el-tab-pane label="策略指标参数" name="indicator">
            <el-form :model="strategyForm" label-width="100px" class="tab-form">
              <template v-if="strategyForm.type === 'ma_cross'">
                <el-form-item label="短均线周期"><el-input-number v-model="strategyForm.params.fast_period" :min="2" :max="100" /></el-form-item>
                <el-form-item label="长均线周期"><el-input-number v-model="strategyForm.params.slow_period" :min="5" :max="200" /></el-form-item>
              </template>
              <template v-if="strategyForm.type === 'rsi'">
                <el-form-item label="RSI周期"><el-input-number v-model="strategyForm.params.period" :min="2" :max="100" /></el-form-item>
                <el-form-item label="超卖线"><el-input-number v-model="strategyForm.params.oversold" :min="10" :max="40" /></el-form-item>
                <el-form-item label="超买线"><el-input-number v-model="strategyForm.params.overbought" :min="60" :max="90" /></el-form-item>
              </template>
              <template v-if="strategyForm.type === 'bollinger'">
                <el-form-item label="布林带周期"><el-input-number v-model="strategyForm.params.period" :min="5" :max="100" /></el-form-item>
                <el-form-item label="标准差倍数"><el-input-number v-model="strategyForm.params.std_dev" :min="1" :max="4" :step="0.1" :precision="1" /></el-form-item>
              </template>
              <template v-if="strategyForm.type === 'macd_divergence'">
                <el-form-item label="MACD快线"><el-input-number v-model="strategyForm.params.macd_fast" :min="3" :max="20" /></el-form-item>
                <el-form-item label="MACD慢线"><el-input-number v-model="strategyForm.params.macd_slow" :min="10" :max="40" /></el-form-item>
                <el-form-item label="MACD信号线"><el-input-number v-model="strategyForm.params.macd_signal" :min="3" :max="15" /></el-form-item>
                <el-form-item label="峰值窗口"><el-input-number v-model="strategyForm.params.peak_window" :min="2" :max="20" /></el-form-item>
              </template>
              <template v-if="strategyForm.type === 'trend_break'">
                <el-form-item label="趋势EMA周期"><el-input-number v-model="strategyForm.params.ema_period" :min="5" :max="60" /></el-form-item>
                <el-form-item label="布林带周期"><el-input-number v-model="strategyForm.params.boll_period" :min="5" :max="30" /></el-form-item>
                <el-form-item label="布林标准差"><el-input-number v-model="strategyForm.params.boll_std" :min="0.5" :max="4" :step="0.1" :precision="1" /></el-form-item>
                <el-form-item label="量均周期"><el-input-number v-model="strategyForm.params.vol_ma_period" :min="5" :max="30" /></el-form-item>
                <el-form-item label="量比阈值"><el-input-number v-model="strategyForm.params.vol_ratio" :min="0.5" :max="3" :step="0.1" :precision="1" /></el-form-item>
              </template>
              <template v-if="strategyForm.type === 'rsi_macd'">
                <el-form-item label="RSI周期"><el-input-number v-model="strategyForm.params.rsi_period" :min="2" :max="30" /></el-form-item>
                <el-form-item label="超卖线"><el-input-number v-model="strategyForm.params.oversold" :min="10" :max="40" /></el-form-item>
                <el-form-item label="超买线"><el-input-number v-model="strategyForm.params.overbought" :min="60" :max="90" /></el-form-item>
                <el-form-item label="MACD快线"><el-input-number v-model="strategyForm.params.macd_fast" :min="3" :max="20" /></el-form-item>
                <el-form-item label="MACD慢线"><el-input-number v-model="strategyForm.params.macd_slow" :min="10" :max="40" /></el-form-item>
                <el-form-item label="MACD信号线"><el-input-number v-model="strategyForm.params.macd_signal" :min="3" :max="15" /></el-form-item>
              </template>
              <template v-if="strategyForm.type === 'vol_break'">
                <el-form-item label="回望周期"><el-input-number v-model="strategyForm.params.lookback" :min="5" :max="60" /></el-form-item>
                <el-form-item label="量均周期"><el-input-number v-model="strategyForm.params.vol_ma_period" :min="5" :max="30" /></el-form-item>
                <el-form-item label="量比阈值"><el-input-number v-model="strategyForm.params.vol_ratio" :min="1" :max="5" :step="0.1" :precision="1" /></el-form-item>
              </template>
              <template v-if="!['ma_cross', 'rsi', 'bollinger', 'macd_divergence', 'trend_break', 'rsi_macd', 'vol_break'].includes(strategyForm.type)">
                <div class="no-params-tip">该策略无额外指标参数</div>
              </template>
            </el-form>
          </el-tab-pane>

          <!-- Tab 4: 运行时间 -->
          <el-tab-pane label="运行时间" name="schedule">
            <el-form label-width="100px" class="tab-form">
              <el-form-item label="运行星期">
                <el-checkbox-group v-model="strategyForm.run_days">
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
                  <el-time-select v-model="strategyForm.run_start_time" placeholder="开始时间" start="00:00" step="00:30" end="23:30" style="width: 120px;" />
                  <span class="time-sep">至</span>
                  <el-time-select v-model="strategyForm.run_end_time" placeholder="结束时间" start="00:00" step="00:30" end="23:30" style="width: 120px;" />
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
        <div class="sqd-footer">
          <el-button @click="strategyDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="strategySaving" @click="saveAndStartStrategy" class="sqd-start-btn">
            <span v-if="!strategySaving">🚀 保存并启动</span>
            <span v-else>启动中...</span>
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, WarningFilled, InfoFilled } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useWebSocket } from '../utils/ws'
import * as echarts from 'echarts'
import okxLogo from '../assets/okx-logo.png'
import { useRouter } from 'vue-router'

const { on: wsOn, off: wsOff, connected: wsConnected } = useWebSocket()
const router = useRouter()

// ─── AI 分析室数据 ───
const aiTeamOpinions = ref({})
const aiTeamJudge = ref('')
const aiTeamTimestamp = ref('')
const aiTeamPeriod = ref('')
const formattedAnalysisTime = computed(() => {
  if (!aiTeamTimestamp.value) return ''
  // 去掉秒数，保留到分钟
  return aiTeamTimestamp.value.replace(/:\d{2}$/, '')
})

// ─── AI分析室Logo水印 ───
const siteLogo = ref('/static/uploads/site-logo.jpg')
const aiTeamLoading = ref(false)
const nextAnalysisCountdown = ref('')
const btcPrice = ref(null)

const analystConfig = ref({
  aggressive: { name: '趋势猎手', emoji: '🚀', avatar_url: '' },
  conservative: { name: '风控专家', emoji: '🛡️', avatar_url: '' },
  technical: { name: '量化派', emoji: '📊', avatar_url: '' },
  judge: { name: '裁决者', emoji: '⚖️', avatar_url: '' },
})

const analystShortNames = { aggressive: '趋势', conservative: '风控', technical: '量化', judge: '裁决' }

function getAnalystName(key) { return analystConfig.value[key]?.name || key }
function getAnalystEmoji(key) { return analystConfig.value[key]?.emoji || '🤖' }
function getAnalystAvatar(key) { return analystConfig.value[key]?.avatar_url || '' }
function getAnalystShortName(key) { return analystShortNames[key] || key }
function getAnalystTag(key) {
  const tags = { aggressive: '激进派', conservative: '稳健派', technical: '技术派' }
  return tags[key] || ''
}

function formatContent(text) {
  if (!text) return ''
  return text.trim().replace(/\r?\n/g, '\n').replace(/\n{2,}/g, '\n').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
}

function goToAIWarRoom() { router.push('/strategy/ai-war-room') }

// ─── AI快捷分析(右列按钮，单分析师) ───
const aiAnalyzing = ref(false)
const aiQuickText = ref('')
const aiQuickAnalyst = ref('')

async function triggerAiAnalysis() {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('AI分析功能仅限登录用户使用')
    return
  }
  if (aiAnalyzing.value) return
  aiAnalyzing.value = true
  aiQuickText.value = ''
  aiQuickAnalyst.value = ''

  try {
    const resp = await fetch('/api/dashboard/ai_quick_analysis', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.error || `HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.content) {
            aiQuickText.value += data.content
          }
          if (data.done) {
            // 分析完成
          }
          if (data.error) {
            aiQuickText.value += `\n⚠️ ${data.error}`
          }
        } catch (e) {
          // skip
        }
      }
    }
  } catch (e) {
    console.error('AI quick analysis error:', e)
    if (!aiQuickText.value) {
      aiQuickText.value = '分析失败: ' + e.message
    }
  } finally {
    aiAnalyzing.value = false
    loadJudgeRecords()
  }
}

// ─── AI判断追踪 ───
function formatJudgeTime(t) {
  if (!t) return '--'
  const d = new Date(t)
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function loadJudgeRecords() {
  try {
    const res = await api.get('/dashboard/ai_judge_records?limit=5')
    judgeRecords.value = res.records || []
  } catch (e) { console.error('judge records error:', e) }
}

// ─── 精选策略 ───
const featuredStrategies = ref([])
const featuredStrategiesLoading = ref(false)

// 策略模拟统计数据（精选策略展示用）
const strategyMockStats = {
  // key=策略type, value=统计数据
  default: { profit: 12.8, win_rate: 78.5, max_drawdown: 4.2, sharpe: 2.1, trades: 156, users: 328, rating: 4.6 },
  macd_divergence: { profit: 15.3, win_rate: 94.8, max_drawdown: 3.2, sharpe: 2.8, trades: 48, users: 512, rating: 4.9 },
  ma_cross: { profit: 8.6, win_rate: 72.3, max_drawdown: 6.1, sharpe: 1.5, trades: 203, users: 256, rating: 4.3 },
  rsi: { profit: 6.2, win_rate: 65.8, max_drawdown: 7.5, sharpe: 1.2, trades: 178, users: 189, rating: 4.1 },
  bollinger: { profit: 10.1, win_rate: 71.2, max_drawdown: 5.3, sharpe: 1.8, trades: 134, users: 215, rating: 4.4 },
  trend_break: { profit: 18.7, win_rate: 82.5, max_drawdown: 5.8, sharpe: 2.4, trades: 92, users: 387, rating: 4.7 },
  rsi_macd: { profit: 14.2, win_rate: 80.1, max_drawdown: 4.6, sharpe: 2.3, trades: 167, users: 298, rating: 4.5 },
  vol_break: { profit: 11.9, win_rate: 76.4, max_drawdown: 4.8, sharpe: 2.0, trades: 145, users: 234, rating: 4.5 },
  supertrend: { profit: 9.3, win_rate: 69.7, max_drawdown: 5.5, sharpe: 1.6, trades: 189, users: 176, rating: 4.2 },
  kdj: { profit: 7.8, win_rate: 68.2, max_drawdown: 6.3, sharpe: 1.4, trades: 211, users: 165, rating: 4.2 },
  dual_ema: { profit: 11.5, win_rate: 74.8, max_drawdown: 4.9, sharpe: 1.9, trades: 153, users: 242, rating: 4.4 },
  ma_ribbon: { profit: 13.6, win_rate: 77.9, max_drawdown: 5.1, sharpe: 2.2, trades: 128, users: 278, rating: 4.6 },
  ema_volume: { profit: 10.8, win_rate: 73.5, max_drawdown: 4.4, sharpe: 1.9, trades: 142, users: 203, rating: 4.4 },
  cci: { profit: 5.9, win_rate: 64.1, max_drawdown: 7.8, sharpe: 1.1, trades: 195, users: 148, rating: 4.0 },
  st_kdj: { profit: 16.4, win_rate: 85.3, max_drawdown: 4.1, sharpe: 2.5, trades: 108, users: 342, rating: 4.8 },
  ribbon_macd: { profit: 14.8, win_rate: 79.6, max_drawdown: 4.3, sharpe: 2.4, trades: 119, users: 305, rating: 4.6 },
}

// 增强后的精选策略（注入模拟统计数据）
const enrichedStrategies = computed(() => {
  return featuredStrategies.value.map((s, idx) => {
    const mock = strategyMockStats[s.type] || strategyMockStats.default
    return {
      ...s,
      profit: s.profit ?? (idx === 0 ? mock.profit : mock.profit - 3),
      win_rate: s.win_rate ?? mock.win_rate,
      max_drawdown: s.max_drawdown ?? mock.max_drawdown,
      sharpe: s.sharpe ?? mock.sharpe,
      trades: s.trades ?? mock.trades,
      users: s.users ?? mock.users,
      rating: s.rating ?? mock.rating,
      desc: s.desc || getDefaultDesc(s.type),
    }
  })
})

function getDefaultDesc(type) {
  const descs = {
    macd_divergence: '基于MACD峰值背离检测，高胜率区间突破策略，30分钟周期最优表现',
    ma_cross: '双均线交叉经典策略，快慢均线金叉/死叉信号触发，适合趋势行情',
    rsi: 'RSI超买超卖反转策略，结合多周期确认过滤虚假信号，稳健收益',
    bollinger: '布林带收窄突破策略，捕捉波动率扩张带来的趋势行情',
    trend_break: 'EMA趋势+布林带+量能三重确认突破，过滤假突破，精准捕捉趋势',
    rsi_macd: 'RSI与MACD双指标共振策略，多重验证提高信号准确度',
    vol_break: '量能突破策略，基于成交量异常放大捕捉突破行情',
    supertrend: '超级趋势跟踪策略，ATR自适应通道，大趋势高收益',
    kdj: 'KDJ随机指标策略，结合K/D/J三线交叉判断买卖点',
    dual_ema: '双EMA趋势策略，长短周期EMA组合判断趋势方向',
    ma_ribbon: '均线Ribbon策略，多周期均线排列判断趋势强度',
    ema_volume: 'EMA量价策略，结合价格均线与成交量分析',
    cci: 'CCI商品通道指标策略，捕捉超买超卖极端行情',
    st_kdj: '超级KDJ策略，结合ATR通道的自适应KDJ改进版',
    ribbon_macd: '均线Ribbon+MACD组合策略，趋势判断+动量确认双重验证',
    bollinger: '布林带收窄突破策略，捕捉波动率扩张带来的趋势行情',
  }
  return descs[type] || '多维度技术指标量化策略，自适应市场状态，追求稳健收益'
}
const availableStrategies = ref([])
const strategyDialogVisible = ref(false)
const strategySaving = ref(false)
const strategyEditId = ref(null)
const strategySettingsMode = ref('simple')  // 'simple' | 'pro'
const strategyProTab = ref('config')

const strategyForm = reactive({
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
  position_mode: 'both',
  timeframes: ['1h'],
  run_days: [1, 2, 3, 4, 5, 6, 0],
  run_start_time: '00:00',
  run_end_time: '23:59',
  description: '',
  params: {},
})

// 各策略类型的指标参数 key 映射
const strategyParamKeys = {
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

async function loadAvailableStrategies() {
  try {
    const res = await api.get('/strategy/available')
    availableStrategies.value = res.strategies || []
  } catch { /* ignore */ }
}

function strategyTypeLabel(type) {
  const labels = {
    ma_cross: '均线交叉', rsi: 'RSI指标', bollinger: '布林带',
    macd: 'MACD', macd_divergence: 'MACD背离', ema_volume: 'EMA量价',
    supertrend: '超级趋势', kdj: 'KDJ', dual_ema: '双EMA',
    ma_ribbon: '均线 Ribbon', cci: 'CCI', trend_break: '趋势突破',
    rsi_macd: 'RSI+MACD', st_kdj: '超级KDJ', ribbon_macd: 'Ribbon+MACD',
    vol_break: '量能突破',
  }
  return labels[type] || type || '量化策略'
}

function useStrategy(s) {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请登录后再操作')
    return
  }
  if (!bitgetBound.value) {
    ElMessage.warning('未检测到交易所绑定')
    return
  }
  strategyEditId.value = s.id
  const p = s.params || {}
  strategyForm.name = s.name || '策略'
  strategyForm.type = s.type || ''
  strategyForm.platform = p.platform || 'okx'
  strategyForm.inst_id = p.inst_id || 'BTC-USDT-SWAP'
  strategyForm.size_mode = p.size_mode || 'percent'
  strategyForm.size = p.size ?? 1
  strategyForm.size_pct = p.size_pct ?? 10
  strategyForm.leverage = p.leverage ?? 10
  strategyForm.take_profit_pct = p.take_profit_pct ?? 5
  strategyForm.stop_loss_pct = p.stop_loss_pct ?? 3
  strategyForm.trailing_stop_pct = p.trailing_stop_pct ?? 0
  strategyForm.trail_activate_pct = p.trail_activate_pct ?? 0
  strategyForm.trail_callback_points = p.trail_callback_points ?? 0
  strategyForm.cooldown_minutes = p.cooldown_minutes ?? 0
  strategyForm.td_mode = p.td_mode || 'cross'
  strategyForm.position_mode = p.position_mode || 'both'
  strategyForm.timeframes = p.timeframes || ['1h']
  strategyForm.run_days = p.run_days || [1, 2, 3, 4, 5, 6, 0]
  strategyForm.run_start_time = p.run_start_time || '00:00'
  strategyForm.run_end_time = p.run_end_time || '23:59'
  strategyForm.description = p.description || ''

  // 填充策略指标参数
  const keys = strategyParamKeys[s.type] || []
  const paramsCopy = {}
  for (const k of keys) {
    paramsCopy[k] = p[k] ?? (availableStrategies.value.find(x => x.type === s.type)?.default_params || {})[k]
  }
  strategyForm.params = paramsCopy

  // 重置为简易版
  strategySettingsMode.value = 'simple'
  strategyProTab.value = 'config'
  strategyDialogVisible.value = true
}

async function saveAndStartStrategy() {
  if (!strategyEditId.value) return
  strategySaving.value = true
  try {
    const body = {
      platform: strategyForm.platform,
      inst_id: strategyForm.inst_id,
      leverage: strategyForm.leverage,
      size_mode: strategyForm.size_mode,
      size: strategyForm.size,
      size_pct: strategyForm.size_pct,
      position_mode: strategyForm.position_mode,
      timeframes: strategyForm.timeframes,
      run_days: strategyForm.run_days,
      run_start_time: strategyForm.run_start_time,
      run_end_time: strategyForm.run_end_time,
      take_profit_pct: strategyForm.take_profit_pct,
      stop_loss_pct: strategyForm.stop_loss_pct,
      trailing_stop_pct: strategyForm.trailing_stop_pct,
      trail_activate_pct: strategyForm.trail_activate_pct,
      trail_callback_points: strategyForm.trail_callback_points,
      cooldown_minutes: strategyForm.cooldown_minutes,
      td_mode: strategyForm.td_mode,
      description: strategyForm.description,
      params: strategyForm.params,
    }
    // 先保存设置
    await api.put(`/strategy/${strategyEditId.value}`, body)
    // 再启动
    await api.post(`/strategy/${strategyEditId.value}/start`)
    ElMessage.success('策略已启动')
    strategyDialogVisible.value = false
    // 刷新列表
    loadFeaturedStrategies()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    strategySaving.value = false
  }
}

// ─── 实时状态计算 ───
const currentDirection = computed(() => {
  if (!aiTeamJudge.value) return 'hold'
  if (aiTeamJudge.value.includes('做多')) return 'long'
  if (aiTeamJudge.value.includes('做空')) return 'short'
  return 'hold'
})
const currentEntry = computed(() => {
  if (judgeRecords.value.length === 0) return null
  return judgeRecords.value[0].entry_price
})
const livePnL = computed(() => {
  if (!currentEntry.value || !btcPrice.value) return 0
  const diff = btcPrice.value - currentEntry.value
  return currentDirection.value === 'long' ? diff : -diff
})

// ─── AI 数据加载 ───
async function loadAnalystConfig() {
  try {
    const res = await api.get('/settings/ai')
    if (res.analysts) {
      for (const key of ['aggressive', 'conservative', 'technical']) {
        if (res.analysts[key]) {
          analystConfig.value[key] = { name: res.analysts[key].name || key, emoji: res.analysts[key].emoji || '🤖', avatar_url: res.analysts[key].avatar_url || '' }
        }
      }
    }
    if (res.judge) analystConfig.value.judge = { name: res.judge.name || '裁决者', emoji: res.judge.emoji || '⚖️', avatar_url: res.judge.avatar_url || '' }
  } catch (e) { console.error('analyst config error:', e) }
}

async function loadAiChatHistory() {
  try {
    const res = await api.get('/dashboard/ai_chat_history?limit=1')
    if (res.history && res.history.length > 0) {
      const latest = res.history[0]
      aiTeamOpinions.value = latest.opinions || {}
      aiTeamJudge.value = latest.judge || ''
      aiTeamPeriod.value = latest.period || '30m'
      aiTeamTimestamp.value = latest.created_at ? new Date(latest.created_at).toLocaleString('zh-CN') : ''
    }
  } catch (e) { console.error('ai history error:', e) }
}

// ─── 市场状态仪表盘 ───
const regimeLoading = ref(true)
const regimeData = ref({
  regime: 'ranging',
  regime_label: '震荡',
  score: 0,
  trend_direction: '',
  btc_price: 0,
  btc_change_24h: 0,
  funding_rate: 0,
  fear_greed: 50,
  details: {},
})

const regimeColor = computed(() => {
  const map = {
    strong_trend: '#00b96b',
    trending: '#00b96b',
    weak_trend: '#f5a623',
    ranging: '#86909c',
    volatile: '#ff4d4f',
  }
  return map[regimeData.value.regime] || '#86909c'
})

const fearGreedColor = computed(() => {
  const v = regimeData.value.fear_greed || 50
  if (v >= 70) return '#22c55e'
  if (v >= 50) return '#f5a623'
  return '#ef4444'
})

const regimeHint = computed(() => {
  const map = {
    strong_trend: '市场处于强势趋势中，趋势策略表现优异',
    trending: '趋势形成中，可跟随方向操作',
    weak_trend: '趋势信号偏弱，建议轻仓或观望',
    ranging: '市场震荡整理，适合网格和高抛低吸',
    volatile: '高波动环境，注意风险控制',
  }
  return map[regimeData.value.regime] || '加载中...'
})

const regimeIndicators = computed(() => {
  const d = regimeData.value.details || {}
  // 后端返回格式: {adx: {value: 38.44, score: 1.0}, vol_ratio: {value: 0.522, score: 0.3}, ...}
  const adxVal = d.adx?.value ?? d.adx
  const volVal = d.vol_ratio?.value ?? d.vol_compress_ratio
  const devVal = d.deviation?.value ?? d.ma_deviation_pct
  const atrVal = d.atr_change?.value ?? d.atr_change_rate
  return [
    { key: 'adx', name: 'ADX 趋势强度', value: typeof adxVal === 'number' ? adxVal.toFixed(1) : '--', pct: typeof adxVal === 'number' ? Math.min(adxVal / 50 * 100, 100) : 0 },
    { key: 'vol_compress', name: '波动率压缩比', value: typeof volVal === 'number' ? volVal.toFixed(2) : '--', pct: typeof volVal === 'number' ? Math.min(volVal / 3 * 100, 100) : 0 },
    { key: 'ma_dev', name: '均线偏离度', value: typeof devVal === 'number' ? (devVal * 100).toFixed(2) + '%' : '--', pct: typeof devVal === 'number' ? Math.min(Math.abs(devVal) * 100 / 5 * 100, 100) : 0 },
    { key: 'atr_chg', name: 'ATR 变化率', value: typeof atrVal === 'number' ? (atrVal * 100).toFixed(1) + '%' : '--', pct: typeof atrVal === 'number' ? Math.min(Math.abs(atrVal) * 100, 100) : 0 },
  ]
})

async function fetchBtcPrice() {
  try {
    const r = await api.get('/dashboard/market_regime')
    if (r.btc_price) btcPrice.value = r.btc_price
    // 同时更新市场状态仪表盘数据
    regimeData.value = {
      regime: r.regime || 'ranging',
      regime_label: r.regime_label || '震荡',
      score: r.score || 0,
      trend_direction: r.trend_direction || '',
      btc_price: r.btc_price || 0,
      btc_change_24h: r.btc_change_24h || 0,
      funding_rate: r.funding_rate || 0,
      fear_greed: r.fear_greed || 50,
      details: r.details || {},
    }
    regimeLoading.value = false
  } catch (e) {
    regimeLoading.value = false
  }
}

function updateCountdown() {
  const now = new Date()
  const m = now.getMinutes(), s = now.getSeconds()
  let nM = m < 30 ? 30 - m - 1 : 60 - m - 1
  let nS = 60 - s
  if (nS === 60) { nM += 1; nS = 0 }
  if (nM < 0) nM = 0
  nextAnalysisCountdown.value = `${nM}分${nS}秒`
  if (s % 30 === 0) fetchBtcPrice()
}

async function fetchSiteLogo() {
  try {
    const r = await api.get('/settings/site')
    if (r.site_logo) siteLogo.value = r.site_logo
  } catch (e) { /* ignore */ }
}

async function loadFeaturedStrategies() {
  featuredStrategiesLoading.value = true
  try {
    const res = await api.get('/strategy/available')
    featuredStrategies.value = (res.strategies || res.list || res || []).slice(0, 2)
  } catch (e) { console.error('strategies error:', e) }
  featuredStrategiesLoading.value = false
}

let countdownTimer = null
const judgeRecords = ref([])

let pnlChart = null

const hasApiKey = ref(localStorage.getItem('bitget_bound') === '1')  // 先用 localStorage 快速渲染，防止闪烁
const accountBalance = ref(null)
const registerUrls = ref({ bitget: '' })
const unrealizedPnl = ref(null)
const fundingBalance = ref(0)
const currencies = ref([])
const positions = ref([])
const recentTrades = ref([])
const runningStrategies = ref(null)
const totalStrategyProfit = ref(null)

// 量化机器人数据
const robotsData = ref([])
const robotsLoading = ref(true)

// 领奖台奖牌图标
import trophyGoldImg from '../assets/trophy-gold.png'
import trophySilverImg from '../assets/trophy-silver.png'
import trophyBronzeImg from '../assets/trophy-bronze.png'
const trophyImgs = [trophyGoldImg, trophySilverImg, trophyBronzeImg]

// 机器人统计计算属性
const runningRobotCount = computed(() => robotsData.value.filter(r => r.is_running).length)
const totalRobotPnl = computed(() => robotsData.value.reduce((s, r) => s + (r.total_pnl || 0), 0))
const avgWinRate = computed(() => {
  if (robotsData.value.length === 0) return 0
  return robotsData.value.reduce((s, r) => s + (r.win_rate || 0), 0) / robotsData.value.length
})

// 按盈亏排序，分出前三名和其余
const sortedRobots = computed(() => {
  return [...robotsData.value].sort((a, b) => (b.total_pnl || 0) - (a.total_pnl || 0))
})
const podiumRobots = computed(() => sortedRobots.value.slice(0, 3))
const restRobots = computed(() => sortedRobots.value.slice(3))

function calcRobotMonthly(robot) {
  if (!robot.initial_capital || !robot.created_at) return 0
  const totalReturn = (robot.total_pnl / robot.initial_capital) * 100
  const createdAt = new Date(robot.created_at)
  const now = new Date()
  const daysRunning = Math.max(1, Math.floor((now - createdAt) / (1000 * 60 * 60 * 24)))
  return (totalReturn / daysRunning) * 30
}

function formatRuntime(robot) {
  if (!robot.created_at) return '--'
  const created = new Date(robot.created_at)
  const now = new Date()
  const diffMs = now - created
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (days < 1) {
    const hours = Math.floor(diffMs / (1000 * 60 * 60))
    return `${hours}小时`
  } else if (days < 30) {
    return `${days}天`
  } else if (days < 365) {
    const months = Math.floor(days / 30)
    const remainDays = days % 30
    return remainDays > 0 ? `${months}月${remainDays}天` : `${months}个月`
  } else {
    const years = Math.floor(days / 365)
    const months = Math.floor((days % 365) / 30)
    return months > 0 ? `${years}年${months}月` : `${years}年`
  }
}

// API配置相关
const apiConfig = ref({
  key: '',
  secret: '',
  passphrase: '',
  bitget_uid: localStorage.getItem('bitget_bound_uid') || '',
})
const savingApi = ref(false)
const testingApi = ref(false)
const refreshingUid = ref(false)
const testResult = ref(null)

// 热门活动数据 - setup 阶段从 localStorage 读取，首帧即有数据
const CACHE_KEY = 'hot_activities_cache'

function _readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) { /* ignore */ }
  return null
}
const _cached = _readCache()

const hotActivities = ref((_cached && _cached.activities) ? _cached.activities : [])
const activityBanners = ref((_cached && _cached.banners) ? _cached.banners : [])
const hotActivityLoading = ref(!_cached)

function saveActivitiesToCache(banners, activities) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ banners, activities }))
  } catch (e) { /* ignore */ }
}

async function fetchHotActivities() {
  try {
    const res = await api.get('/activities')
    const activities = (res.activities || []).map(a => ({
      icon: a.icon_url,
      title: a.title,
      desc: a.desc,
      status: a.status,
      statusType: a.status_type || 'status-active',
      badge: a.badge,
      badgeType: a.badge_type || '',
    }))
    activityBanners.value = res.banners || []
    hotActivities.value = activities
    saveActivitiesToCache(res.banners || [], activities)
  } catch (e) {
    console.error('Failed to load hot activities:', e)
  } finally {
    hotActivityLoading.value = false
  }
}

// 绑定对话框相关
const bindDialogVisible = ref(false)
const bindLoading = ref(false)
const bindForm = ref({
  key: '',
  secret: '',
  passphrase: '',
  sandbox: false, // 强制使用实盘
})

// Bitget 是否已绑定
const bitgetBound = computed(() => {
  return hasApiKey.value === true
})

// 实时价格滚动条 — 纯 CSS 动画 + DOM 直操作，脱离 Vue 响应式
const tickerTrack = ref(null)
const tickerCoins = [
  { symbol: 'BTC', price: 0, change: 0 },
  { symbol: 'ETH', price: 0, change: 0 },
  { symbol: 'BNB', price: 0, change: 0 },
  { symbol: 'SOL', price: 0, change: 0 },
  { symbol: 'XRP', price: 0, change: 0 },
  { symbol: 'ADA', price: 0, change: 0 },
  { symbol: 'DOGE', price: 0, change: 0 },
  { symbol: 'DOT', price: 0, change: 0 },
]
let tickerBuilt = false
let tickerFlushTimer = null    // 限频刷新定时器
let pendingTickerUpdates = {}  // 暂存待更新数据

// ── 无缝滚动：纯 CSS animation 方案（固定宽度容器，永不变形） ──
// 核心改进：给 .ticker-price 用固定宽度容器，价格文本更新不会改变 DOM 布局宽度
// 这样 CSS @keyframes 的移动距离始终精确，无需在运行中重新测量

function buildTickerDOM() {
  const track = tickerTrack.value
  if (!track || tickerBuilt) return

  const itemsHTML = tickerCoins.map(c => `<div class="ticker-item"><span class="ticker-symbol">${c.symbol}</span><span class="ticker-price" data-sym="${c.symbol}">$0.00</span><span class="ticker-change" data-sym-chg="${c.symbol}">0.00%</span></div>`).join('')

  // 放 4 份内容：确保在任何屏幕宽度下都能无缝循环
  track.innerHTML = `<div class="ticker-content">${itemsHTML}</div><div class="ticker-content" aria-hidden="true">${itemsHTML}</div><div class="ticker-content" aria-hidden="true">${itemsHTML}</div><div class="ticker-content" aria-hidden="true">${itemsHTML}</div>`
  tickerBuilt = true
}

function flushTickerUpdates() {
  const track = tickerTrack.value
  if (!track) return

  for (const [symbol, data] of Object.entries(pendingTickerUpdates)) {
    const priceStr = '$' + fmtNum(data.price, data.price < 1 ? 4 : 2)
    const changeStr = (data.change >= 0 ? '+' : '') + data.change.toFixed(2) + '%'
    const isUp = data.change >= 0

    track.querySelectorAll(`[data-sym="${symbol}"]`).forEach(el => {
      el.textContent = priceStr
    })
    track.querySelectorAll(`[data-sym-chg="${symbol}"]`).forEach(el => {
      el.textContent = changeStr
      el.style.color = isUp ? '#3fb950' : '#f85149'
      el.style.backgroundColor = isUp ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)'
    })
  }
  pendingTickerUpdates = {}
  tickerFlushTimer = null
}

function remeasureAndSetAnimation() {
  // 不需要重新测量——.ticker-price-box 固定宽度保证布局稳定
}

function scheduleTickerUpdate(symbol, price, change) {
  pendingTickerUpdates[symbol] = { price, change }
  if (!tickerFlushTimer) {
    tickerFlushTimer = setTimeout(flushTickerUpdates, 2000)
  }
}

// 格式化数字（滚动条专用）
function fmtNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '--'
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

// 启动滚动动画
function startTickerAnimation() {
  const track = tickerTrack.value
  if (!track || !tickerBuilt) return

  // 测量单份内容宽度
  void track.offsetWidth  // 强制 reflow
  const contents = track.querySelectorAll('.ticker-content')
  if (contents.length < 2) return
  const r1 = contents[0].getBoundingClientRect()
  const r2 = contents[1].getBoundingClientRect()
  const w = r2.left - r1.left
  if (w < 50) return

  // 设置 CSS 变量：移动 2 份内容宽度（4 份内容中前 2 份 = 一个完整循环）
  track.style.setProperty('--ticker-w', w + 'px')
  // 根据宽度计算合适的动画时长（30px/s 基准速度）
  const duration = (w * 2) / 18
  track.style.setProperty('--ticker-duration', duration + 's')
  track.classList.add('ticker-animated')
}

function stopTickerAnimation() {
  const track = tickerTrack.value
  if (track) track.classList.remove('ticker-animated')
}
const fearGreedIndex = ref(50)
const fearGreedLabel = computed(() => {
  const val = fearGreedIndex.value
  if (val <= 25) return '极度恐惧'
  if (val <= 45) return '恐惧'
  if (val <= 55) return '中性'
  if (val <= 75) return '贪婪'
  return '极度贪婪'
})
const fearGreedClass = computed(() => {
  const val = fearGreedIndex.value
  if (val <= 25) return 'extreme-fear'
  if (val <= 45) return 'fear'
  if (val <= 55) return 'neutral'
  if (val <= 75) return 'greed'
  return 'extreme-greed'
})
const fearGreedEmoji = computed(() => {
  const val = fearGreedIndex.value
  if (val <= 25) return '😱'
  if (val <= 45) return '😰'
  if (val <= 55) return '😐'
  if (val <= 75) return '😊'
  return '🤑'
})

// 格式化数字（通用，Dashboard 其他地方也用）
function formatNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '--'
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

// ─── WebSocket 实时数据回调 ───

function onTicker(data) {
  if (data && data.price && data.symbol) {
    const symbol = data.symbol.replace('-USDT', '')
    const coin = tickerCoins.find(c => c.symbol === symbol)
    if (coin) {
      coin.price = data.price
      if (data.change_24h !== undefined) coin.change = data.change_24h
      // 限频更新 DOM，避免打断 CSS 动画
      scheduleTickerUpdate(symbol, data.price, data.change_24h ?? coin.change)
    }
    // BTC-USDT 实时价格同步到全局状态，保证市场状态和滚动条价格一致
    if (symbol === 'BTC') btcPrice.value = data.price
  }
}

function onAccount(data) {
  if (data && data.total_equity !== undefined) {
    accountBalance.value = data.total_equity
    if (data.total_unrealized_pnl !== undefined) {
      unrealizedPnl.value = data.total_unrealized_pnl
    }
    if (data.details) {
      currencies.value = data.details
    }
  }
}

function onPosition(data) {
  if (data && data.positions) {
    positions.value = data.positions
  }
}

function onTrade(data) {
  if (data) {
    // 新成交推送到最近交易列表头部
    recentTrades.value.unshift({
      id: Date.now(),
      side: data.side === 'buy' ? '买入' : '卖出',
      symbol: data.symbol,
      price: data.price ? '$' + formatNum(data.price) : '--',
      pnl: null,
    })
    if (recentTrades.value.length > 10) {
      recentTrades.value = recentTrades.value.slice(0, 10)
    }
  }
}

function onSignal(data) {
  // 策略信号可以触发 Dashboard 数据刷新
  if (data && (data.signal === 'open_long' || data.signal === 'open_short' ||
      data.signal === 'close_long' || data.signal === 'close_short')) {
    // 信号触发后刷新持仓和账户
    fetchOverview()
  }
}

async function fetchOverview() {
  try {
    const res = await api.get('/dashboard/overview')
    hasApiKey.value = res.has_api_key

    // 更新币种价格
    if (res.prices) {
      for (const [symbol, data] of Object.entries(res.prices)) {
        // 后端返回 "BTCUSDT"，需要提取币种名（去掉 USDT 后缀）
        let coinSymbol = symbol
        if (symbol.endsWith('USDT')) {
          coinSymbol = symbol.slice(0, -4) // "BTCUSDT" -> "BTC"
        } else {
          coinSymbol = symbol.replace('-USDT-SWAP', '').replace('-USDT', '')
        }
        const coin = tickerCoins.find(c => c.symbol === coinSymbol)
        if (coin && data.price > 0) {
          coin.price = data.price
          coin.change = data.change_24h || 0
          scheduleTickerUpdate(coinSymbol, data.price, coin.change)
        }
      }
      // 始终立即刷新一次，确保价格和宽度在动画启动前就正确
      flushTickerUpdates()
    }

    // 更新恐惧贪婪指数
    if (res.fear_greed_index !== undefined) {
      fearGreedIndex.value = res.fear_greed_index
    }

    // 账户余额
    if (res.account_balance !== null) {
      accountBalance.value = res.account_balance
      if (res.unrealized_pnl !== null) {
        unrealizedPnl.value = res.unrealized_pnl
      }
    }

    // 持仓
    positions.value = res.positions || []

    // 资金账户
    if (res.funding_balance !== null) {
      fundingBalance.value = res.funding_balance
    }

    // 币种明细
    currencies.value = res.currencies || []

    // 策略统计
    runningStrategies.value = res.running_strategies ?? 0
    totalStrategyProfit.value = res.total_strategy_profit ?? 0
  } catch (e) {
    console.error('Dashboard overview error:', e)
  }
}


function renderPnlChart(data) {
  if (!pnlChartRef.value) return
  if (!pnlChart) {
    pnlChart = echarts.init(pnlChartRef.value)
  }
  // 动态读取主题CSS变量
  const cs = getComputedStyle(document.documentElement)
  const textMuted = cs.getPropertyValue('--text-muted').trim() || '#86909c'
  const borderPrimary = cs.getPropertyValue('--border-primary').trim() || '#e5e6eb'
  if (data.length === 0) {
    pnlChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: textMuted, fontSize: 14 } },
      xAxis: { show: false }, yAxis: { show: false }, series: []
    })
    return
  }
  const dates = data.map(d => d.date)
  const values = data.map(d => d.equity)
  pnlChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const p = params[0]
        return `${p.axisValue}<br/>权益: <b>$${formatNum(p.value)}</b>`
      }
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11, color: textMuted }, axisLine: { lineStyle: { color: borderPrimary } } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11, color: textMuted, formatter: v => '$' + (v >= 1000 ? (v/1000).toFixed(1) + 'k' : v.toFixed(0)) }, splitLine: { lineStyle: { color: borderPrimary } } },
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
  })
}

async function fetchRecentTrades() {
  try {
    const res = await api.get('/dashboard/recent_trades', { params: { limit: 10 } })
    recentTrades.value = res.trades || []
  } catch (e) {
    console.error('Recent trades error:', e)
  }
}

async function fetchRobotsSummary() {
  robotsLoading.value = true
  try {
    const res = await api.get('/robots/dashboard/summary')
    robotsData.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('Robots summary error:', e)
    robotsData.value = []
  } finally {
    robotsLoading.value = false
  }
}

function handleResize() {
  pnlChart?.resize()
}

function onThemeChange() {
  // 主题变更后延迟重绘图表，等待CSS变量生效
  setTimeout(() => {
  }, 100)
}

// ─── API 配置管理 ───

async function loadApiConfig() {
  try {
    const res = await api.get('/settings/api')
    // 注册链接（无论是否绑定API都加载）
    registerUrls.value = {
      bitget: res.bitget_register_url || '',
    }
    if (res.key) {
      apiConfig.value.key = res.key
      apiConfig.value.secret = res.secret ? '••••••••' : ''
      apiConfig.value.passphrase = res.passphrase ? '••••••••' : ''
      apiConfig.value.bitget_uid = res.bitget_uid || ''
      hasApiKey.value = true
      localStorage.setItem('bitget_bound', '1')
      if (res.bitget_uid) {
        localStorage.setItem('bitget_bound_uid', res.bitget_uid)
      }
    } else {
      hasApiKey.value = false
      localStorage.removeItem('bitget_bound')
      localStorage.removeItem('bitget_bound_uid')
    }
  } catch (e) {
    console.error('加载API配置失败:', e)
  }
}

async function saveApiConfig() {
  savingApi.value = true
  try {
    const res = await api.post('/settings/api', {
      key: apiConfig.value.key,
      secret: apiConfig.value.secret,
      passphrase: apiConfig.value.passphrase,
      sandbox: apiConfig.value.sandbox,
    })
    ElMessage.success('API 配置已保存')
    // 更新UID显示
    if (res.okx_uid) {
      apiConfig.value.okx_uid = res.okx_uid
      ElMessage.success(`OKX UID 已自动获取: ${res.okx_uid}`)
    }
    testResult.value = null
    // 重新加载账户数据
    await fetchOverview()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingApi.value = false
  }
}

async function testConnection() {
  testingApi.value = true
  testResult.value = null
  try {
    const res = await api.post('/settings/test-connection')
    testResult.value = {
      success: true,
      message: `连接成功! 账户权益: $${res.equity?.toLocaleString() || '0'}`,
    }
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    testResult.value = {
      success: false,
      message: `连接失败: ${detail}`,
    }
  } finally {
    testingApi.value = false
  }
}

async function refreshUid() {
  refreshingUid.value = true
  try {
    const res = await api.post('/settings/refresh-uid')
    apiConfig.value.okx_uid = res.okx_uid
    ElMessage.success(`OKX UID 已刷新: ${res.okx_uid}`)
  } catch (e) {
    ElMessage.error('刷新失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    refreshingUid.value = false
  }
}

async function unbindApi() {
  try {
    await ElMessageBox.confirm(
      '确定要解除Bitget API绑定吗？解除后需要重新配置API Key。',
      '确认解除绑定',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    // 清空API配置
    apiConfig.value = {
      key: '',
      secret: '',
      passphrase: '',
      bitget_uid: '',
    }
    hasApiKey.value = false
    localStorage.removeItem('bitget_bound')
    localStorage.removeItem('bitget_bound_uid')
    testResult.value = null

    // 调用后端清空配置
    await api.post('/settings/bitget_api', {
      key: '',
      secret: '',
      passphrase: '',
    })

    ElMessage.success('已解除Bitget API绑定')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('解除绑定失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

// ─── 交易所绑定管理 ───

function showBindDialog(exchange) {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请登录后再操作')
    return
  }
  if (exchange === 'bitget') {
    bindForm.value = {
      key: '',
      secret: '',
      passphrase: '',
    }
    bindDialogVisible.value = true
  } else {
    ElMessage.info(`${exchange.toUpperCase()} 绑定功能即将上线`)
  }
}

async function confirmBind() {
  if (!bindForm.value.key || !bindForm.value.secret || !bindForm.value.passphrase) {
    ElMessage.warning('请填写完整的 API Key、Secret Key 和 Passphrase')
    return
  }

  bindLoading.value = true
  try {
    const res = await api.post('/settings/bitget_api', {
      key: bindForm.value.key,
      secret: bindForm.value.secret,
      passphrase: bindForm.value.passphrase,
    })

    // 更新配置状态
    apiConfig.value.key = bindForm.value.key
    apiConfig.value.secret = '••••••••'
    apiConfig.value.passphrase = '••••••••'
    if (res.bitget_uid) {
      apiConfig.value.bitget_uid = res.bitget_uid
    }
    hasApiKey.value = true
    localStorage.setItem('bitget_bound', '1')
    if (res.bitget_uid) {
      localStorage.setItem('bitget_bound_uid', res.bitget_uid)
    }

    bindDialogVisible.value = false
    ElMessage.success('Bitget API 绑定成功')
    if (res.bitget_uid) {
      ElMessage.success(`Bitget UID: ${res.bitget_uid}`)
    }

    // 刷新账户数据
    await fetchOverview()
  } catch (e) {
    console.error('Bitget绑定错误:', e)
    const errorDetail = e.response?.data?.detail || e.message
    const statusCode = e.response?.status || '未知'
    const errorInfo = `状态码: ${statusCode}\n错误: ${errorDetail}\n请求URL: /api/settings/bitget_api\n请求方法: POST`
    ElMessageBox.alert(errorInfo, '绑定失败详情', {
      confirmButtonText: '确定',
      type: 'error',
    })
  } finally {
    bindLoading.value = false
  }
}

async function unbindExchange(exchange) {
  if (exchange === 'bitget') {
    await unbindApi()
  } else {
    ElMessage.info(`${exchange.toUpperCase()} 解绑功能即将上线`)
  }
}

onMounted(async () => {
  // 先加载配置（快速，设置注册按钮和状态）
  await loadApiConfig()

  // 初始化滚动条
  buildTickerDOM()

  // 加载站点Logo（用于AI分析室水印）
  fetchSiteLogo()

  // 以下全部并行执行，不互相等待，不阻塞页面
  fetchOverview()
  fetchHotActivities()
  fetchRecentTrades()
  fetchRobotsSummary()
  fetchBtcPrice()
  startTickerAnimation()
  loadAnalystConfig()
  loadAiChatHistory()
  loadJudgeRecords()
  loadFeaturedStrategies()
  loadAvailableStrategies()
  updateCountdown()
  countdownTimer = setInterval(updateCountdown, 1000)

  window.addEventListener('resize', handleResize)
  // 监听主题变更，重绘图表
  window.addEventListener('theme-change', onThemeChange)

  // 注册 WebSocket 实时数据
  wsOn('ticker', onTicker)
  wsOn('account', onAccount)
  wsOn('position', onPosition)
  wsOn('trade', onTrade)
  wsOn('signal', onSignal)

  // 兜底定时刷新（WS断线时每60秒刷新一次概览）
  dashboardTimer = setInterval(async () => {
    if (!wsConnected.value) {
      await fetchOverview()
      await fetchRecentTrades()
    }
  }, 60000)
})

let dashboardTimer = null

onBeforeUnmount(() => {
  stopTickerAnimation()
  if (dashboardTimer) clearInterval(dashboardTimer)
  if (countdownTimer) clearInterval(countdownTimer)
  if (tickerFlushTimer) clearTimeout(tickerFlushTimer)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('theme-change', onThemeChange)
  pnlChart?.dispose()

  // 注销 WebSocket 事件
  wsOff('ticker', onTicker)
  wsOff('account', onAccount)
  wsOff('position', onPosition)
  wsOff('trade', onTrade)
  wsOff('signal', onSignal)
})
</script>

<style scoped>
.dashboard-page { min-height: 100%; }

/* 三栏布局：左中列 + 右列 */
.dashboard-three-col {
  display: flex;
  gap: 20px;
}

.left-center-col {
  flex: 1;
  min-width: 0;
}

.right-col {
  width: 20%;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 实时价格滚动条 */
.price-ticker {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 0;
  margin-bottom: 20px;
  display: flex;
  overflow: hidden;
}

/* 恐惧贪婪指数（固定在左边） */
.fear-greed-fixed {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(90deg, rgba(88, 166, 255, 0.08) 0%, rgba(88, 166, 255, 0.02) 100%);
  border-right: 2px solid var(--border-secondary);
}

.fgi-icon {
  font-size: 24px;
  line-height: 1;
}

.fgi-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.fgi-value {
  font-size: 16px;
  font-weight: 800;
  line-height: 1;
}

.fgi-value.extreme-fear {
  color: #f85149;
}

.fgi-value.fear {
  color: #ff9f43;
}

.fgi-value.neutral {
  color: #8b949e;
}

.fgi-value.greed {
  color: #3fb950;
}

.fgi-value.extreme-greed {
  color: #00d26a;
}

.fgi-label {
  font-size: 10px;
  color: var(--text-muted);
}

/* 统计卡片网格 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 18px;
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: var(--card-shadow);
}

.stat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.stat-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-footer {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-up { font-size: 12px; color: #22c55e; font-weight: 600; }
.stat-down { font-size: 12px; color: #ef4444; font-weight: 600; }
.stat-period { font-size: 12px; color: var(--text-muted); }

/* 面板卡片 */
.panel-card { border-radius: 10px; }

/* 量化机器人收益 + 个人中心等高（用父级row flex stretch） */
.pair-row {
  display: flex;
  align-items: stretch;
}
.pair-row > .el-col {
  display: flex;
  flex-direction: column;
}
.pair-row .panel-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.pair-row .panel-card :deep(.el-card__body) {
  flex: 1;
}
.panel-header { display: flex; align-items: center; justify-content: space-between; }
.panel-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }

.placeholder-block {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 量化机器人摘要列表 */
.robot-summary-list {
  display: flex;
  flex-direction: column;
  flex: 1;
}

/* 热门活动 */
.hot-activity-section {
  padding: 0;
}

.hot-activity-section .panel-header {
  margin-bottom: 12px;
}

.activity-banner {
  margin-bottom: 16px;
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  background: var(--bg-card);
}

.banner-image {
  width: 100%;
  height: 200px;
  object-fit: fill;
  display: block;
  transition: transform 0.3s;
}

.banner-image:hover {
  transform: scale(1.02);
}

.banner-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--bg-hover);
  border: 1px dashed var(--border-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.title-icon {
  width: 18px;
  height: 18px;
  margin-right: 4px;
  vertical-align: -3px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  background: var(--activity-card-bg, #ffffff);
  border: 1px solid var(--border-primary);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: all 0.2s ease;
  cursor: pointer;
}

.activity-item:hover {
  border-color: var(--accent);
  border-left-width: 5px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}

.activity-item .activity-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  overflow: hidden;
}

.activity-icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-item .activity-info {
  flex: 1;
  min-width: 0;
}

.activity-item .activity-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
  margin-bottom: 3px;
}

.activity-item .activity-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.activity-item .activity-status {
  font-size: 11px;
  font-weight: 500;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  line-height: 1.5;
}

.activity-status.status-active {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
}

.activity-status.status-upcoming {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.08);
}

.activity-status.status-soon {
  color: var(--text-muted);
  background: var(--bg-hover);
}

.activity-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  line-height: 1.4;
  letter-spacing: 0.5px;
}

.badge-hot {
  color: #fff;
  background: linear-gradient(135deg, #f85149, #ff6b35);
}

.badge-new {
  color: #fff;
  background: linear-gradient(135deg, #409eff, #53a8ff);
}

/* 骨架屏 */
.activity-skeleton {
  pointer-events: none;
}

.skeleton-icon,
.skeleton-line {
  background: linear-gradient(90deg, var(--border-primary) 25%, var(--bg-hover) 50%, var(--border-primary) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 6px;
}

.skeleton-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-line {
  height: 12px;
}

.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-90 { width: 90%; }
.skeleton-line.w-35 { width: 35%; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 市场状态仪表盘 */
.market-regime-section {
  margin-top: 16px;
}

.regime-update-tag {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
  letter-spacing: 1.5px;
  animation: regimePulse 2s ease-in-out infinite;
}

@keyframes regimePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.regime-body {
  border-radius: 16px;
  padding: 18px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  position: relative;
  overflow: hidden;
  transition: border-color 0.5s;
}

.regime-body::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -25%;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: var(--rc, #86909c);
  opacity: 0.05;
  transition: background 0.6s;
  pointer-events: none;
}

.regime-body--strong_trend { --rc: #00b96b; border-color: rgba(0,185,107,0.25); }
.regime-body--trending { --rc: #00b96b; border-color: rgba(0,185,107,0.2); }
.regime-body--weak_trend { --rc: #f5a623; border-color: rgba(245,166,35,0.25); }
.regime-body--volatile { --rc: #ff4d4f; border-color: rgba(255,77,79,0.25); }
.regime-body--ranging { --rc: #86909c; }

.regime-gauge-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.regime-arc {
  width: 100%;
  max-width: 180px;
  height: auto;
  display: block;
}

.regime-score-text {
  font-variant-numeric: tabular-nums;
}

.regime-status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.regime-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  width: fit-content;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  transition: all 0.4s;
}

.badge--strong_trend { background: linear-gradient(135deg, #00b96b, #34d399); }
.badge--trending { background: linear-gradient(135deg, #00b96b, #6ee7b7); }
.badge--weak_trend { background: linear-gradient(135deg, #f5a623, #fbbf24); }
.badge--volatile { background: linear-gradient(135deg, #ff4d4f, #f87171); }
.badge--ranging { background: linear-gradient(135deg, #64748b, #94a3b8); }

.regime-direction {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dir-arrow {
  width: 13px;
  height: 13px;
}

.dir-arrow.dir--up { fill: #22c55e; }
.dir-arrow.dir--down { fill: #ef4444; }

.dir-text--up { color: #22c55e; font-size: 12px; font-weight: 600; }
.dir-text--down { color: #ef4444; font-size: 12px; font-weight: 600; }

.regime-tip {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 12px;
}

.regime-indicators {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 14px;
}

.indicator {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.indicator-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.indicator-name {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.indicator-val {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.indicator-track {
  height: 3px;
  background: var(--border-primary);
  border-radius: 2px;
  overflow: hidden;
}

.indicator-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s cubic-bezier(.4,0,.2,1);
}

.regime-bar {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border-radius: 10px;
  padding: 8px 0;
  border: 1px solid var(--border-primary);
}

.bar-cell {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.bar-label {
  font-size: 9px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.bar-price {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.bar-chg {
  font-size: 10px;
  font-weight: 600;
}

.bar-val {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.bar-divider {
  width: 1px;
  height: 24px;
  background: var(--border-primary);
  flex-shrink: 0;
}

/* AI分析按钮 */
.ai-analyze-section {
  margin-top: 16px;
}

/* AI分析加载动画 */
.ai-loading-overlay {
  margin-top: 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 10px;
  padding: 20px;
  animation: fadeSlideUp 0.3s ease;
}

.ai-loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.ai-loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ai-loading-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.ai-loading-tips {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-secondary);
}

.ai-loading-tips span {
  padding: 4px 8px;
  background: var(--bg-primary);
  border-radius: 6px;
  animation: pulse 1.5s ease-in-out infinite;
}

.ai-loading-tips span:nth-child(2) { animation-delay: 0.3s; }
.ai-loading-tips span:nth-child(3) { animation-delay: 0.6s; }

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.ai-analyze-btn {
  width: 100%;
  height: 40px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  letter-spacing: 0.3px;
  transition: all 0.3s;
}

.ai-analyze-btn:hover {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
}

.ai-analyze-btn .btn-icon {
  font-size: 16px;
}

/* AI快捷分析结果 */
.ai-quick-result {
  margin-top: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 12px;
  animation: fadeSlideUp 0.3s ease;
  position: relative;
}

.ai-quick-result.result-streaming {
  border-color: rgba(99, 102, 241, 0.3);
}

@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.quick-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.7;
  word-break: break-all;
}

.qa-cursor {
  animation: blink 0.7s step-end infinite;
  color: #6366f1;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* AI判断追踪 */
.ai-judge-tracker {
  margin-top: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 12px;
}

.tracker-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.tracker-icon {
  font-size: 14px;
}

.tracker-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tracker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-card);
  border-radius: 8px;
  font-size: 12px;
}

.tracker-time {
  color: var(--text-muted);
  min-width: 70px;
}

.tracker-dir {
  font-weight: 600;
  min-width: 40px;
}

.tracker-dir.dir-long { color: #22c55e; }
.tracker-dir.dir-short { color: #ef4444; }
.tracker-dir.dir-hold { color: #f5a623; }

.tracker-price {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  flex: 1;
}

.tracker-result {
  font-size: 14px;
}

.tracker-result.result-correct { color: #22c55e; }
.tracker-result.result-wrong { color: #ef4444; }

/* 个人中心 */
.personal-center { padding: 10px 0; display: flex; flex-direction: column; flex: 1; min-height: 240px; }
.api-config-section { display: flex; flex-direction: column; gap: 16px; }
.config-item { display: flex; align-items: center; gap: 20px; }
.config-label {
  min-width: 90px;
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}
.config-value { display: flex; align-items: center; flex: 1; }
.config-actions { display: flex; gap: 10px; margin-top: 10px; }
.test-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 10px;
}
.test-result.success { background: #e8ffea; color: #00b42a; }
.test-result.error { background: #ffece8; color: #f53f3f; }

/* 交易所绑定卡片 */
.exchange-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  flex: 1;
  align-content: stretch;
}

.exchange-cards.single-bound {
  grid-template-columns: 1fr;
  max-width: 400px;
}

.exchange-card {
  background: var(--bg-hover);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.exchange-card:hover {
  background: var(--bg-card-hover);
}

.exchange-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.exchange-header .exchange-logo {
  flex-shrink: 0;
}

.exchange-logo {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.exchange-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.exchange-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 操作按钮行 */
.exchange-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}
.exchange-actions .el-button {
  flex: 1;
  min-width: 0;
  height: 32px;
  font-size: 14px;
}

/* 注册按钮 */
.register-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  padding: 0 15px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  background: #fff;
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
}
.register-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 提示文字 */
.exchange-tip {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
  font-size: 13px;
  color: #e74c3c;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tip-icon {
  width: 16px;
  height: 16px;
  vertical-align: middle;
}

.okx-logo {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  overflow: hidden;
}

.exchange-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.bitget-logo {
  background: linear-gradient(135deg, #0052ff 0%, #0066ff 100%);
}

.htx-logo {
  background: linear-gradient(135deg, #00a651 0%, #00c853 100%);
}

.exchange-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-size: 12px;
  color: var(--text-muted);
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 绑定后的统计网格 */
.bound-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--border-secondary);
}

.bound-stat {
  background: var(--bg-secondary);
  border-radius: 6px;
  padding: 8px 10px;
}

.bound-stat-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.bound-stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.bound-stat-value.accent {
  color: #409eff;
}

.bound-unbind {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 8px;
  background: var(--red-light);
  border: 1px solid rgba(244, 63, 94, 0.3);
  border-radius: 6px;
  color: var(--red);
  cursor: pointer;
  transition: all 0.2s;
  padding: 6px 16px;
  font-size: 13px;
}

.bound-unbind:hover {
  background: rgba(244, 63, 94, 0.15);
  border-color: var(--red);
}

.unbind-icon {
  font-size: 14px;
  line-height: 1;
}

.unbind-text {
  font-size: 14px;
  font-weight: 700;
}

.stat-loading {
  color: var(--text-disabled) !important;
  font-size: 14px !important;
  font-weight: 400 !important;
}

/* 图表区域 */

/* 账户资产 */
.asset-list { min-height: 280px; }
.asset-empty {
  height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; color: var(--text-muted);
}
.asset-empty p { margin: 10px 0; font-size: 13px; color: var(--text-muted); }

.asset-total { padding: 4px 0 10px; }
.asset-total-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.asset-total-value { font-size: 26px; font-weight: 700; color: var(--text-primary); }
.asset-pnl { margin-top: 4px; font-size: 12px; }

.asset-divider { height: 1px; background: var(--border-secondary); margin: 8px 0; }

.asset-funding { padding: 4px 0 8px; }

.asset-coins { max-height: 160px; overflow-y: auto; }
.asset-coin {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; border-bottom: 1px solid var(--border-primary);
}
.asset-coin:last-child { border-bottom: none; }
.coin-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.coin-right { text-align: right; }
.coin-equity { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.coin-available { font-size: 11px; color: var(--text-muted); margin-left: 8px; }

/* 持仓盈亏色 */
.pnl-up { color: #16a34a; font-weight: 500; }
.pnl-down { color: #dc2626; font-weight: 500; }
.val-up { color: #ef5350; }
.val-down { color: #26a69a; }

/* 量化机器人面板 */
.robot-panel .panel-header {
  position: relative;
}

.robot-title-icon {
  font-size: 16px;
  margin-right: 2px;
}

.robot-view-all {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.robot-view-all:hover {
  color: var(--accent);
}

.view-all-arrow {
  font-size: 14px;
  transition: transform 0.2s;
}

.robot-view-all:hover .view-all-arrow {
  transform: translateX(3px);
}

/* ─── 量化机器人新UI ─── */
.robot-stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon { font-size: 28px; }

.stat-info { flex: 1; }

.stat-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}

.stat-unit { font-size: 12px; font-weight: 400; opacity: 0.7; }

.stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

.stat-card--running { border-color: #22c55e33; background: linear-gradient(135deg, var(--bg-secondary), #22c55e0a); }
.stat-card--running .stat-value { color: #22c55e; }

.stat-card--profit { border-color: #22c55e33; }
.stat-card--profit .stat-value { color: #22c55e; }

.stat-card--loss { border-color: #ef444433; }
.stat-card--loss .stat-value { color: #ef4444; }

.stat-card--winrate { border-color: #409eff33; }
.stat-card--winrate .stat-value { color: #409eff; }

/* ─── 领奖台样式 ─── */
.podium-section { margin-bottom: 16px; }

/* === 第一名 王者卡片 === */
.podium-gold {
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 12px;
  border: 1.5px solid rgba(251, 191, 36, 0.2);
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.podium-gold:hover {
  transform: translateY(-3px) scale(1.005);
  box-shadow: 0 16px 40px rgba(251, 191, 36, 0.12), 0 0 80px rgba(251, 191, 36, 0.04);
  border-color: rgba(251, 191, 36, 0.4);
}
/* 金色光晕 */
.pg-glow {
  position: absolute;
  top: -60px; right: -60px;
  width: 180px; height: 180px;
  background: radial-gradient(circle, rgba(251, 191, 36, 0.1) 0%, transparent 65%);
  pointer-events: none;
}
/* 边框流光动画 */
.pg-border-shine {
  position: absolute;
  top: -1px; left: -100%;
  width: 60%; height: 2px;
  background: linear-gradient(90deg, transparent, rgba(251, 191, 36, 0.6), transparent);
  animation: borderSweep 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes borderSweep {
  0% { left: -60%; }
  100% { left: 120%; }
}
.pnl-bg-up { background: linear-gradient(145deg, var(--bg-secondary) 0%, rgba(34, 197, 94, 0.03) 100%); }
.pnl-bg-down { background: linear-gradient(145deg, var(--bg-secondary) 0%, rgba(239, 68, 68, 0.03) 100%); }

/* 顶部区域 */
.pg-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; position: relative; z-index: 1; }
.pg-left { display: flex; align-items: center; gap: 14px; }
.pg-avatar-box { position: relative; flex-shrink: 0; }
.pg-avatar { width: 52px; height: 52px; border-radius: 16px; object-fit: cover; border: 2px solid rgba(251, 191, 36, 0.3); box-shadow: 0 4px 12px rgba(251, 191, 36, 0.1); }
.pg-rank-badge { position: absolute; bottom: -5px; left: -5px; font-size: 8px; font-weight: 900; background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #fff; padding: 1px 5px; border-radius: 6px; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(251, 191, 36, 0.3); }
.pg-crown { position: absolute; top: -12px; right: -8px; width: 22px; height: 22px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }

.pg-info { min-width: 0; }
.pg-name { font-size: 18px; font-weight: 900; color: var(--text-primary); letter-spacing: 0.5px; }
.pg-sub { display: flex; align-items: center; gap: 6px; margin-top: 5px; flex-wrap: wrap; }
.pg-chip { font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
.pg-chip--gold { background: rgba(251, 191, 36, 0.12); color: #f59e0b; }
.pg-chip--strat { background: rgba(96, 165, 250, 0.12); color: #60a5fa; }
.pg-chip--live { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.pg-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: currentColor; animation: pulse 2s infinite; }
.pg-dot--gold { background: #f59e0b; }

/* 盈亏区域 */
.pg-right { text-align: right; flex-shrink: 0; }
.pg-pnl-wrap { display: flex; align-items: baseline; justify-content: flex-end; }
.pg-pnl-sign { font-size: 18px; font-weight: 700; opacity: 0.6; margin-right: 1px; }
.pg-pnl-num { font-size: 32px; font-weight: 900; font-variant-numeric: tabular-nums; letter-spacing: -1px; line-height: 1; }
.pg-pnl-label { font-size: 10px; color: var(--text-muted); margin-top: 4px; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 500; }
.pnl-up { color: #22c55e; }
.pnl-down { color: #ef4444; }
.pnl-u { font-size: 11px; font-weight: 500; opacity: 0.6; margin-left: 2px; }

/* 分隔线 */
.pg-divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(251, 191, 36, 0.15), transparent); margin-bottom: 16px; position: relative; z-index: 1; }

/* 指标区域 */
.pg-metrics { display: grid; grid-template-columns: auto 1fr repeat(4, 1fr); gap: 12px; align-items: center; position: relative; z-index: 1; }

/* 胜率环形图 */
.gm-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.gm-ring { position: relative; width: 48px; height: 48px; }
.gm-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.gm-ring-bg { color: rgba(255,255,255,0.06); }
.gm-ring-fg { transition: stroke-dasharray 0.6s ease; }
.gm-ring--green .gm-ring-fg { color: #22c55e; }
.gm-ring--blue .gm-ring-fg { color: #60a5fa; }
.gm-ring-val { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800; color: var(--text-primary); }
.gm-text { font-size: 9px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.3px; }

/* 月化进度条 */
.gm-bar-item { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.gm-bar-label { font-size: 9px; color: var(--text-muted); font-weight: 500; }
.gm-bar-track { height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }
.gm-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.gm-bar--up { background: linear-gradient(90deg, #22c55e, #4ade80); }
.gm-bar--down { background: linear-gradient(90deg, #ef4444, #f87171); }
.gm-bar-val { font-size: 13px; font-weight: 800; font-variant-numeric: tabular-nums; }
.gm-val--green { color: #22c55e; }
.gm-val--red { color: #ef4444; }

/* 数字指标 */
.gm-num-item { display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 8px 0; border-radius: 10px; background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.03); }
.gm-num-val { font-size: 15px; font-weight: 800; color: var(--text-primary); font-variant-numeric: tabular-nums; line-height: 1; }
.gm-num-label { font-size: 9px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.2px; }

/* === 第二三名 并排卡片 === */
.podium-row-bottom { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.podium-small {
  border-radius: 14px;
  padding: 14px;
  border: 1px solid var(--border-primary);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}
.podium-small:hover { transform: translateY(-2px); }
.podium-silver { border-top: 2px solid #94a3b8; }
.podium-silver:hover { box-shadow: 0 8px 24px rgba(148, 163, 184, 0.1); border-color: rgba(148, 163, 184, 0.35); }
.podium-bronze { border-top: 2px solid #d97706; }
.podium-bronze:hover { box-shadow: 0 8px 24px rgba(217, 119, 6, 0.1); border-color: rgba(217, 119, 6, 0.35); }

.ps-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.ps-avatar-box { position: relative; flex-shrink: 0; }
.ps-avatar { width: 34px; height: 34px; border-radius: 10px; object-fit: cover; border: 1.5px solid var(--border-primary); }
.ps-rank { position: absolute; bottom: -4px; left: -4px; font-size: 8px; font-weight: 800; background: var(--bg-secondary); border: 1px solid var(--border-primary); padding: 0 4px; border-radius: 5px; color: var(--text-muted); }
.podium-silver .ps-rank { color: #94a3b8; border-color: rgba(148, 163, 184, 0.3); }
.podium-bronze .ps-rank { color: #d97706; border-color: rgba(217, 119, 6, 0.3); }
.ps-medal { position: absolute; top: -8px; right: -6px; width: 16px; height: 16px; object-fit: contain; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2)); }

.ps-mid { flex: 1; min-width: 0; }
.ps-name { font-size: 13px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ps-meta-row { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
.ps-runtime { font-size: 10px; color: var(--text-muted); display: inline-flex; align-items: center; gap: 3px; }
.ps-clock { font-size: 10px; }
.ps-live { font-size: 10px; color: #22c55e; font-weight: 600; display: inline-flex; align-items: center; gap: 3px; }

.ps-pnl { font-size: 17px; font-weight: 800; font-variant-numeric: tabular-nums; flex-shrink: 0; line-height: 1; }
.ps-pnl-sign { opacity: 0.6; }

.ps-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
.ps-cell { display: flex; justify-content: space-between; padding: 3px 0; }
.ps-cl { font-size: 10px; color: var(--text-muted); }
.ps-cv { font-size: 11px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }

.robot-cards-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.robot-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 14px;
  transition: all 0.2s;
}

.robot-card:hover { border-color: var(--accent-color); transform: translateY(-2px); }

.robot-card--running { border-left: 3px solid #22c55e; }

.rc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.rc-avatar {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.rc-emoji { font-size: 20px; }

.rc-status-dot {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 10px;
  height: 10px;
  background: #22c55e;
  border-radius: 50%;
  border: 2px solid var(--bg-secondary);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.rc-info { flex: 1; min-width: 0; }

.rc-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }

.rc-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }

.rc-badge {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--bg-hover);
  border-radius: 4px;
  color: var(--text-muted);
}

.rc-monthly { font-size: 12px; font-weight: 600; }
.rc-monthly.up { color: #22c55e; }
.rc-monthly.down { color: #ef4444; }

.rc-pnl { text-align: right; }
.rc-pnl-value { font-size: 18px; font-weight: 700; }
.rc-pnl-unit { font-size: 12px; opacity: 0.7; }
.rc-pnl.pnl-up .rc-pnl-value { color: #22c55e; }
.rc-pnl.pnl-down .rc-pnl-value { color: #ef4444; }

.rc-footer {
  display: flex;
  gap: 16px;
  padding-top: 10px;
  border-top: 1px solid var(--border-primary);
}

.rc-stat { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.rc-stat-icon { font-size: 14px; }
.rc-stat-val { font-weight: 600; }
.rc-stat-val.high-win { color: #22c55e; }

/* ─── 策略设置弹窗 ─── */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.mode-switch { display: flex; gap: 0; }
.mode-switch .el-button { border-radius: 0; }
.mode-switch .el-button:first-child { border-radius: 4px 0 0 4px; }
.mode-switch .el-button:last-child { border-radius: 0 4px 4px 0; }

.simple-settings { padding: 10px 0; }
.hint-label { margin-left: 8px; font-size: 12px; color: var(--text-muted); }

.simple-tip {
  display: flex; align-items: center; gap: 6px;
  padding: 12px 16px; background: var(--accent-light);
  border-radius: 8px; color: var(--accent); font-size: 13px; margin-top: 16px;
}

.pro-settings { margin: 0 -20px; padding: 0; }
.pro-settings :deep(.el-tabs--border-card) { border: none; border-radius: 0; background: transparent; box-shadow: none; }
.pro-settings :deep(.el-tabs__header) { background: var(--bg-secondary); border-bottom: 1px solid var(--border-primary); margin: 0; padding: 0 20px; }
.pro-settings :deep(.el-tabs__nav) { border: none; }
.pro-settings :deep(.el-tabs__item) { padding: 0 20px; height: 40px; line-height: 40px; }
.pro-settings :deep(.el-tabs__content) { padding: 16px 20px; max-height: 420px; overflow-y: auto; background: transparent; border: none; }
.pro-settings :deep(.el-tab-pane) { overflow: visible; }

.tab-form { max-width: 100%; padding: 0; }
.tab-form :deep(.el-form-item) { margin-bottom: 18px; }
.tab-form :deep(.el-divider) { margin: 16px 0; }
.tab-form :deep(.el-input-number) { width: 160px; }
.tab-form :deep(.el-slider) { max-width: 320px; }

.time-range-row { display: flex; align-items: center; gap: 12px; }
.time-sep { color: var(--text-muted); font-size: 13px; }

.schedule-tip {
  display: flex; align-items: center; gap: 6px;
  padding: 12px 16px; background: var(--blue-light);
  border-radius: 8px; color: var(--blue); font-size: 13px; margin-top: 12px;
}

.no-params-tip { color: var(--text-muted); font-size: 13px; padding: 20px 0; text-align: center; }

.sqd-form .el-form-item { margin-bottom: 18px; }
.sqd-form .el-form-item__label { font-weight: 600; color: var(--text-primary); }
.sqd-form .el-slider { padding-right: 16px; }

.sqd-footer { display: flex; justify-content: flex-end; gap: 10px; }
.sqd-start-btn { min-width: 130px; font-weight: 700; }

/* ─── 精选策略卡片 ─── */
.strategy-card {
  position: relative;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 14px;
  padding: 14px 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
  transition: all 0.3s ease;
  overflow: hidden;
}
.strategy-card:hover {
  border-color: var(--accent-color);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* 顶部光效 */
.sc-glow {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  opacity: 0;
  transition: opacity 0.3s;
}
.strategy-card:hover .sc-glow { opacity: 1; }
.sc-theme-0 .sc-glow { background: linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa); }
.sc-theme-1 .sc-glow { background: linear-gradient(90deg, #f59e0b, #fbbf24, #fcd34d); }

/* 头部 */
.sc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}
.sc-title-row { display: flex; align-items: center; gap: 8px; }
.sc-icon-wrap {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
.sc-icon-0 { background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15)); }
.sc-icon-1 { background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(251,191,36,0.15)); }

.sc-title-info { display: flex; flex-direction: column; gap: 2px; }
.sc-name-row { display: flex; align-items: center; gap: 6px; }
.sc-name { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.sc-type-label { font-size: 11px; color: var(--text-muted); }

.sc-badge {
  font-size: 10px;
  padding: 1px 6px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* 收益率 */
.sc-profit-box {
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 8px;
}
.sc-profit-main { display: flex; align-items: baseline; gap: 1px; }
.sc-profit-box.profit-up { background: linear-gradient(135deg, rgba(34,197,94,0.08), rgba(34,197,94,0.03)); }
.sc-profit-box.profit-down { background: linear-gradient(135deg, rgba(239,68,68,0.08), rgba(239,68,68,0.03)); }
.sc-profit-val { font-size: 20px; font-weight: 800; line-height: 1.1; }
.sc-profit-unit { font-size: 12px; font-weight: 600; }
.sc-profit-period { font-size: 10px; color: var(--text-muted); line-height: 1; }
.sc-profit-box.profit-up .sc-profit-val,
.sc-profit-box.profit-up .sc-profit-unit { color: #22c55e; }
.sc-profit-box.profit-down .sc-profit-val,
.sc-profit-box.profit-down .sc-profit-unit { color: #ef4444; }

/* 描述 */
.sc-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 8px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 数据指标网格 */
.sc-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin-bottom: 10px;
  padding: 8px 6px;
  background: var(--bg-card);
  border-radius: 8px;
}
.sc-stat {
  text-align: center;
  padding: 4px 0;
}
.sc-stat-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}
.sc-stat-val.text-green { color: #22c55e; }
.sc-stat-val.text-red { color: #ef4444; }
.sc-stat-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}
.sc-rating {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
}
.sc-stars {
  font-size: 10px;
  color: #fbbf24;
  letter-spacing: 1px;
  line-height: 1;
}

/* 按钮 */
.sc-btn {
  width: 100%;
  height: 32px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  transition: all 0.2s;
}
.sc-btn:hover {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}
.sc-btn-icon { margin-right: 4px; }

.text-green { color: #22c55e !important; }
.text-red { color: #ef4444 !important; }

/* ─── AI分析室新UI ─── */
.ai-chat-window {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex: 1;
  position: relative;
}
/* Logo水印 - 绝对定位覆盖在内容最上层 */
.ai-chat-window::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('/static/uploads/site-logo.jpg') center/30% no-repeat;
  opacity: 0.15;
  pointer-events: none;
  z-index: 999;
}

.ai-models-bar {
  display: flex;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-primary);
}

.ai-model-tag {
  font-size: 10px;
  padding: 2px 8px 2px 6px;
  background: var(--bg-hover);
  border-radius: 10px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 3px;
}

.amt-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: #22c55e;
  display: inline-block;
}

.ai-model-tag.judge {
  background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15));
  color: #6366f1;
  border: 1px solid rgba(99,102,241,0.2);
}

/* 两栏布局 */
.ai-two-col {
  display: flex;
  gap: 12px;
  padding: 12px;
  flex: 1;
  min-height: 0;
}

.ai-col-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.ai-col-right {
  width: 45%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

/* 分析师卡片 */
.ai-analyst-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
}

.ai-analyst-card:hover {
  border-color: var(--accent-color);
  transform: translateX(2px);
}

/* 左侧彩色边条 */
.aac-color-bar {
  width: 3px;
  flex-shrink: 0;
  border-radius: 3px 0 0 3px;
}
.aac-aggressive .aac-color-bar { background: linear-gradient(180deg, #ef4444, #f97316); }
.aac-conservative .aac-color-bar { background: linear-gradient(180deg, #3b82f6, #6366f1); }
.aac-technical .aac-color-bar { background: linear-gradient(180deg, #22c55e, #10b981); }

.aac-body {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
}

.ai-ac-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.ai-ac-avatar {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}
.aac-aggressive .ai-ac-avatar { background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(249,115,22,0.12)); }
.aac-conservative .ai-ac-avatar { background: linear-gradient(135deg, rgba(59,130,246,0.12), rgba(99,102,241,0.12)); }
.aac-technical .ai-ac-avatar { background: linear-gradient(135deg, rgba(34,197,94,0.12), rgba(16,185,129,0.12)); }

.ai-ac-avatar img { width: 100%; height: 100%; border-radius: 8px; object-fit: cover; }

.ai-ac-name { font-size: 12px; font-weight: 700; color: var(--text-primary); }

.ai-ac-tag {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
  margin-left: auto;
  flex-shrink: 0;
}
.aac-aggressive .ai-ac-tag { background: rgba(239,68,68,0.1); color: #ef4444; }
.aac-conservative .ai-ac-tag { background: rgba(59,130,246,0.1); color: #3b82f6; }
.aac-technical .ai-ac-tag { background: rgba(34,197,94,0.1); color: #22c55e; }

.ai-ac-content {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 7;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 裁决卡片 */
.ai-judge-card {
  background: linear-gradient(135deg, #6366f11a, #8b5cf61a);
  border: 1px solid #6366f133;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  flex-direction: column;
  width: fit-content;
  max-width: 100%;
}

.ai-jc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.ai-jc-icon { font-size: 16px; }

.ai-jc-title { font-size: 13px; font-weight: 700; color: var(--text-primary); }

.ai-jc-content {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  flex: 1;
  overflow-y: auto;
}

/* 实时监控面板 */
.ai-live-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 10px;
}

.ai-live-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.ai-live-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.ai-live-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.ai-live-icon { font-size: 12px; }
.ai-live-val { font-weight: 600; color: var(--text-primary); }
.ai-live-item.pnl-up .ai-live-val { color: #22c55e; }
.ai-live-item.pnl-down .ai-live-val { color: #ef4444; }
.ai-live-val.dir-long { color: #22c55e; }
.ai-live-val.dir-short { color: #ef4444; }

.ai-empty-state {
  text-align: center;
  padding: 40px 20px;
}

.ai-empty-icon { font-size: 48px; margin-bottom: 12px; }
.ai-empty-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.ai-empty-desc { font-size: 12px; color: var(--text-muted); }

/* 机器人总览条 */
.robot-overview {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border-radius: 10px;
  margin-bottom: 12px;
}

.rov-item {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.rov-label {
  font-size: 11px;
  color: var(--text-muted);
}

.rov-value {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}

.rov-running { color: #22c55e; }

.rov-winrate { color: #409eff; }

.rov-divider {
  width: 1px;
  height: 30px;
  background: var(--border-primary);
  flex-shrink: 0;
}

/* 机器人列表项 */
.robot-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 10px;
  transition: all 0.2s;
  margin-bottom: 8px;
}

.robot-item:last-child {
  margin-bottom: 0;
}

.robot-item:hover {
  background: var(--bg-hover);
}

.ri-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.ri-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ri-avatar-active {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(16, 185, 129, 0.1));
}

.ri-emoji { font-size: 18px; }

.ri-info {
  flex: 1;
  min-width: 0;
}

.ri-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ri-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.ri-strategies {
  font-size: 11px;
  color: var(--text-muted);
}

.ri-dot {
  font-size: 10px;
  color: var(--border-primary);
}

.ri-monthly {
  font-size: 11px;
  font-weight: 600;
}

.ri-right {
  text-align: right;
  flex-shrink: 0;
}

.ri-pnl {
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.ri-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.ri-winrate {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.ri-winrate.win-high { color: #22c55e; }

.ri-trades {
  font-size: 11px;
  color: var(--text-muted);
}

/* 第三排：最近交易 */
.third-row-trades {
  margin-top: 20px;
}

/* 交易列表 */
.trade-list { min-height: 240px; max-height: 280px; overflow-y: auto; }
.trade-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 0; border-bottom: 1px solid var(--border-primary);
}
.trade-item:last-child { border-bottom: none; }
.trade-left { display: flex; align-items: center; gap: 8px; }
.trade-symbol { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.trade-right { text-align: right; }
.trade-price { font-size: 13px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.trade-pnl { font-size: 12px; margin-left: 8px; }

/* 响应式 */
@media (max-width: 1400px) {
  .right-col { width: 25%; }
}
@media (max-width: 1200px) {
  .dashboard-three-col {
    flex-direction: column;
  }
  .right-col {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
  }
  .right-col > * {
    flex: 1;
    min-width: 280px;
  }
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .pair-row {
    flex-direction: column;
  }
  .pair-row > .el-col {
    width: 100% !important;
    max-width: 100%;
    margin-bottom: 16px;
  }
}
@media (max-width: 900px) {
  .exchange-cards {
    flex-direction: column;
  }
  .exchange-card {
    min-width: 100%;
  }
}
@media (max-width: 768px) {
  .stat-grid { grid-template-columns: repeat(1, 1fr); }
  .fear-greed-fixed {
    flex-direction: column;
    padding: 6px 12px;
  }
  .price-ticker {
    flex-direction: column;
  }
  .banner-image {
    height: 150px;
  }
}

/* 绑定对话框 */
.bind-dialog :deep(.el-dialog) {
  border-radius: 16px !important;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15) !important;
  overflow: hidden;
  animation: bindDialogIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  transform-origin: center center;
}

@keyframes bindDialogIn {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.3);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

.bind-dialog :deep(.el-overlay) {
  animation: bindOverlayIn 0.35s ease forwards;
}

@keyframes bindOverlayIn {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

.bind-dialog :deep(.el-overlay-dialog) {
  display: flex;
  justify-content: center;
  align-items: center;
}

.bind-dialog :deep(.el-dialog__header) {
  padding: 16px 0 8px 0;
  margin: 0 16px;
}

.bind-dialog :deep(.el-dialog__headerbtn) {
  top: 16px;
  right: 8px;
  font-size: 18px;
  color: var(--text-muted);
}

.bind-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.bind-dialog :deep(.el-dialog__footer) {
  padding: 0;
  display: none;
}

.bind-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.bind-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.bind-dialog-content {
  padding: 0 0 12px;
}

/* 提示信息栏 */
.bind-notice {
  background: var(--accent-light) !important;
  padding: 10px 14px !important;
  margin: 0 0 16px 0 !important;
  line-height: 1.5;
  color: var(--text-primary);
  font-size: 12px;
  border-left: 4px solid var(--accent) !important;
  border-radius: 0 !important;
}

/* 表单 */
.bind-form {
  padding: 0 16px;
}

.bind-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.bind-form :deep(.el-input__wrapper) {
  background: var(--bg-input);
  border-radius: 6px;
  box-shadow: 0 0 0 1px var(--border-primary) inset;
  padding: 0 12px;
  height: 40px;
}

.bind-form :deep(.el-input__inner) {
  font-size: 13px;
  color: var(--text-primary);
}

.bind-form :deep(.el-input__inner::placeholder) {
  color: var(--text-muted);
}

/* 教程链接 */
.bind-tutorial {
  text-align: center;
  margin: 4px 16px 14px;
}

.bind-tutorial a {
  color: var(--accent);
  text-decoration: none;
  font-size: 12px;
}

.bind-tutorial a:hover {
  text-decoration: underline;
}

/* 确认按钮 */
.bind-submit-btn {
  display: block;
  width: calc(100% - 32px);
  margin: 0 16px;
  height: 40px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
}

/* ─── AI 聊天室 ─── */
.ai-chat-section {
  background-color: #ffffff;
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 16px;
  position: relative;
  transition: all 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
}
/* 暗色模式 */
.app-container.dark .ai-chat-section {
  background-color: #1e293b;
}
.ai-chat-section:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); border-color: rgba(99,102,241,0.2); }
.ai-chat-icon { font-size: 18px; margin-right: 4px; }
.ai-subtitle { font-size: 11px; color: #666; margin-bottom: 12px; padding: 8px 12px; background: rgba(0,0,0,0.02); border-radius: 6px; line-height: 1.6; }
.ai-countdown { display: flex; align-items: center; gap: 8px; padding: 6px 16px; background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.1)); border-radius: 20px; font-size: 12px; border: 1px solid rgba(99,102,241,0.2); }
.countdown-label { color: #6366f1; font-weight: 500; }
.countdown-time { color: #818cf8; font-weight: 600; font-variant-numeric: tabular-nums; }
.ai-right-badges { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
.ai-current-time { display: flex; align-items: center; gap: 4px; font-size: 12px; padding: 5px 12px; background: rgba(99,102,241,0.05); border-radius: 8px; border: 1px solid rgba(99,102,241,0.1); white-space: nowrap; }
.act-label { color: #64748b; font-weight: 500; }
.act-time { color: #334155; font-weight: 600; }
.act-period { color: #ef4444; font-weight: 700; }
.ai-chat-container { flex: 1; min-height: 0; }
.ai-chat-messages { display: flex; flex-direction: column; gap: 16px; padding: 4px 0; }
.ai-chat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 180px; }
.ai-analysis-grid { display: grid; grid-template-columns: 1.2fr auto 0.8fr; gap: 20px; align-items: start; }
.ai-analysts-column { display: flex; flex-direction: column; gap: 16px; }
.ai-message { display: flex; gap: 12px; cursor: pointer; border-radius: 10px; padding: 4px; transition: background 0.2s; }
.ai-message:hover { background: rgba(99,102,241,0.03); }
.ai-avatar-wrap { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.ai-message-avatar { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; background: var(--bg-secondary); border: 1px solid var(--border-primary); overflow: hidden; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.ai-avatar-name { font-size: 10px; color: var(--text-muted); }
.ai-message-body { flex: 1; min-width: 0; }
.ai-message-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.ai-message-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ai-message-content { font-size: 12px; line-height: 1.6; color: var(--text-secondary); background: var(--bg-secondary); border-radius: 10px; padding: 10px 14px; border: 1px solid var(--border-primary); }
.ai-message-content strong { font-weight: 600; color: var(--text-primary); }
.ai-analysts-column .ai-message-content { max-height: 9em; overflow: hidden; position: relative; }
.ai-analysts-column .ai-message-content::after { content: '...'; position: absolute; bottom: 0; right: 6px; background: var(--bg-secondary); padding: 0 4px; font-size: 12px; line-height: 1.6; }
.ai-divider { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 0; }
.divider-line { width: 2px; height: 30px; background: linear-gradient(to bottom, transparent, var(--border-primary), transparent); }
.divider-label { writing-mode: vertical-rl; font-size: 11px; font-weight: 600; color: var(--accent); }
.ai-judge-column { display: flex; flex-direction: column; }
.ai-message--judge .ai-message-avatar { background: rgba(99,102,241,0.1); border-color: rgba(99,102,241,0.3); }
.ai-message--judge .ai-message-content { background: linear-gradient(135deg, rgba(99,102,241,0.06), rgba(168,85,247,0.04)); border-color: rgba(99,102,241,0.15); }
.ai-live-monitor { margin-top: 12px; padding: 12px; background: linear-gradient(135deg, rgba(99,102,241,0.04), rgba(59,130,246,0.04)); border: 1px solid rgba(99,102,241,0.1); border-radius: 10px; }
.live-header { font-size: 11px; font-weight: 600; color: #6366f1; margin-bottom: 10px; }
.live-body { display: flex; flex-direction: column; gap: 6px; }
.live-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; border-radius: 6px; background: rgba(255,255,255,0.6); font-size: 11px; }
.live-pnl-row { border-radius: 6px; animation: pnlPulse 2s infinite; }
.live-cell { display: flex; align-items: center; gap: 6px; }
.live-icon { font-size: 12px; width: 18px; text-align: center; }
.live-label { color: #666; font-size: 10px; }
.live-dir { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: 12px; }
.live-val { font-weight: 600; color: #333; font-size: 12px; }
.live-pnl { font-weight: 700; font-size: 14px; }
.pnl-up { color: #16a34a; }
.pnl-down { color: #dc2626; }
@keyframes pnlPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.85; } }

/* ─── 精选策略 ─── */
.featured-strategies-section {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.featured-icon { font-size: 16px; margin-right: 4px; }
.view-all-link { font-size: 12px; color: var(--accent); text-decoration: none; }
.view-all-link:hover { text-decoration: underline; }
.featured-strategies-list { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.featured-strategy-item { flex: 1; position: relative; padding: 16px; background: var(--bg-secondary); border-radius: 12px; transition: all 0.2s; }
.featured-strategy-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.strategy-item-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.strategy-title-row { display: flex; align-items: center; gap: 6px; }
.strategy-item-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.strategy-official-badge { font-size: 10px; padding: 2px 6px; background: rgba(99,102,241,0.1); color: #6366f1; border-radius: 4px; }
.strategy-profit-badge { display: flex; flex-direction: column; align-items: flex-end; padding: 8px 12px; border-radius: 8px; }
.strategy-profit-badge.profit-up { background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05)); }
.strategy-profit-badge.profit-down { background: linear-gradient(135deg, rgba(239,68,68,0.1), rgba(239,68,68,0.05)); }
.profit-value { font-size: 18px; font-weight: 700; }
.profit-label { font-size: 10px; color: var(--text-muted); }
.strategy-item-desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.5; }
.strategy-metrics { display: flex; gap: 8px; margin-bottom: 10px; }
.metric-pill { display: flex; align-items: center; gap: 4px; padding: 4px 10px; background: rgba(0,0,0,0.03); border-radius: 20px; font-size: 11px; }
.pill-icon { font-size: 12px; }
.pill-label { color: var(--text-muted); }
.pill-value { font-weight: 600; color: var(--text-primary); }
.strategy-actions { display: flex; gap: 8px; align-items: center; }
.use-strategy-btn { flex: 1; }

/* ─── 盈利颜色 ─── */
.profit-up { color: #16a34a; }
.profit-down { color: #dc2626; }
.dir-long { color: #16a34a; background: rgba(22,163,74,0.08); }
.dir-short { color: #dc2626; background: rgba(220,38,38,0.08); }
.dir-hold { color: #666; background: rgba(0,0,0,0.06); }
</style>

<!-- 非scoped样式：ticker滚动条由innerHTML动态创建，scoped属性无法匹配 -->
<style>
/* 滚动区域 — 必须非scoped，因为子元素由 innerHTML 创建 */
.ticker-scroll-area {
  flex: 1;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
}

.ticker-track {
  display: flex;
  width: max-content;
  align-items: center;
}

/* 激活动画 */
.ticker-track.ticker-animated {
  animation: tickerScroll var(--ticker-duration, 80s) linear infinite;
  will-change: transform;
}

.ticker-track.ticker-animated:hover {
  animation-play-state: paused;
}

@keyframes tickerScroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(calc(var(--ticker-w, 1200px) * -2)); }
}

.ticker-content {
  display: flex;
  gap: 0;
  align-items: center;
  flex-shrink: 0;
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 8px;
  white-space: nowrap;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 每个 ticker-item 之间用竖线分隔 */
.ticker-item + .ticker-item {
  border-left: 1px solid var(--border-secondary);
}

/* ticker-content 之间的分隔也用竖线 */
.ticker-content + .ticker-content > .ticker-item:first-child {
  border-left: 1px solid var(--border-secondary);
}

.ticker-price {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  display: inline-block;
  min-width: 42px;
}

.ticker-change {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  display: inline-block;
  min-width: 50px;
  text-align: center;
  /* 默认色 */
  color: #8b949e;
  background: transparent;
}

.ticker-symbol {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

/* Element Plus Dialog 覆盖 */
.el-dialog.bind-dialog {
  border-radius: 16px !important;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.18) !important;
  overflow: hidden;
  animation: bindDialogIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  transform-origin: center center;
  padding: 0 !important;
}

@keyframes bindDialogIn {
  0% {
    opacity: 0;
    transform: scale(0.3);
  }
  60% {
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.el-dialog.bind-dialog .el-dialog__header {
  padding: 16px 0 8px !important;
  margin: 0 12px !important;
}

.el-dialog.bind-dialog .el-dialog__body {
  padding: 0 !important;
  margin: 0 !important;
}

.el-dialog.bind-dialog .bind-dialog-content {
  padding: 0 !important;
  margin: 0 !important;
}

.el-dialog.bind-dialog .bind-notice {
  background: var(--accent-light) !important;
  padding: 10px 14px !important;
  margin: 0 0 16px 0 !important;
  border-left: 4px solid var(--accent) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

.el-dialog.bind-dialog .bind-form {
  padding: 0 12px !important;
}

.el-dialog.bind-dialog .bind-tutorial {
  margin: 4px 12px 14px !important;
}

.el-dialog.bind-dialog .bind-submit-btn {
  margin: 0 12px !important;
  width: calc(100% - 24px) !important;
}
</style>
