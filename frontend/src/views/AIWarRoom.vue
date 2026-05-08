<template>
  <div class="ai-war-room">
    <el-card shadow="hover" class="panel-card">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">
            <el-icon><Cpu /></el-icon>
            AI 作战室
          </span>
          <div class="ai-countdown" v-if="!aiTeamLoading">
            <span class="countdown-label">⏱️ 下次分析</span>
            <span class="countdown-time">{{ nextAnalysisCountdown }}</span>
          </div>
        </div>
      </template>

      <div class="ai-subtitle">
        <span class="subtitle-icon">💡</span>
        AI聊天室基于四大国产模型，对每30分K和1小时K进行分析讨论。由
        <span class="model-tag">GLM-5.1</span>
        <span class="model-tag">Kimi-2.6</span>
        <span class="model-tag">Minimax-2.7</span>
        进行技术分析，最后由
        <span class="model-tag model-tag--judge">DeepSeek-4.0 Pro</span>
        进行总结并判断
      </div>

      <div class="ai-chat-container">
        <div class="ai-chat-messages">
          <div v-if="Object.keys(aiTeamOpinions).length === 0 && !aiTeamJudge && !aiTeamLoading" class="ai-chat-empty">
            <div class="empty-icon">🤖</div>
            <p class="empty-title">AI 团队正在待命</p>
            <p class="empty-desc">系统每30分钟自动分析市场，为您提供专业判断</p>
          </div>

          <div class="ai-analysis-grid" v-if="Object.keys(aiTeamOpinions).length > 0 || aiTeamJudge">
            <div class="ai-analysts-column">
              <template v-for="(opinion, key) in aiTeamOpinions" :key="key">
                <div class="ai-message" :class="'ai-message--' + key">
                  <div class="ai-avatar-wrap">
                    <div class="ai-message-avatar">
                      <img v-if="getAnalystAvatar(key)" :src="getAnalystAvatar(key)" class="avatar-img" />
                      <span v-else>{{ getAnalystEmoji(key) }}</span>
                    </div>
                    <div class="ai-avatar-name">{{ getAnalystShortName(key) }}</div>
                  </div>
                  <div class="ai-message-body">
                    <div class="ai-message-header">
                      <span class="ai-message-name">{{ getAnalystName(key) }}</span>
                      <span class="ai-message-role">{{ getAnalystRole(key) }}</span>
                    </div>
                    <div class="ai-message-content" v-html="formatContent(opinion)"></div>
                  </div>
                </div>
              </template>
            </div>

            <div class="ai-divider">
              <div class="divider-line"></div>
              <div class="divider-label">综合裁决</div>
              <div class="divider-line"></div>
            </div>

            <div class="ai-judge-column">
              <div v-if="aiTeamJudge" class="ai-message ai-message--judge">
                <div class="ai-avatar-wrap">
                  <div class="ai-message-avatar">
                    <img v-if="getAnalystAvatar('judge')" :src="getAnalystAvatar('judge')" class="avatar-img" />
                    <span v-else>{{ getAnalystEmoji('judge') }}</span>
                  </div>
                  <div class="ai-avatar-name">裁决</div>
                </div>
                <div class="ai-message-body">
                  <div class="ai-message-header">
                    <span class="ai-message-name">🏆 综合判断</span>
                    <span class="ai-message-role">最终结论</span>
                  </div>
                  <div class="ai-message-content judge-content" v-html="formatContent(aiTeamJudge)"></div>
                  <div class="ai-message-footer">
                    <span class="ai-time">{{ aiTeamTimestamp }}</span>
                    <span class="ai-disclaimer">⚠️ 仅供参考</span>
                  </div>
                </div>
              </div>

              <div class="ai-judge-tracker" v-if="judgeRecords.length > 0">
                <div class="tracker-title">
                  <span class="tracker-icon">📈</span>
                  <span>判断追踪</span>
                </div>
                <div class="tracker-list">
                  <div class="tracker-item" v-for="r in judgeRecords" :key="r.id">
                    <span class="tracker-time">{{ formatJudgeTime(r.created_at) }}</span>
                    <span class="tracker-period">{{ r.period || '--' }}</span>
                    <span class="tracker-dir" :class="'dir-' + r.direction">
                      {{ r.direction === 'long' ? '📈 多' : r.direction === 'short' ? '📉 空' : '⏸ 观' }}
                    </span>
                    <span class="tracker-price">{{ r.entry_price || '--' }}</span>
                    <span class="tracker-result" :class="'result-' + r.result">
                      <template v-if="r.result === 'correct'">✓ 正确</template>
                      <template v-else-if="r.result === 'wrong'">✗ 错误</template>
                      <template v-else>⏳ 验证中</template>
                    </span>
                  </div>
                </div>
              </div>

              <!-- 实时监控面板 -->
              <div class="ai-live-monitor">
                <div class="live-header">⚡ 实时状态</div>
                <div class="live-body">
                  <div class="live-row">
                    <div class="live-cell">
                      <span class="live-icon">🎯</span>
                      <span class="live-label">方向</span>
                    </div>
                    <span class="live-dir" :class="'dir-' + currentDirection">
                      {{ currentDirection === 'long' ? '做多' : currentDirection === 'short' ? '做空' : '观望' }}
                    </span>
                  </div>
                  <div class="live-row">
                    <div class="live-cell">
                      <span class="live-icon">📍</span>
                      <span class="live-label">入场</span>
                    </div>
                    <span class="live-val">${{ currentEntry || '--' }}</span>
                  </div>
                  <div class="live-row">
                    <div class="live-cell">
                      <span class="live-icon">📊</span>
                      <span class="live-label">现价</span>
                    </div>
                    <span class="live-val">${{ btcPrice || '--' }}</span>
                  </div>
                  <div class="live-row live-pnl-row" :class="livePnL >= 0 ? 'pnl-up' : 'pnl-down'">
                    <div class="live-cell">
                      <span class="live-icon">💰</span>
                      <span class="live-label">盈亏</span>
                    </div>
                    <span class="live-pnl">{{ livePnL >= 0 ? '+' : '' }}{{ livePnL || 0 }}点</span>
                  </div>
                </div>
              </div>

              <!-- 战绩统计 -->
              <div class="ai-stats-panel">
                <div class="stats-title">
                  <span class="stats-icon">🏆</span>
                  <span>近期战绩</span>
                </div>
                <div class="stats-grid">
                  <div class="stats-item">
                    <span class="stats-label">近7天胜率</span>
                    <span class="stats-value">{{ winRate7d }}%</span>
                  </div>
                  <div class="stats-item">
                    <span class="stats-label">做多胜率</span>
                    <span class="stats-value text-green">{{ longWinRate }}%</span>
                  </div>
                  <div class="stats-item">
                    <span class="stats-label">做空胜率</span>
                    <span class="stats-value text-red">{{ shortWinRate }}%</span>
                  </div>
                  <div class="stats-item">
                    <span class="stats-label">最大盈利</span>
                    <span class="stats-value text-green">+{{ maxProfit }}点</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Cpu } from '@element-plus/icons-vue'
