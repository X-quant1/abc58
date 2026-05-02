<template>
  <div class="admin-page">
    <div class="admin-header">
      <h1 class="admin-title">管理后台</h1>
      <span class="admin-badge">ADMIN</span>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="admin-tabs">
      <!-- ═══ 1. 运营概览 ═══ -->
      <el-tab-pane label="运营概览" name="overview">
        <div class="stat-cards">
          <div class="stat-card blue">
            <div class="stat-label">注册用户</div>
            <div class="stat-value">{{ overview.users?.total || 0 }}</div>
            <div class="stat-sub">今日 +{{ overview.users?.today_new || 0 }} | 7日活跃 {{ overview.users?.active_7d || 0 }}</div>
          </div>
          <div class="stat-card green">
            <div class="stat-label">运行策略</div>
            <div class="stat-value">{{ overview.strategies?.running || 0 }}<span class="stat-total">/{{ overview.strategies?.total || 0 }}</span></div>
            <div class="stat-sub">策略引擎正常运行中</div>
          </div>
          <div class="stat-card orange">
            <div class="stat-label">今日交易</div>
            <div class="stat-value">{{ overview.trades?.today || 0 }}</div>
            <div class="stat-sub">累计 {{ overview.trades?.total || 0 }} 笔</div>
          </div>
          <div class="stat-card" :class="overview.finance?.total_pnl >= 0 ? 'green' : 'red'">
            <div class="stat-label">累计盈亏</div>
            <div class="stat-value">{{ formatPnl(overview.finance?.total_pnl) }}</div>
            <div class="stat-sub">今日 {{ formatPnl(overview.finance?.today_pnl) }} | 手续费 {{ overview.finance?.total_fee || 0 }}</div>
          </div>
        </div>

        <!-- 最近注册用户 -->
        <div class="panel">
          <h3 class="panel-title">最近注册用户</h3>
          <el-table :data="overview.recent_users || []" stripe size="small" max-height="360">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="email" label="邮箱" width="180" />
            <el-table-column prop="role" label="角色" width="80">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'danger'" size="small">{{ row.active ? '正常' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="注册时间">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 系统状态 -->
        <div class="panel">
          <h3 class="panel-title">系统状态</h3>
          <div class="status-items">
            <div class="status-item">
              <span class="status-label">24h 错误数</span>
              <span class="status-value" :class="{ danger: (overview.system?.error_count_24h || 0) > 10 }">
                {{ overview.system?.error_count_24h || 0 }}
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">未读通知</span>
              <span class="status-value">{{ overview.system?.unread_notifications || 0 }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">管理员数</span>
              <span class="status-value">{{ overview.users?.admin_count || 0 }}</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ═══ 2. 用户管理 ═══ -->
      <el-tab-pane label="用户管理" name="users">
        <div class="toolbar">
          <el-input v-model="userSearch" placeholder="搜索用户名/邮箱/OKX ID" clearable style="width: 260px" @clear="loadUsers" @keyup.enter="loadUsers">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="userRoleFilter" placeholder="角色" clearable style="width: 120px; margin-left: 10px" @change="loadUsers">
            <el-option label="全部" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
          <el-button type="primary" @click="loadUsers" style="margin-left: 10px">搜索</el-button>
          <span class="toolbar-total">共 {{ userTotal }} 条</span>
        </div>
        <el-table :data="users" stripe size="small" v-loading="userLoading" style="width: fit-content">
          <el-table-column prop="id" label="ID" width="50" />
          <el-table-column prop="username" label="用户名" width="100" show-overflow-tooltip />
          <el-table-column prop="email" label="邮箱" show-overflow-tooltip />
          <el-table-column label="绑定平台" width="70">
            <template #default="{ row }">
              <el-tag v-if="row.okx_uid" type="success" size="small">OKX</el-tag>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="okx_uid" label="OKX ID" width="160">
            <template #default="{ row }">
              <div style="display: flex; align-items: center; gap: 4px;">
                <span v-if="row.okx_uid">{{ row.okx_uid }}</span>
                <span v-else style="color: #999">-</span>
                <el-button size="small" text @click="openOkxUidDialog(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="是否下级" width="75">
            <template #default="{ row }">
              <el-tag v-if="row.is_subordinate" type="warning" size="small">下级</el-tag>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="nickname" label="昵称" width="80" show-overflow-tooltip />
          <el-table-column prop="role" label="角色" width="75">
            <template #default="{ row }">
              <el-select :model-value="row.role" size="small" style="width: 70px" @change="(v) => setUserRole(row, v)">
                <el-option label="用户" value="user" />
                <el-option label="管理员" value="admin" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="65">
            <template #default="{ row }">
              <el-switch :model-value="row.active" :disabled="row.role === 'admin'" @change="(v) => toggleUser(row, v)" />
            </template>
          </el-table-column>
          <el-table-column prop="last_login" label="最后登录" width="140">
            <template #default="{ row }">{{ formatTime(row.last_login) || '从未登录' }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="注册时间" width="140">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="userTotal > userPageSize"
          background
          layout="prev, pager, next"
          :total="userTotal"
          :page-size="userPageSize"
          :current-page="userPage"
          @current-change="userPage = $event; loadUsers()"
          style="margin-top: 16px; justify-content: center"
        />
      </el-tab-pane>

      <!-- ═══ 3. 交易记录 ═══ -->
      <el-tab-pane label="交易记录" name="trades">
        <div class="toolbar">
          <span class="toolbar-label">最近</span>
          <el-select v-model="tradeDays" style="width: 100px; margin: 0 10px" @change="loadTrades">
            <el-option :value="1" :label="'1天'" />
            <el-option :value="7" :label="'7天'" />
            <el-option :value="30" :label="'30天'" />
            <el-option :value="90" :label="'90天'" />
          </el-select>
          <span class="toolbar-total">共 {{ tradeStats.count }} 笔</span>
        </div>

        <div class="trade-stats">
          <div class="ts-item">
            <span class="ts-label">总盈亏</span>
            <span class="ts-value" :class="tradeStats.total_pnl >= 0 ? 'up' : 'down'">{{ formatPnl(tradeStats.total_pnl) }}</span>
          </div>
          <div class="ts-item">
            <span class="ts-label">总手续费</span>
            <span class="ts-value">{{ tradeStats.total_fee }}</span>
          </div>
          <div class="ts-item">
            <span class="ts-label">总交易额</span>
            <span class="ts-value">{{ tradeStats.total_amount }}</span>
          </div>
        </div>

        <el-table :data="trades" stripe size="small" v-loading="tradeLoading" max-height="500">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="strategy_id" label="策略" width="60" />
          <el-table-column prop="symbol" label="合约" width="140" />
          <el-table-column prop="direction" label="方向" width="120">
            <template #default="{ row }">
              <span :class="row.direction?.includes('long') ? 'up' : 'down'">{{ directionLabel(row.direction) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="100" />
          <el-table-column prop="amount" label="数量" width="80" />
          <el-table-column prop="pnl" label="盈亏" width="100">
            <template #default="{ row }">
              <span :class="row.pnl >= 0 ? 'up' : 'down'">{{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl?.toFixed(4) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="fee" label="手续费" width="80" />
          <el-table-column prop="created_at" label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="tradeTotal > tradePageSize"
          background
          layout="prev, pager, next"
          :total="tradeTotal"
          :page-size="tradePageSize"
          :current-page="tradePage"
          @current-change="tradePage = $event; loadTrades()"
          style="margin-top: 16px; justify-content: center"
        />
      </el-tab-pane>

      <!-- ═══ 4. 站点配置 ═══ -->
      <el-tab-pane label="站点配置" name="config">
        <el-form label-position="top" class="config-form" v-loading="configLoading">
          <h3 class="panel-title">品牌信息</h3>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="网站名称">
                <el-input v-model="siteConfig.site_name" placeholder="BTC Quant" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="网站标语">
                <el-input v-model="siteConfig.site_slogan" placeholder="专业量化交易策略管理平台" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="品牌标题（登录页）">
                <el-input v-model="siteConfig.brand_headline" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="品牌描述（登录页）">
                <el-input v-model="siteConfig.brand_desc" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="底部版权信息">
            <el-input v-model="siteConfig.brand_footer" />
          </el-form-item>
          <el-form-item label="Logo URL">
            <el-input v-model="siteConfig.logo_url" placeholder="https://example.com/logo.png" />
          </el-form-item>

          <h3 class="panel-title" style="margin-top: 24px">功能开关</h3>
          <el-form-item label="开放注册">
            <el-switch v-model="allowRegister" active-text="开放" inactive-text="关闭" />
          </el-form-item>

          <h3 class="panel-title" style="margin-top: 24px">公告设置</h3>
          <el-form-item label="公告标题">
            <el-input v-model="siteConfig.announcement_title" placeholder="留空则不显示公告" />
          </el-form-item>
          <el-form-item label="公告内容">
            <el-input v-model="siteConfig.announcement_content" type="textarea" :rows="3" placeholder="支持换行" />
          </el-form-item>

          <h3 class="panel-title" style="margin-top: 24px">联系方式</h3>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="联系邮箱">
                <el-input v-model="siteConfig.contact_email" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Telegram">
                <el-input v-model="siteConfig.contact_telegram" />
              </el-form-item>
            </el-col>
          </el-row>

          <h3 class="panel-title" style="margin-top: 24px">交易所注册链接（展示在个人中心卡片上）</h3>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="OKX 注册链接">
                <el-input v-model="siteConfig.okx_register_url" placeholder="https://..." />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="Bitget 注册链接">
                <el-input v-model="siteConfig.bitget_register_url" placeholder="https://..." />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="HTX 注册链接">
                <el-input v-model="siteConfig.htx_register_url" placeholder="https://..." />
              </el-form-item>
            </el-col>
          </el-row>

          <h3 class="panel-title" style="margin-top: 24px">用户协议</h3>
          <el-form-item label="协议标题">
            <el-input v-model="siteConfig.agreement_title" />
          </el-form-item>
          <el-form-item label="协议内容">
            <el-input v-model="siteConfig.agreement_content" type="textarea" :rows="8" placeholder="可使用换行分段" />
          </el-form-item>

          <el-form-item style="margin-top: 20px">
            <el-button type="primary" :loading="configSaving" @click="saveConfig">保存配置</el-button>
            <span v-if="configSaved" style="margin-left: 12px; color: #67c23a; font-size: 13px">✓ 已保存</span>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- ═══ 5. 邮件通知 ═══ -->
      <el-tab-pane label="邮件通知" name="notify">
        <el-row :gutter="20">
          <el-col :span="12">
            <div class="panel">
              <div class="panel-header-row">
                <h3 class="panel-title">SMTP 配置</h3>
                <el-switch v-model="notifyForm.email_enabled" active-text="已开启" inactive-text="已关闭" active-color="#00b42a" @change="saveNotifyConfig" />
              </div>
              <el-form :model="notifyForm" label-width="100px" class="settings-form">
                <el-form-item label="SMTP 主机">
                  <el-input v-model="notifyForm.smtp_host" placeholder="smtp.qq.com / smtp.gmail.com" />
                </el-form-item>
                <el-form-item label="SMTP 端口">
                  <el-input-number v-model="notifyForm.smtp_port" :min="1" :max="9999" style="width: 200px;" />
                  <el-checkbox v-model="notifyForm.smtp_ssl" style="margin-left: 12px;">SSL</el-checkbox>
                </el-form-item>
                <el-form-item label="发件邮箱">
                  <el-input v-model="notifyForm.smtp_user" placeholder="your@qq.com" />
                </el-form-item>
                <el-form-item label="SMTP 密码">
                  <el-input v-model="notifyForm.smtp_password" placeholder="授权码（非登录密码）" show-password />
                </el-form-item>
                <el-form-item label="收件邮箱">
                  <el-input v-model="notifyForm.smtp_to" placeholder="多个用逗号分隔" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveNotifyConfig" :loading="savingNotify">保存配置</el-button>
                  <el-button @click="testNotifyEmail" :loading="testingNotify">发送测试邮件</el-button>
                </el-form-item>
              </el-form>
              <div v-if="notifyTestResult" class="test-result" :class="notifyTestResult.success ? 'success' : 'error'">
                <span>{{ notifyTestResult.message }}</span>
              </div>
              <div class="api-tips" style="margin-top: 16px">
                <p><strong>邮件通知说明：</strong></p>
                <p>开启后，所有用户的策略开仓/平仓、异常告警、系统错误会统一通过此邮箱发送。</p>
                <p>QQ邮箱请使用「授权码」作为密码，<a href="https://service.mail.qq.com/detail/0/310" target="_blank">获取授权码</a></p>
              </div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="panel">
              <h3 class="panel-title">通知场景</h3>
              <div class="notify-scenes">
                <div v-for="scene in notifyScenes" :key="scene.key" class="notify-scene-item">
                  <div class="scene-left">
                    <el-icon :size="18" :color="scene.color"><component :is="scene.icon" /></el-icon>
                    <div>
                      <div class="scene-title">{{ scene.title }}</div>
                      <div class="scene-desc">{{ scene.desc }}</div>
                    </div>
                  </div>
                  <el-switch v-model="notifyForm[scene.key]" @change="saveNotifyConfig" />
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- ═══ 6. 策略管理 ═══ -->
      <el-tab-pane label="策略管理" name="strategies">
        <div class="toolbar">
          <el-button type="primary" @click="openCreateStrategyDialog">
            <el-icon><Plus /></el-icon> 新建策略
          </el-button>
          <el-input v-model="stratSearch" placeholder="搜索策略名称" clearable style="width: 220px; margin-left: 10px" @clear="filterStrats" @keyup.enter="filterStrats">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="stratStatusFilter" placeholder="状态" clearable style="width: 120px; margin-left: 10px" @change="filterStrats">
            <el-option label="全部" value="" />
            <el-option label="已上架" value="published" />
            <el-option label="已下架" value="unpublished" />
          </el-select>
          <el-button type="success" @click="publishAll" style="margin-left: 10px">全部上架</el-button>
          <el-button type="warning" @click="unpublishAll">全部下架</el-button>
          <el-button type="danger" :disabled="selectedStrategies.length === 0" @click="batchDeleteStrategies">
            批量删除 ({{ selectedStrategies.length }})
          </el-button>
          <span class="toolbar-total">共 {{ stratList.length }} 个策略 | 已上架 {{ publishedCount }} 个</span>
        </div>

        <el-table :data="filteredStrategies" stripe size="small" v-loading="stratLoading" @selection-change="handleStrategySelection">
          <el-table-column type="selection" width="50" />
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="策略名称" min-width="140" />
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag v-if="!row.published" type="warning" size="small">已下架</el-tag>
              <el-tag v-else :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '运行中' : '已停止' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="持仓" width="80">
            <template #default="{ row }">
              <span :class="row.position === 'long' ? 'up' : row.position === 'short' ? 'down' : ''">
                {{ row.position || 'none' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="上架" width="100">
            <template #default="{ row }">
              <el-switch :model-value="row.published" @change="(v) => togglePublish(row, v)" />
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" text @click="openEditStrategyDialog(row)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" type="danger" text @click="deleteStrategy(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="filteredStrategies.length === 0" class="empty-tip">暂无策略</div>
      </el-tab-pane>

      <!-- ═══ 7. 系统日志 ═══ -->
      <el-tab-pane label="系统日志" name="logs">
        <div class="toolbar">
          <el-select v-model="logLevel" placeholder="级别" clearable style="width: 100px" @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="Info" value="info" />
            <el-option label="Warn" value="warn" />
            <el-option label="Error" value="error" />
          </el-select>
          <el-select v-model="logModule" placeholder="模块" clearable style="width: 120px; margin-left: 10px" @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="策略" value="strategy" />
            <el-option label="交易" value="trade" />
            <el-option label="行情" value="market" />
            <el-option label="系统" value="system" />
          </el-select>
          <el-select v-model="logHours" style="width: 110px; margin-left: 10px" @change="loadLogs">
            <el-option :value="6" label="6小时" />
            <el-option :value="24" label="24小时" />
            <el-option :value="72" label="3天" />
            <el-option :value="168" label="7天" />
          </el-select>
          <el-button type="primary" @click="loadLogs" style="margin-left: 10px">刷新</el-button>
          <span class="toolbar-total">共 {{ logTotal }} 条</span>
        </div>
        <el-table :data="logs" stripe size="small" v-loading="logLoading" max-height="550">
          <el-table-column prop="created_at" label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="level" label="级别" width="70">
            <template #default="{ row }">
              <el-tag :type="row.level === 'error' ? 'danger' : row.level === 'warn' ? 'warning' : 'info'" size="small">
                {{ row.level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="module" label="模块" width="80" />
          <el-table-column prop="message" label="消息" min-width="400" show-overflow-tooltip />
        </el-table>
        <el-pagination
          v-if="logTotal > logPageSize"
          background
          layout="prev, pager, next"
          :total="logTotal"
          :page-size="logPageSize"
          :current-page="logPage"
          @current-change="logPage = $event; loadLogs()"
          style="margin-top: 16px; justify-content: center"
        />
      </el-tab-pane>

      <!-- ═══ 8. 系统信息 ═══ -->
      <el-tab-pane label="系统信息" name="system">
        <div class="panel">
          <h3 class="panel-title">系统信息</h3>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="系统版本">0.1.0</el-descriptions-item>
            <el-descriptions-item label="数据库">SQLite (WAL)</el-descriptions-item>
            <el-descriptions-item label="后端框架">FastAPI + uvicorn</el-descriptions-item>
            <el-descriptions-item label="前端框架">Vue 3 + Element Plus</el-descriptions-item>
            <el-descriptions-item label="交易所">OKX ({{ isSandbox ? '模拟盘' : '实盘' }})</el-descriptions-item>
            <el-descriptions-item label="策略引擎">9 策略运行中</el-descriptions-item>
            <el-descriptions-item label="交易周期">1H (1小时)</el-descriptions-item>
            <el-descriptions-item label="持仓模式">双向持仓 (long_short_mode)</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="panel" style="margin-top: 20px">
          <h3 class="panel-title">API 路由</h3>
          <div class="api-list">
            <div class="api-group">
              <span class="api-prefix">POST</span> /api/auth/login — 登录
            </div>
            <div class="api-group">
              <span class="api-prefix">POST</span> /api/auth/register — 注册
            </div>
            <div class="api-group">
              <span class="api-prefix">POST</span> /api/auth/send-code — 发送验证码
            </div>
            <div class="api-group">
              <span class="api-prefix">GET</span> /api/strategy/list — 策略列表
            </div>
            <div class="api-group">
              <span class="api-prefix">GET</span> /api/trade/positions — 持仓查询
            </div>
            <div class="api-group">
              <span class="api-prefix">GET</span> /api/market/ticker — 行情数据
            </div>
            <div class="api-group">
              <span class="api-prefix">GET</span> /api/admin/* — 管理后台接口
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ═══ 9. 活动管理 ═══ -->
      <el-tab-pane label="活动管理" name="activities">
        <div class="panel">
          <h3 class="panel-title">横幅图片</h3>
          <el-form-item label="当前图片">
            <div v-if="activityForm.banner_url" class="banner-preview">
              <img :src="activityForm.banner_url" style="max-width: 100%; max-height: 200px; border-radius: 6px;" />
            </div>
            <div v-else class="banner-empty">未设置横幅图片</div>
            <el-upload
              :action="`/api/admin/activities/upload`"
              :headers="uploadHeaders"
              :on-success="onBannerUploadSuccess"
              :before-upload="beforeImageUpload"
              :show-file-list="false"
              accept="image/*"
              style="margin-top: 10px;"
            >
              <el-button type="primary" size="small">{{ activityForm.banner_url ? '更换横幅图片' : '上传横幅图片' }}</el-button>
            </el-upload>
          </el-form-item>
        </div>

        <div class="panel" v-for="(card, index) in activityForm.activities" :key="index">
          <h3 class="panel-title">活动卡片 {{ index + 1 }}</h3>
          <el-form label-position="top">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item label="图标图片">
                  <div v-if="card.icon_url" class="icon-preview">
                    <img :src="card.icon_url" style="max-width: 64px; max-height: 64px; border-radius: 6px;" />
                  </div>
                  <div v-else class="icon-empty">未设置图标</div>
                  <el-upload
                    :action="`/api/admin/activities/upload`"
                    :headers="uploadHeaders"
                    :on-success="(res) => onIconUploadSuccess(res, index)"
                    :before-upload="beforeImageUpload"
                    :show-file-list="false"
                    accept="image/*"
                    style="margin-top: 8px;"
                  >
                    <el-button size="small">{{ card.icon_url ? '更换图标' : '上传图标' }}</el-button>
                  </el-upload>
                </el-form-item>
              </el-col>
              <el-col :span="18">
                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="活动标题">
                      <el-input v-model="card.title" placeholder="活动标题" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="活动描述">
                      <el-input v-model="card.description" placeholder="活动简要描述" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="12">
                  <el-col :span="8">
                    <el-form-item label="状态文字">
                      <el-input v-model="card.status_text" placeholder="如：进行中" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="角标文字">
                      <el-input v-model="card.badge_label" placeholder="如：HOT" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="角标类型">
                      <el-select v-model="card.badge_type" style="width: 100%">
                        <el-option label="无角标" value="none" />
                        <el-option label="HOT (红)" value="hot" />
                        <el-option label="NEW (蓝)" value="new" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <el-button type="primary" @click="saveActivities" :loading="activitySaving" style="margin-top: 16px;">
          保存活动配置
        </el-button>
      </el-tab-pane>

      <!-- ═══ 9. 机器人管理 ═══ -->
      <el-tab-pane label="机器人管理" name="robots">
        <div class="panel">
          <div class="panel-header-row">
            <h3 class="panel-title">量化机器人</h3>
            <el-button type="primary" size="small" @click="openRobotCreateDialog">
              <el-icon><Plus /></el-icon> 新建机器人
            </el-button>
          </div>
          <el-table :data="robots" stripe size="small">
            <el-table-column prop="id" label="ID" width="50" />
            <el-table-column prop="name" label="名称" width="120" />
            <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
            <el-table-column prop="strategies" label="策略" width="200">
              <template #default="{ row }">
                <el-tag v-for="s in row.strategies" :key="s" size="small" style="margin-right: 4px;">
                  {{ formatStrategyName(s) }}
                </el-tag>
                <span v-if="!row.strategies?.length" class="text-muted">未配置</span>
              </template>
            </el-table-column>
            <el-table-column prop="current_equity" label="当前权益" width="100">
              <template #default="{ row }">${{ formatNum(row.current_equity) }}</template>
            </el-table-column>
            <el-table-column prop="total_pnl" label="累计盈亏" width="100">
              <template #default="{ row }">
                <span :class="row.total_pnl >= 0 ? 'val-up' : 'val-down'">
                  {{ row.total_pnl >= 0 ? '+' : '' }}${{ formatNum(row.total_pnl) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="win_rate" label="胜率" width="70">
              <template #default="{ row }">{{ row.win_rate.toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column prop="is_running" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_running ? 'success' : 'info'" size="small">
                  {{ row.is_running ? '运行中' : '已停止' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <div class="robot-actions">
                  <el-button size="small" class="action-btn edit" @click="openRobotEditDialog(row)">编辑</el-button>
                  <el-button size="small" class="action-btn" :class="row.is_running ? 'stop' : 'start'" @click="toggleRobot(row)">
                    {{ row.is_running ? '停止' : '启动' }}
                  </el-button>
                  <el-button size="small" class="action-btn delete" @click="deleteRobot(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- OKX UID 编辑对话框 -->
    <el-dialog v-model="okxUidDialogVisible" title="设置 OKX UID" width="400px">
      <el-form label-width="80px">
        <el-form-item label="用户">
          <span>{{ okxUidDialogUser?.username }}</span>
        </el-form-item>
        <el-form-item label="OKX UID">
          <el-input v-model="okxUidDialogValue" placeholder="输入 OKX 账户 ID" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="okxUidDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveOkxUid">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建策略对话框 -->
    <el-dialog v-model="showCreateStrategyDialog" title="新建策略" width="620px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="110px" class="create-form">
        <el-form-item label="策略名称">
          <el-input v-model="createForm.name" placeholder="如：MACD背离-30m" />
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
          <el-input-number v-model="createForm.leverage" :min="1" :max="125" :step="1" />
          <span class="hint-label">倍（建议 ≤ 20）</span>
        </el-form-item>
        <el-form-item label="交易周期">
          <el-checkbox-group v-model="createForm.timeframes">
            <el-checkbox value="5m">5分钟</el-checkbox>
            <el-checkbox value="10m">10分钟</el-checkbox>
            <el-checkbox value="15m">15分钟</el-checkbox>
            <el-checkbox value="30m">30分钟</el-checkbox>
            <el-checkbox value="1h">1小时</el-checkbox>
            <el-checkbox value="4h">4小时</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="持仓模式">
          <el-radio-group v-model="createForm.td_mode">
            <el-radio value="cross">全仓</el-radio>
            <el-radio value="isolated">逐仓</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-divider content-position="left">止盈止损</el-divider>
        <el-form-item label="止盈比例">
          <el-input-number v-model="createForm.take_profit_pct" :min="0" :max="100" :step="0.1" :precision="2" />
          <span class="hint-label">%（0=不设止盈）</span>
        </el-form-item>
        <el-form-item label="止损比例">
          <el-input-number v-model="createForm.stop_loss_pct" :min="0" :max="100" :step="0.1" :precision="2" />
          <span class="hint-label">%（0=不设止损）</span>
        </el-form-item>
        <el-form-item label="移动止盈">
          <el-input-number v-model="createForm.trailing_stop_pct" :min="0" :max="50" :step="0.1" :precision="2" />
          <span class="hint-label">%（0=不启用）</span>
        </el-form-item>
        <el-form-item label="移动激活阈值">
          <el-input-number v-model="createForm.trail_activate_pct" :min="0" :max="10" :step="0.1" :precision="2" />
          <span class="hint-label">%（盈利达到此比例激活移动止盈）</span>
        </el-form-item>
        <el-form-item label="回调点数">
          <el-input-number v-model="createForm.trail_callback_points" :min="0" :max="1000" :step="1" />
          <span class="hint-label">点（价格回调此点数触发平仓）</span>
        </el-form-item>
        <el-form-item label="冷却时间">
          <el-input-number v-model="createForm.cooldown_minutes" :min="0" :max="1440" :step="5" />
          <span class="hint-label">分钟（开仓后冷却时间，0=不限制）</span>
        </el-form-item>
        <el-form-item label="策略说明">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="策略描述、适用场景、风险提示等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateStrategyDialog = false">取消</el-button>
        <el-button type="primary" @click="createStrategy" :loading="creating">创建策略</el-button>
      </template>
    </el-dialog>

    <!-- 修改策略对话框 -->
    <el-dialog v-model="showEditStrategyDialog" title="修改策略" width="620px" :close-on-click-modal="false">
      <el-form :model="editForm" label-width="110px" class="create-form">
        <el-form-item label="策略名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="策略类型">
          <el-select v-model="editForm.type" style="width: 100%;" disabled>
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
          <el-select v-model="editForm.inst_id" style="width: 100%;">
            <el-option label="BTC-USDT 永续" value="BTC-USDT-SWAP" />
            <el-option label="ETH-USDT 永续" value="ETH-USDT-SWAP" />
            <el-option label="SOL-USDT 永续" value="SOL-USDT-SWAP" />
          </el-select>
        </el-form-item>
        <el-form-item label="下单方式">
          <el-radio-group v-model="editForm.size_mode">
            <el-radio value="fixed">固定张数</el-radio>
            <el-radio value="percent">仓位百分比</el-radio>
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
        <el-form-item label="杠杆倍数">
          <el-input-number v-model="editForm.leverage" :min="1" :max="125" :step="1" />
          <span class="hint-label">倍（建议 ≤ 20）</span>
        </el-form-item>
        <el-form-item label="交易周期">
          <el-checkbox-group v-model="editForm.timeframes">
            <el-checkbox value="5m">5分钟</el-checkbox>
            <el-checkbox value="10m">10分钟</el-checkbox>
            <el-checkbox value="15m">15分钟</el-checkbox>
            <el-checkbox value="30m">30分钟</el-checkbox>
            <el-checkbox value="1h">1小时</el-checkbox>
            <el-checkbox value="4h">4小时</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="持仓模式">
          <el-radio-group v-model="editForm.td_mode">
            <el-radio value="cross">全仓</el-radio>
            <el-radio value="isolated">逐仓</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-divider content-position="left">止盈止损</el-divider>
        <el-form-item label="止盈比例">
          <el-input-number v-model="editForm.take_profit_pct" :min="0" :max="100" :step="0.1" :precision="2" />
          <span class="hint-label">%（0=不设止盈）</span>
        </el-form-item>
        <el-form-item label="止损比例">
          <el-input-number v-model="editForm.stop_loss_pct" :min="0" :max="100" :step="0.1" :precision="2" />
          <span class="hint-label">%（0=不设止损）</span>
        </el-form-item>
        <el-form-item label="移动止损">
          <el-input-number v-model="editForm.trailing_stop_pct" :min="0" :max="50" :step="0.1" :precision="2" />
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
        <el-form-item label="策略说明">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="策略描述、适用场景、风险提示等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditStrategyDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEditStrategy" :loading="savingEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 机器人编辑对话框 -->
    <el-dialog v-model="robotDialogVisible" :title="robotDialogMode === 'create' ? '新建机器人' : '编辑机器人'" width="750px" destroy-on-close>
      <el-form :model="robotForm" label-width="100px">
        <el-form-item label="机器人名称">
          <el-input v-model="robotForm.name" placeholder="例如：趋势先锋" maxlength="20" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="robotForm.description" type="textarea" :rows="2" placeholder="策略描述" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="robotForm.initial_capital" :min="100" :max="1000000" :step="1000" :precision="2" />
          <span class="hint-label">USDT</span>
        </el-form-item>

        <!-- 通用交易参数 -->
        <el-divider content-position="left">通用交易参数</el-divider>
        <el-form-item label="下单方式">
          <el-radio-group v-model="robotForm.size_mode">
            <el-radio value="fixed">固定张数</el-radio>
            <el-radio value="percent">仓位百分比</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="robotForm.size_mode === 'fixed'" label="下单张数">
          <el-input-number v-model="robotForm.size" :min="0.01" :max="1000" :step="0.01" :precision="2" />
          <span class="hint-label">合约张数（最小0.01）</span>
        </el-form-item>
        <el-form-item v-else label="仓位比例">
          <el-input-number v-model="robotForm.size_pct" :min="1" :max="100" :step="5" />
          <span class="hint-label">% 可用资金</span>
        </el-form-item>
        <el-form-item label="杠杆倍数">
          <el-input-number v-model="robotForm.leverage" :min="1" :max="125" :step="1" />
          <span class="hint-label">倍（建议 ≤ 20）</span>
        </el-form-item>

        <!-- 策略配置 -->
        <el-divider content-position="left">运行策略</el-divider>
        <el-form-item label=" ">
          <div class="strategy-config-list">
            <div v-for="(strategy, idx) in robotForm.strategyConfigs" :key="idx" class="strategy-config-item">
              <div class="strategy-header" @click="toggleStrategyExpand(idx)">
                <el-checkbox v-model="strategy.enabled" @click.stop />
                <span class="strategy-name">{{ getStrategyName(strategy.type) }}</span>
                <el-tag v-if="strategy.enabled" type="success" size="small" style="margin-left: 8px;">已启用</el-tag>
                <el-icon class="expand-icon" :class="{ expanded: strategy.expanded }"><ArrowRight /></el-icon>
              </div>
              <div v-show="strategy.expanded" class="strategy-params" :class="{ disabled: !strategy.enabled }">
                <div class="param-row" v-for="(value, key) in strategy.params" :key="key">
                  <label class="param-label">{{ formatParamLabel(key) }}</label>
                  <el-input-number
                    v-if="typeof value === 'number' && !Array.isArray(value)"
                    v-model="strategy.params[key]"
                    :min="getParamMin(key)"
                    :max="getParamMax(key)"
                    :step="getParamStep(key)"
                    :precision="2"
                    size="small"
                    :disabled="!strategy.enabled"
                  />
                  <el-select v-else-if="Array.isArray(value)" v-model="strategy.params[key]" multiple size="small" style="width: 180px;" :disabled="!strategy.enabled">
                    <el-option v-for="tf in ['5m', '10m', '15m', '30m', '1h', '4h']" :key="tf" :label="tf" :value="tf" />
                  </el-select>
                  <el-input v-else v-model="strategy.params[key]" size="small" style="width: 180px;" :disabled="!strategy.enabled" />
                </div>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="robotForm.sort_order" :min="0" :max="99" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="robotDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRobot">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Edit, Switch, WarningFilled, Monitor, Delete, Plus, ArrowRight } from '@element-plus/icons-vue'
import axios from '../utils/api'

const router = useRouter()

// 当前标签
const activeTab = ref('overview')
const isSandbox = ref(false)

// ═══ 1. 运营概览 ═══
const overview = ref({})

async function loadOverview() {
  try {
    overview.value = await axios.get('/admin/overview')
  } catch (e) {
    if (e?.status === 403) {
      ElMessage.error('需要管理员权限')
      router.push('/dashboard')
    }
  }
}

// ═══ 2. 用户管理 ═══
const users = ref([])
const userTotal = ref(0)
const userPage = ref(1)
const userPageSize = 20
const userSearch = ref('')
const userRoleFilter = ref('')
const userLoading = ref(false)

async function loadUsers() {
  userLoading.value = true
  try {
    const params = { page: userPage.value, size: userPageSize }
    if (userSearch.value) params.search = userSearch.value
    if (userRoleFilter.value) params.role = userRoleFilter.value
    const data = await axios.get('/admin/users', { params })
    users.value = data.users
    userTotal.value = data.total
  } catch { /* ignore */ }
  userLoading.value = false
}

async function toggleUser(row, active) {
  const action = active ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(`确定${action}用户 "${row.username}"？`, '确认操作', { type: 'warning' })
    await axios.post('/admin/users/toggle', { user_id: row.id, active })
    ElMessage.success(`已${action}`)
    loadUsers()
    loadOverview()
  } catch { /* cancel */ }
}

async function setUserRole(row, role) {
  if (row.role === role) return
  const label = role === 'admin' ? '管理员' : '普通用户'
  try {
    await ElMessageBox.confirm(`确定将 "${row.username}" 设为${label}？`, '确认操作', { type: 'warning' })
    await axios.post('/admin/users/role', { user_id: row.id, role })
    ElMessage.success('角色已更新')
    loadUsers()
    loadOverview()
  } catch { /* cancel or error, restore */ }
}

// OKX UID 编辑
const okxUidDialogVisible = ref(false)
const okxUidDialogUser = ref(null)
const okxUidDialogValue = ref('')

function openOkxUidDialog(row) {
  okxUidDialogUser.value = row
  okxUidDialogValue.value = row.okx_uid || ''
  okxUidDialogVisible.value = true
}

async function saveOkxUid() {
  if (!okxUidDialogUser.value) return
  try {
    await axios.post('/admin/users/okx-uid', {
      user_id: okxUidDialogUser.value.id,
      okx_uid: okxUidDialogValue.value
    })
    ElMessage.success('OKX UID 已保存')
    okxUidDialogVisible.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

// ═══ 3. 交易记录 ═══
const trades = ref([])
const tradeTotal = ref(0)
const tradePage = ref(1)
const tradePageSize = 20
const tradeDays = ref(30)
const tradeLoading = ref(false)
const tradeStats = ref({ count: 0, total_pnl: 0, total_fee: 0, total_amount: 0 })

async function loadTrades() {
  tradeLoading.value = true
  try {
    const data = await axios.get('/admin/trades', {
      params: { page: tradePage.value, size: tradePageSize, days: tradeDays.value }
    })
    trades.value = data.trades
    tradeTotal.value = data.total
    tradeStats.value = data.stats
  } catch { /* ignore */ }
  tradeLoading.value = false
}

// ═══ 4. 站点配置 ═══
const siteConfig = reactive({
  site_name: '', site_slogan: '', brand_headline: '', brand_desc: '',
  brand_footer: '', logo_url: '', allow_register: 'true',
  announcement_title: '', announcement_content: '',
  contact_email: '', contact_telegram: '',
  okx_register_url: '', bitget_register_url: '', htx_register_url: '',
  agreement_title: '', agreement_content: '',
})
const configLoading = ref(false)
const configSaving = ref(false)
const configSaved = ref(false)

const allowRegister = computed({
  get: () => siteConfig.allow_register === 'true',
  set: v => { siteConfig.allow_register = v ? 'true' : 'false' }
})

async function loadConfig() {
  configLoading.value = true
  try {
    const data = await axios.get('/admin/config')
    Object.assign(siteConfig, data.configs)
  } catch { /* ignore */ }
  configLoading.value = false
}

async function saveConfig() {
  configSaving.value = true
  configSaved.value = false
  try {
    await axios.post('/admin/config', { configs: { ...siteConfig } })
    ElMessage.success('配置已保存')
    configSaved.value = true
    setTimeout(() => { configSaved.value = false }, 3000)
  } catch {
    ElMessage.error('保存失败')
  }
  configSaving.value = false
}

// ═══ 5. 邮件通知 ═══
const notifyForm = reactive({
  smtp_host: '',
  smtp_port: 465,
  smtp_user: '',
  smtp_password: '',
  smtp_to: '',
  smtp_ssl: true,
  email_enabled: false,
  notify_trade: true,
  notify_error: true,
  notify_system: true,
})

const notifyScenes = [
  { key: 'notify_trade', title: '交易通知', desc: '开仓/平仓时发送邮件', icon: 'Switch', color: '#f7931a' },
  { key: 'notify_error', title: '策略异常', desc: '策略运行错误、余额不足等', icon: 'WarningFilled', color: '#f53f3f' },
  { key: 'notify_system', title: '系统告警', desc: '系统错误、WebSocket断连等', icon: 'Monitor', color: '#3491fa' },
]

const savingNotify = ref(false)
const testingNotify = ref(false)
const notifyTestResult = ref(null)

async function loadNotifyConfig() {
  try {
    const res = await axios.get('/settings/notify')
    Object.assign(notifyForm, {
      smtp_host: res.smtp_host ?? '',
      smtp_port: res.smtp_port ?? 465,
      smtp_user: res.smtp_user ?? '',
      smtp_password: res.smtp_password ?? '',
      smtp_to: res.smtp_to ?? '',
      smtp_ssl: res.smtp_ssl ?? true,
      email_enabled: res.email_enabled ?? false,
      notify_trade: res.notify_trade ?? true,
      notify_error: res.notify_error ?? true,
      notify_system: res.notify_system ?? true,
    })
  } catch { /* ignore */ }
}

async function saveNotifyConfig() {
  savingNotify.value = true
  try {
    await axios.post('/settings/notify', notifyForm)
    ElMessage.success('通知配置已保存')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingNotify.value = false
  }
}

async function testNotifyEmail() {
  testingNotify.value = true
  notifyTestResult.value = null
  try {
    await saveNotifyConfig()
    const res = await axios.post('/settings/notify/test')
    notifyTestResult.value = { success: true, message: res.message }
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    notifyTestResult.value = { success: false, message: detail }
  } finally {
    testingNotify.value = false
  }
}

// ═══ 6. 策略管理 ═══
const stratList = ref([])
const stratSearch = ref('')
const stratStatusFilter = ref('')
const stratLoading = ref(false)
const selectedStrategies = ref([])

// 创建策略相关
const showCreateStrategyDialog = ref(false)
const creating = ref(false)
const availableStrategies = ref([])
const strategyTemplates = ref([])

// 策略模板加载
async function loadStrategyTemplates() {
  try {
    const res = await axios.get('/strategy/available')
    strategyTemplates.value = Array.isArray(res?.strategies) ? res.strategies : []
  } catch (e) {
    console.error('Failed to load strategy templates:', e)
  }
}

function formatStrategyName(type) {
  if (!type) return '未知'
  const tpl = strategyTemplates.value.find(t => t.type === type) || availableStrategies.value.find(s => s.type === type)
  return tpl ? tpl.name : type
}

function formatNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '--'
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

const createForm = reactive({
  name: '',
  type: '',
  inst_id: 'BTC-USDT-SWAP',
  size_mode: 'fixed',
  size: 1,
  size_pct: 10,
  leverage: 10,
  take_profit_pct: 0,
  stop_loss_pct: 0,
  trailing_stop_pct: 0,
  trail_activate_pct: 0,
  trail_callback_points: 0,
  cooldown_minutes: 0,
  td_mode: 'cross',
  timeframes: ['1h'],
  description: '',
  params: {}
})

// 修改策略相关
const showEditStrategyDialog = ref(false)
const savingEdit = ref(false)
const editingStrategyId = ref(null)
const editForm = reactive({
  name: '',
  type: '',
  inst_id: 'BTC-USDT-SWAP',
  size_mode: 'fixed',
  size: 1,
  size_pct: 10,
  leverage: 10,
  take_profit_pct: 0,
  stop_loss_pct: 0,
  trailing_stop_pct: 0,
  trail_activate_pct: 0,
  trail_callback_points: 0,
  cooldown_minutes: 0,
  td_mode: 'cross',
  timeframes: ['1h'],
  description: '',
  params: {}
})

const publishedCount = computed(() => stratList.value.filter(s => s.published).length)

const filteredStrategies = computed(() => {
  let list = stratList.value
  if (stratSearch.value) {
    const kw = stratSearch.value.toLowerCase()
    list = list.filter(s => s.name.toLowerCase().includes(kw))
  }
  if (stratStatusFilter.value === 'published') list = list.filter(s => s.published)
  if (stratStatusFilter.value === 'unpublished') list = list.filter(s => !s.published)
  return list
})

function filterStrats() { /* computed handles it */ }

async function loadStrategies() {
  stratLoading.value = true
  try {
    const data = await axios.get('/admin/strategies/list')
    stratList.value = data.strategies
  } catch { /* ignore */ }
  stratLoading.value = false
}

async function togglePublish(row, published) {
  try {
    const res = await axios.post('/admin/strategies/publish', { strategy_id: row.id, published })
    row.published = published
    ElMessage.success(res.message || `策略「${row.name}」已${published ? '上架' : '下架'}`)
    // 刷新列表以获取最新状态
    await loadStrategies()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message || '操作失败'
    ElMessage.error(detail)
    // 刷新列表以恢复正确状态
    await loadStrategies()
  }
}

async function publishAll() {
  try {
    await ElMessageBox.confirm('确定将所有策略上架？', '确认', { type: 'warning' })
    await axios.post('/admin/strategies/publish-all')
    ElMessage.success('已全部上架')
    await loadStrategies()
  } catch { /* cancel */ }
}

async function unpublishAll() {
  try {
    await ElMessageBox.confirm('确定将所有策略下架？用户将无法看到任何策略。', '确认', { type: 'warning' })
    await axios.post('/admin/strategies/unpublish-all')
    ElMessage.success('已全部下架')
    await loadStrategies()
  } catch { /* cancel */ }
}

async function deleteStrategy(row) {
  try {
    await ElMessageBox.confirm(`确定要删除策略「${row.name}」吗？此操作不可恢复。`, '确认删除', { type: 'warning' })
    await axios.delete(`/strategy/${row.id}`)
    ElMessage.success('策略已删除')
    await loadStrategies()
  } catch { /* cancel */ }
}

function handleStrategySelection(selection) {
  selectedStrategies.value = selection
}

async function batchDeleteStrategies() {
  if (selectedStrategies.value.length === 0) return
  
  const ids = selectedStrategies.value.map(s => s.id)
  const names = selectedStrategies.value.map(s => s.name).join('、')
  
  try {
    await ElMessageBox.confirm(
      `确定要删除以下 ${ids.length} 个策略吗？此操作不可恢复。\n\n${names}`,
      '批量删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    
    // 逐个删除
    let successCount = 0
    let failCount = 0
    for (const id of ids) {
      try {
        await axios.delete(`/strategy/${id}`)
        successCount++
      } catch {
        failCount++
      }
    }
    
    if (failCount === 0) {
      ElMessage.success(`已成功删除 ${successCount} 个策略`)
    } else {
      ElMessage.warning(`删除完成：成功 ${successCount} 个，失败 ${failCount} 个`)
    }

    selectedStrategies.value = []
    await loadStrategies()
  } catch { /* cancel */ }
}

// 创建策略相关函数
async function loadAvailableStrategies() {
  try {
    const data = await axios.get('/strategy/available')
    availableStrategies.value = data.strategies || []
  } catch { /* ignore */ }
}

function openCreateStrategyDialog() {
  createForm.name = ''
  createForm.type = ''
  createForm.inst_id = 'BTC-USDT-SWAP'
  createForm.size_mode = 'fixed'
  createForm.size = 1
  createForm.size_pct = 10
  createForm.leverage = 10
  createForm.take_profit_pct = 0
  createForm.stop_loss_pct = 0
  createForm.trailing_stop_pct = 0
  createForm.trail_activate_pct = 0
  createForm.trail_callback_points = 0
  createForm.cooldown_minutes = 0
  createForm.td_mode = 'cross'
  createForm.timeframes = ['1h']
  createForm.description = ''
  createForm.params = {}
  showCreateStrategyDialog.value = true
}

function onStrategyTypeChange(type) {
  const found = availableStrategies.value.find(s => s.type === type)
  if (found) {
    createForm.params = { ...found.default_params }
    // 如果默认参数中有timeframes，更新到表单
    if (found.default_params.timeframes) {
      createForm.timeframes = found.default_params.timeframes
    }
    // MACD背离策略特殊处理：填充推荐参数
    if (type === 'macd_divergence') {
      createForm.take_profit_pct = 0.3
      createForm.stop_loss_pct = 0.25
      createForm.trail_activate_pct = 0.2
      createForm.trail_callback_points = 15
      createForm.cooldown_minutes = 30
      createForm.timeframes = ['30m']
    }
  }
}

async function createStrategy() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入策略名称')
    return
  }
  if (!createForm.type) {
    ElMessage.warning('请选择策略类型')
    return
  }

  creating.value = true
  try {
    // 后端期望参数在顶层，不是嵌套在 params 里
    const body = {
      name: createForm.name,
      type: createForm.type,
      params: createForm.params,  // 策略特定参数
      inst_id: createForm.inst_id,
      size_mode: createForm.size_mode,
      size: createForm.size,
      size_pct: createForm.size_pct,
      leverage: createForm.leverage,
      take_profit_pct: createForm.take_profit_pct,
      stop_loss_pct: createForm.stop_loss_pct,
      trailing_stop_pct: createForm.trailing_stop_pct,
      td_mode: createForm.td_mode,
      timeframes: createForm.timeframes,
      use_regime_filter: false,  // 已移除市场状态过滤
    }
    await axios.post('/strategy/create', body)
    ElMessage.success('策略已创建')
    showCreateStrategyDialog.value = false
    await loadStrategies()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

// 修改策略相关函数
function openEditStrategyDialog(row) {
  editingStrategyId.value = row.id
  editForm.name = row.name
  editForm.type = row.type
  editForm.inst_id = row.params?.inst_id || 'BTC-USDT-SWAP'
  editForm.size_mode = row.params?.size_mode || 'fixed'
  editForm.size = row.params?.size ?? 1
  editForm.size_pct = row.params?.size_pct || 10
  editForm.leverage = row.params?.leverage || 10
  editForm.take_profit_pct = row.params?.take_profit_pct || 0
  editForm.stop_loss_pct = row.params?.stop_loss_pct || 0
  editForm.trailing_stop_pct = row.params?.trailing_stop_pct || 0
  editForm.trail_activate_pct = row.params?.trail_activate_pct || 0
  editForm.trail_callback_points = row.params?.trail_callback_points || 0
  editForm.cooldown_minutes = row.params?.cooldown_minutes || 0
  editForm.td_mode = row.params?.td_mode || 'cross'
  editForm.timeframes = row.params?.timeframes || ['1h']
  editForm.description = row.params?.description || ''
  editForm.params = row.params || {}
  showEditStrategyDialog.value = true
}

async function saveEditStrategy() {
  if (!editForm.name.trim()) {
    ElMessage.warning('请输入策略名称')
    return
  }

  savingEdit.value = true
  try {
    const body = {
      name: editForm.name,
      inst_id: editForm.inst_id,
      size_mode: editForm.size_mode,
      size: editForm.size,
      size_pct: editForm.size_pct,
      leverage: editForm.leverage,
      take_profit_pct: editForm.take_profit_pct,
      stop_loss_pct: editForm.stop_loss_pct,
      trailing_stop_pct: editForm.trailing_stop_pct,
      trail_activate_pct: editForm.trail_activate_pct,
      trail_callback_points: editForm.trail_callback_points,
      cooldown_minutes: editForm.cooldown_minutes,
      td_mode: editForm.td_mode,
      timeframes: editForm.timeframes,
      description: editForm.description,
    }
    await axios.put(`/strategy/${editingStrategyId.value}`, body)
    ElMessage.success('策略已修改')
    showEditStrategyDialog.value = false
    await loadStrategies()
  } catch (e) {
    ElMessage.error('修改失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingEdit.value = false
  }
}

// ═══ 7. 系统日志 ═══
const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = 50
const logLevel = ref('')
const logModule = ref('')
const logHours = ref(24)
const logLoading = ref(false)

async function loadLogs() {
  logLoading.value = true
  try {
    const params = { page: logPage.value, size: logPageSize, hours: logHours.value }
    if (logLevel.value) params.level = logLevel.value
    if (logModule.value) params.module = logModule.value
    const data = await axios.get('/admin/logs', { params })
    logs.value = data.logs
    logTotal.value = data.total
  } catch { /* ignore */ }
  logLoading.value = false
}

// ═══ 工具函数 ═══
function formatTime(ts) {
  if (!ts) return ''
  return ts.replace('T', ' ').substring(0, 19)
}

function formatPnl(v) {
  if (v == null) return '0'
  return (v >= 0 ? '+' : '') + parseFloat(v).toFixed(4)
}

function directionLabel(d) {
  if (!d) return d
  const map = { open_long: '开多', open_short: '开空', close_long: '平多', close_short: '平空', buy: '买入', sell: '卖出' }
  return map[d] || d
}

// ═══ 9. 活动管理 ═══
const activityForm = reactive({
  banner_url: '',
  activities: [
    { id: null, sort_order: 1, icon_url: '', title: '', description: '', status_text: '', badge_label: '', badge_type: 'none', active: true },
    { id: null, sort_order: 2, icon_url: '', title: '', description: '', status_text: '', badge_label: '', badge_type: 'none', active: true },
    { id: null, sort_order: 3, icon_url: '', title: '', description: '', status_text: '', badge_label: '', badge_type: 'none', active: true },
  ],
})
const activitySaving = ref(false)

const uploadHeaders = {
  Authorization: `Bearer ${localStorage.getItem('token')}`,
}

function beforeImageUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isImage) { ElMessage.error('只能上传图片文件'); return false }
  if (!isLt5M) { ElMessage.error('图片大小不能超过 5MB'); return false }
  return true
}

function onBannerUploadSuccess(res) {
  activityForm.banner_url = res.url
  ElMessage.success('横幅上传成功')
}

function onIconUploadSuccess(res, index) {
  activityForm.activities[index].icon_url = res.url
  ElMessage.success('图标上传成功')
}

async function loadActivities() {
  try {
    const data = await axios.get('/admin/activities')
    activityForm.banner_url = data.banner_url || ''
    if (data.activities) {
      for (let i = 0; i < 3; i++) {
        if (data.activities[i]) {
          Object.assign(activityForm.activities[i], data.activities[i])
        }
      }
    }
  } catch (e) {
    ElMessage.error('加载活动数据失败')
  }
}

async function saveActivities() {
  activitySaving.value = true
  try {
    await axios.post('/admin/activities/save', {
      banner_url: activityForm.banner_url,
      activities: activityForm.activities,
    })
    ElMessage.success('活动配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    activitySaving.value = false
  }
}

// ═══ 机器人管理 ═══
const robots = ref([])
const robotDialogVisible = ref(false)
const robotDialogMode = ref('create')
const robotForm = ref({
  name: '',
  description: '',
  initial_capital: 10000,
  size_mode: 'fixed',
  size: 1,
  size_pct: 10,
  leverage: 10,
  strategies: [],
  strategyConfigs: [],
  sort_order: 0,
})
const robotEditId = ref(null)

async function loadRobots() {
  try {
    const res = await axios.get('/robots')
    robots.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('Failed to load robots:', e)
  }
}

// 策略参数标签映射
const paramLabels = {
  fast_period: '快线周期',
  slow_period: '慢线周期',
  signal_period: '信号周期',
  period: '周期',
  std_dev: '标准差',
  oversold: '超卖阈值',
  overbought: '超买阈值',
  timeframe: '交易周期',
  timeframes: '交易周期',
  multiplier: '乘数',
  atr_period: 'ATR周期',
  k_period: 'K周期',
  k_smooth: 'K平滑',
  d_smooth: 'D平滑',
  volume_ma_period: '成交量MA周期',
  volume_ratio: '成交量倍数',
  lookback: '回看周期',
  trend_period: '趋势周期',
  ema_period: 'EMA周期',
  boll_period: '布林周期',
  boll_std: '布林标准差',
  vol_ma_period: '成交量MA周期',
  vol_ratio: '成交量倍数',
  macd_fast: 'MACD快线',
  macd_slow: 'MACD慢线',
  macd_signal: 'MACD信号',
  rsi_period: 'RSI周期',
  peak_window: '峰值窗口',
  tp_pct: '止盈比例(%)',
  sl_pct: '止损比例(%)',
  trail_activate: '移动止盈激活(%)',
  trail_callback: '回调点数',
  cooldown_minutes: '冷却时间(分钟)',
  size: '下单张数',
  size_mode: '下单模式',
  inst_id: '交易品种',
  use_regime_filter: '市场状态过滤',
  funding_threshold: '资金费率阈值',
  min_interval: '最小间隔(小时)',
  period1: '周期1',
  period2: '周期2',
  period3: '周期3',
  period4: '周期4',
}

function formatParamLabel(key) {
  return paramLabels[key] || key
}

function getParamMin(key) {
  if (key.includes('period') || key.includes('window') || key.includes('lookback')) return 1
  if (key.includes('ratio') || key.includes('multiplier')) return 0.1
  if (key === 'tp_pct' || key === 'sl_pct') return 0
  if (key === 'trail_activate') return 0
  if (key === 'trail_callback') return 0
  if (key === 'size') return 0.01
  return 0
}

function getParamMax(key) {
  if (key.includes('period') || key.includes('window') || key.includes('lookback')) return 500
  if (key.includes('ratio')) return 10
  if (key === 'multiplier') return 10
  if (key === 'tp_pct' || key === 'sl_pct') return 100
  if (key === 'trail_activate') return 50
  if (key === 'trail_callback') return 1000
  if (key === 'size') return 1000
  return 10000
}

function getParamStep(key) {
  if (key.includes('period') || key.includes('window') || key.includes('lookback')) return 1
  if (key === 'tp_pct' || key === 'sl_pct' || key === 'trail_activate') return 0.1
  if (key === 'size') return 0.01
  return 0.1
}

function getStrategyName(type) {
  const tpl = strategyTemplates.value.find(t => t.type === type)
  return tpl ? tpl.name : type
}

function toggleStrategyExpand(idx) {
  robotForm.value.strategyConfigs[idx].expanded = !robotForm.value.strategyConfigs[idx].expanded
}

// 构建策略配置列表（包含所有可用策略，可选择启用）
function buildStrategyConfigs(selectedStrategies = []) {
  return strategyTemplates.value.map(tpl => {
    // 查找是否已选中此策略
    const selected = selectedStrategies.find(s => {
      if (typeof s === 'string') return s === tpl.type
      return s.type === tpl.type
    })

    return {
      type: tpl.type,
      enabled: !!selected,
      expanded: false,
      params: selected && typeof selected === 'object' && selected.params
        ? { ...tpl.default_params, ...selected.params }
        : { ...tpl.default_params }
    }
  })
}

function openRobotCreateDialog() {
  robotDialogMode.value = 'create'
  robotEditId.value = null
  robotForm.value = {
    name: '',
    description: '',
    initial_capital: 10000,
    size_mode: 'fixed',
    size: 1,
    size_pct: 10,
    leverage: 10,
    strategies: [],
    strategyConfigs: buildStrategyConfigs([]),
    sort_order: robots.value.length,
  }
  robotDialogVisible.value = true
}

function openRobotEditDialog(robot) {
  robotDialogMode.value = 'edit'
  robotEditId.value = robot.id
  // 解析已保存的策略配置
  let savedStrategies = []
  try {
    savedStrategies = Array.isArray(robot.strategies)
      ? robot.strategies.map(s => typeof s === 'string' ? { type: s, params: {} } : s)
      : []
  } catch {
    savedStrategies = []
  }

  robotForm.value = {
    name: robot.name,
    description: robot.description || '',
    initial_capital: robot.initial_capital,
    size_mode: robot.size_mode || 'fixed',
    size: robot.size || 1,
    size_pct: robot.size_pct || 10,
    leverage: robot.leverage || 10,
    strategies: robot.strategies || [],
    strategyConfigs: buildStrategyConfigs(savedStrategies),
    sort_order: robot.sort_order,
  }
  robotDialogVisible.value = true
}

async function saveRobot() {
  if (!robotForm.value.name.trim()) {
    ElMessage.warning('请输入机器人名称')
    return
  }

  // 提取启用的策略配置
  const enabledStrategies = robotForm.value.strategyConfigs
    .filter(s => s.enabled)
    .map(s => ({
      type: s.type,
      params: s.params
    }))

  const payload = {
    name: robotForm.value.name,
    description: robotForm.value.description,
    initial_capital: robotForm.value.initial_capital,
    size_mode: robotForm.value.size_mode,
    size: robotForm.value.size,
    size_pct: robotForm.value.size_pct,
    leverage: robotForm.value.leverage,
    strategies: enabledStrategies,
    sort_order: robotForm.value.sort_order,
  }

  try {
    if (robotDialogMode.value === 'create') {
      await axios.post('/robots', payload)
      ElMessage.success('创建成功')
    } else {
      await axios.put(`/robots/${robotEditId.value}`, payload)
      ElMessage.success('更新成功')
    }
    robotDialogVisible.value = false
    await loadRobots()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function toggleRobot(robot) {
  try {
    await axios.post(`/robots/${robot.id}/toggle`, { is_running: !robot.is_running })
    robot.is_running = !robot.is_running
    ElMessage.success(robot.is_running ? '已启动' : '已停止')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function deleteRobot(robot) {
  try {
    await ElMessageBox.confirm(`确定要删除机器人"${robot.name}"吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await axios.delete(`/robots/${robot.id}`)
    ElMessage.success('已删除')
    await loadRobots()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

// ═══ 初始化 ═══
onMounted(async () => {
  // 先检查是否是管理员
  try {
    await loadOverview()
  } catch (e) {
    if (e?.status === 403) {
      ElMessage.error('需要管理员权限')
      router.push('/dashboard')
      return
    }
  }
  loadConfig()
  loadNotifyConfig()
  loadAvailableStrategies()  // 加载可用策略类型列表
  loadStrategyTemplates()    // 加载策略模板（用于机器人管理）
})

// Tab 切换时加载对应数据
import { watch } from 'vue'
watch(activeTab, (tab) => {
  if (tab === 'users') loadUsers()
  if (tab === 'trades') loadTrades()
  if (tab === 'strategies') loadStrategies()
  if (tab === 'logs') loadLogs()
  if (tab === 'overview') loadOverview()
  if (tab === 'activities') loadActivities()
  if (tab === 'robots') loadRobots()
})
</script>

<style scoped>
.admin-page {
  padding: 4px;
  max-width: 1400px;
  margin: 0 auto;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.admin-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 0;
}

.admin-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f56c6c, #e63946);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
}

/* Tab 样式 */
.admin-tabs {
  border-radius: 12px;
  overflow: hidden;
}

.admin-tabs :deep(.el-tabs__content) {
  padding: 20px;
}

/* ═══ 统计卡片 ═══ */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  border-radius: 12px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

.stat-card.blue { border-left: 4px solid #409eff; }
.stat-card.green { border-left: 4px solid #67c23a; }
.stat-card.orange { border-left: 4px solid #e6a23c; }
.stat-card.red { border-left: 4px solid #f56c6c; }

.stat-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.stat-total {
  font-size: 14px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.stat-sub {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 8px;
}

/* ═══ Panel ═══ */
.panel {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 16px 0;
}

/* ═══ 工具栏 ═══ */
.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 6px;
}

.toolbar-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.toolbar-total {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

/* ═══ 状态列表 ═══ */
.status-items {
  display: flex;
  gap: 40px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.status-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.status-value.danger {
  color: #f56c6c;
}

/* ═══ 交易统计 ═══ */
.trade-stats {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
  padding: 16px;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
}

.ts-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ts-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.ts-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* ═══ 配置表单 ═══ */
.config-form {
  max-width: 800px;
}

/* ═══ API 列表 ═══ */
.api-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.api-group {
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--el-text-color-regular);
}

.api-prefix {
  display: inline-block;
  width: 50px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  margin-right: 8px;
  background: #ecf5ff;
  color: #409eff;
}

/* ═══ 颜色 ═══ */
.up { color: #f56c6c; }
.down { color: #67c23a; }

.empty-tip {
  text-align: center;
  padding: 40px;
  color: var(--el-text-color-placeholder);
  font-size: 14px;
}

/* ═══ 邮件通知 ═══ */
.panel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.settings-form {
  max-width: 400px;
}

.test-result {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-top: 12px;
}
.test-result.success { background: #f0f9eb; color: #67c23a; }
.test-result.error { background: #fef0f0; color: #f56c6c; }

.api-tips {
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  color: #64748b;
}
.api-tips p { margin: 4px 0; }
.api-tips a { color: #3b82f6; }

.notify-scenes {
  padding: 8px 0;
}
.notify-scene-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.notify-scene-item:last-child { border-bottom: none; }
.scene-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.scene-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.scene-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

/* ═══ 创建策略表单 ═══ */
.create-form {
  max-width: 560px;
}

.hint-label {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

/* ═══ 机器人策略配置 ═══ */
.strategy-config-list {
  width: 100%;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
}

.strategy-config-item {
  border-bottom: 1px solid var(--border-secondary);
}

.strategy-config-item:last-child {
  border-bottom: none;
}

.strategy-header {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  background: var(--bg-secondary);
  transition: background 0.2s;
}

.strategy-header:hover {
  background: var(--bg-hover);
}

.strategy-name {
  flex: 1;
  margin-left: 10px;
  font-weight: 500;
  color: var(--text-primary);
}

.expand-icon {
  transition: transform 0.2s;
  color: var(--text-muted);
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.strategy-params {
  padding: 12px 16px;
  background: var(--bg-card);
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
}

.strategy-params.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 280px;
}

.param-label {
  width: 100px;
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.robot-actions {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
}

.action-btn {
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  background: transparent;
  transition: all 0.2s;
}

.action-btn.edit {
  color: #3b82f6;
}

.action-btn.edit:hover {
  background: rgba(59, 130, 246, 0.1);
}

.action-btn.start {
  color: #22c55e;
}

.action-btn.start:hover {
  background: rgba(34, 197, 94, 0.1);
}

.action-btn.stop {
  color: #f59e0b;
}

.action-btn.stop:hover {
  background: rgba(245, 158, 11, 0.1);
}

.action-btn.delete {
  color: #ef4444;
}

.action-btn.delete:hover {
  background: rgba(239, 68, 68, 0.1);
}

@media (max-width: 600px) {
  .strategy-params {
    grid-template-columns: 1fr;
  }
}

</style>