import api from '../utils/api'

const aiTeamOpinions = ref({})
const aiTeamJudge = ref('')
const aiTeamTimestamp = ref('')
const nextAnalysisCountdown = ref('')
const judgeRecords = ref([])
const aiTeamLoading = ref(false)
const btcPrice = ref(null)

// 实时监控计算属性
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

// 战绩统计
const winRate7d = computed(() => {
  const verified = judgeRecords.value.filter(r => r.result !== 'pending')
  if (verified.length === 0) return 0
  const wins = verified.filter(r => r.result === 'correct').length
  return Math.round(wins / verified.length * 100)
})

const longWinRate = computed(() => {
  const longRecords = judgeRecords.value.filter(r => r.direction === 'long' && r.result !== 'pending')
  if (longRecords.length === 0) return 0
  const wins = longRecords.filter(r => r.result === 'correct').length
  return Math.round(wins / longRecords.length * 100)
})

const shortWinRate = computed(() => {
  const shortRecords = judgeRecords.value.filter(r => r.direction === 'short' && r.result !== 'pending')
  if (shortRecords.length === 0) return 0
  const wins = shortRecords.filter(r => r.result === 'correct').length
  return Math.round(wins / shortRecords.length * 100)
})

const maxProfit = computed(() => {
  const verified = judgeRecords.value.filter(r => r.result === 'correct' && r.entry_price)
  if (verified.length === 0) return 0
  return Math.round(Math.max(...verified.map(r => Math.abs(r.entry_price - (r.price_at_verify || r.entry_price)))))
})

const analystConfig = ref({
  aggressive: { name: '趋势猎手', emoji: '🚀', avatar_url: '' },
  conservative: { name: '风控专家', emoji: '🛡️', avatar_url: '' },
  technical: { name: '量化派', emoji: '📊', avatar_url: '' },
  judge: { name: '裁决者', emoji: '⚖️', avatar_url: '' },
})

const analystShortNames = {
  aggressive: '趋势',
  conservative: '风控',
  technical: '量化',
  judge: '裁决',
}

const analystRoles = {
  aggressive: '趋势分析',
  conservative: '风险控制',
  technical: '量化分析',
  judge: '综合判断',
}

function getAnalystName(key) {
  return analystConfig.value[key]?.name || key
}

function getAnalystEmoji(key) {
  return analystConfig.value[key]?.emoji || '🤖'
}

function getAnalystAvatar(key) {
  return analystConfig.value[key]?.avatar_url || ''
}

function getAnalystShortName(key) {
  return analystShortNames[key] || key
}

function getAnalystRole(key) {
  return analystRoles[key] || ''
}

function formatContent(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/^(<br>\s*)+/, '')
    .replace(/(<br>\s*)+$/, '')
}

function formatJudgeTime(timeStr) {
  if (!timeStr) return '--'
  const d = new Date(timeStr)
  return d.toLocaleTimeString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadAnalystConfig() {
  try {
    const res = await api.get('/settings/ai')
    if (res.analysts) {
      for (const key of ['aggressive', 'conservative', 'technical']) {
        if (res.analysts[key]) {
          analystConfig.value[key] = {
            name: res.analysts[key].name || key,
            emoji: res.analysts[key].emoji || '🤖',
            avatar_url: res.analysts[key].avatar_url || '',
          }
        }
      }
    }
    if (res.judge) {
      analystConfig.value.judge = {
        name: res.judge.name || '裁决者',
        emoji: res.judge.emoji || '⚖️',
        avatar_url: res.judge.avatar_url || '',
      }
    }
  } catch (e) {
    console.error('Load analyst config error:', e)
  }
}

async function loadAiChatHistory() {
  try {
    const res = await api.get('/dashboard/ai_chat_history?limit=1')
    if (res.history && res.history.length > 0) {
      const latest = res.history[0]
      aiTeamOpinions.value = latest.opinions || {}
      aiTeamJudge.value = latest.judge || ''
      aiTeamTimestamp.value = latest.created_at ? new Date(latest.created_at).toLocaleString('zh-CN') : ''
    }
  } catch (e) {
    console.error('Load AI chat history error:', e)
  }
}

async function loadJudgeRecords() {
  try {
    const res = await api.get('/dashboard/ai_judge_records', { params: { limit: 10 } })
    judgeRecords.value = res.records || []
  } catch (e) {
    console.error('Load judge records error:', e)
  }
}

function updateCountdown() {
  const now = new Date()
  const minute = now.getMinutes()
  let targetMinute = minute < 30 ? 30 : 60
  let target = new Date(now)
  target.setMinutes(targetMinute, 0, 0)
  if (targetMinute === 60) {
    target.setHours(target.getHours() + 1)
    target.setMinutes(0, 0, 0)
  }
  const diff = Math.max(0, Math.floor((target - now) / 1000))
  const m = Math.floor(diff / 60)
  const s = diff % 60
  nextAnalysisCountdown.value = `${m}分${s}秒`

  // 每30秒获取实时价格
  const sec = now.getSeconds()
  if (sec % 30 === 0) fetchBtcPrice()
}

async function fetchBtcPrice() {
  try {
    const res = await api.get('/dashboard/market_regime')
    if (res.btc_price) btcPrice.value = res.btc_price
  } catch (e) { /* 静默 */ }
}

let countdownTimer = null

onMounted(() => {
  loadAnalystConfig()
  loadAiChatHistory()
  loadJudgeRecords()
  updateCountdown()
  countdownTimer = setInterval(updateCountdown, 1000)
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.ai-war-room {
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.ai-countdown {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.ai-subtitle {
  font-size: 11px;
  color: #666;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
  line-height: 1.6;
}

.model-tag {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  margin: 0 2px;
}

.model-tag--judge {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.15));
  color: #8b5cf6;
}

.ai-chat-container {
  min-height: auto;
}

.ai-chat-messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

.ai-analysis-grid {
  display: grid;
  grid-template-columns: 1.2fr auto 0.8fr;
  gap: 20px;
  align-items: start;
}

.ai-analysts-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-message {
  display: flex;
  gap: 12px;
  animation: messageIn 0.3s ease;
}

.ai-avatar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.ai-message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  overflow: hidden;
}

.ai-avatar-name {
  font-size: 10px;
  color: var(--text-muted);
}

.ai-message-body {
  flex: 1;
  min-width: 0;
}

.ai-message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.ai-message-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.ai-message-role {
  font-size: 10px;
  color: var(--text-muted);
}

.ai-message-content {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: 10px;
  padding: 10px 14px;
  border: 1px solid var(--border-primary);
}

.ai-message-content strong {
  font-weight: 600;
  color: var(--text-primary);
}

.ai-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 0;
}

.divider-line {
  width: 2px;
  height: 30px;
  background: linear-gradient(to bottom, transparent, var(--border-primary), transparent);
}

.divider-label {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 1px;
  padding: 4px 0;
}

.ai-judge-column {
  display: flex;
  flex-direction: column;
}

.ai-message--judge .ai-message-avatar {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.3);
}

.ai-message--judge .ai-message-content {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.06), rgba(168, 85, 247, 0.04));
  border-color: rgba(99, 102, 241, 0.15);
}

.ai-message-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 10px;
  color: var(--text-muted);
}

.ai-judge-tracker {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.1);
}

.tracker-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.tracker-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tracker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  font-size: 11px;
  transition: all 0.2s;
}

.tracker-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.tracker-time {
  color: #999;
  font-size: 10px;
  min-width: 85px;
}

.tracker-period {
  color: #666;
  font-size: 10px;
  padding: 1px 6px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 3px;
  min-width: 32px;
  text-align: center;
}

.tracker-dir {
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 45px;
  text-align: center;
}

.dir-long {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
}

.dir-short {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.dir-hold {
  color: #666;
  background: rgba(0, 0, 0, 0.06);
}

.tracker-price {
  color: #333;
  font-weight: 600;
  flex: 1;
}

.tracker-result {
  font-weight: 500;
  min-width: 60px;
  text-align: right;
}

.result-correct {
  color: #16a34a;
}

.result-wrong {
  color: #dc2626;
}

.result-pending {
  color: #f59e0b;
}

@keyframes messageIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 实时监控 */
.ai-live-monitor {
  margin-top: 12px;
  padding: 12px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(59, 130, 246, 0.04));
  border: 1px solid rgba(99, 102, 241, 0.1);
  border-radius: 10px;
}

.live-header {
  font-size: 11px;
  font-weight: 600;
  color: #6366f1;
  margin-bottom: 10px;
}

.live-body { display: flex; flex-direction: column; gap: 6px; }

.live-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.6);
  font-size: 11px;
}

.live-pnl-row { border-radius: 6px; animation: pnlPulse 2s infinite; }
.pnl-up { background: rgba(22, 163, 74, 0.08); border: 1px solid rgba(22, 163, 74, 0.15); }
.pnl-down { background: rgba(220, 38, 38, 0.08); border: 1px solid rgba(220, 38, 38, 0.15); }

.live-cell { display: flex; align-items: center; gap: 6px; }
.live-icon { font-size: 12px; width: 18px; text-align: center; }
.live-label { color: #666; font-size: 10px; }
.live-dir { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: 12px; }
.live-val { font-weight: 600; color: #333; font-size: 12px; }
.live-pnl { font-weight: 700; font-size: 14px; }

.monitor-title, .stats-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.monitor-grid, .stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.monitor-item, .stats-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
}

.monitor-label, .stats-label {
  font-size: 10px;
  color: #999;
}

.monitor-value, .stats-value {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

@keyframes pnlPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}

.ai-stats-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.1);
}

.text-green { color: #16a34a; }
.text-red { color: #dc2626; }
</style>
