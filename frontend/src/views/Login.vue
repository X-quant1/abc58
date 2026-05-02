<template>
  <div class="login-page" :class="{ dark: isDark, light: !isDark }" :style="pageBgStyle">
    <!-- 主题切换按钮 -->
    <button class="theme-toggle" :class="{ light: !isDark }" @click="toggleTheme">
      <svg v-if="isDark" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      <span>{{ isDark ? '日间' : '夜间' }}</span>
    </button>

    <div class="login-wrapper">
      <!-- 品牌标题 -->
      <div class="brand-title">
        <span :class="{ 'dark-text': isDark, 'light-text': !isDark }">BTC Quant</span>
      </div>

      <!-- 主卡片 -->
      <div class="login-card" :style="cardShadow">
        <!-- 左侧品牌面板 -->
        <div class="brand-panel">
          <div class="brand-circle c1"></div>
          <div class="brand-circle c2"></div>
          <svg class="brand-grid" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="grid-pattern" width="32" height="32" patternUnits="userSpaceOnUse">
                <path d="M 32 0 L 0 0 0 32" fill="none" stroke="white" stroke-width="0.5"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid-pattern)"/>
          </svg>

          <div class="brand-content">
            <div class="brand-logo">
              <div class="logo-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
              </div>
              <span class="logo-text">BTC Quant</span>
            </div>
            <h2 class="brand-headline">专业量化交易<br/>策略管理平台</h2>
            <p class="brand-desc">连接 OKX 交易所，多策略自动执行，<br/>让量化更简单高效。</p>
          </div>

          <div class="brand-features">
            <div v-for="f in features" :key="f.label" class="feature-item">
              <div class="feature-icon"><component :is="f.icon" /></div>
              <span>{{ f.label }}</span>
            </div>
          </div>

          <div class="brand-footer">
            <div class="brand-divider"></div>
            <p>© 2026 BTC Quant · 专业 · 稳定 · 安全</p>
          </div>
        </div>

        <!-- 右侧表单区 -->
        <div class="form-panel" :style="{ background: formBg }">
          <!-- ==================== 登录模式 ==================== -->
          <template v-if="page === 'login'">
            <div class="form-header">
              <h3 :style="{ color: titleColor }">欢迎回来</h3>
              <p class="form-subtitle" :style="{ color: subtitleColor }">登录您的账号，开始自动化交易</p>
            </div>

            <!-- 登录锁定提示 -->
            <div v-if="lockCountdown > 0" class="lock-notice" :class="{ dark: isDark }">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <span>登录已锁定，请 {{ lockCountdown }} 秒后重试</span>
            </div>

            <!-- 密码登录 / 验证码登录 切换 -->
            <div class="login-tabs" :class="{ dark: isDark }">
              <button
                v-for="tab in loginTabs"
                :key="tab.value"
                class="login-tab"
                :class="{ active: loginMode === tab.value, dark: isDark }"
                @click="switchLoginMode(tab.value)"
              >{{ tab.label }}</button>
            </div>

            <!-- 密码登录 -->
            <el-form v-show="loginMode === 'password'" ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-position="top" hide-required-asterisk>
              <el-form-item prop="email" style="margin-top: 2px">
                <el-input v-model="pwdForm.email" placeholder="邮箱地址或用户名" :prefix-icon="User" size="large" :style="inputStyle" @input="pwdEmailError = ''" />
                <Transition name="err-fade">
                  <div v-if="pwdEmailError" class="field-error">{{ pwdEmailError }}</div>
                </Transition>
              </el-form-item>
              <el-form-item prop="password" style="margin-top: 2px">
                <el-input v-model="pwdForm.password" type="password" placeholder="密码" :prefix-icon="Lock" size="large" show-password :style="inputStyle" :disabled="lockCountdown > 0" @input="pwdPasswordError = ''" @keyup.enter="handlePwdLogin" />
                <Transition name="err-fade">
                  <div v-if="pwdPasswordError" class="field-error">{{ pwdPasswordError }}</div>
                </Transition>
              </el-form-item>
              <el-form-item prop="agree" style="margin-bottom: 10px; margin-top: -5px">
                <div style="width: 100%;">
                  <div style="display: flex; align-items: center; margin-bottom: -6px;">
                    <el-checkbox v-model="pwdForm.remember" :style="{ color: subtitleColor }">
                      <span style="font-size: 11px">记住我</span>
                    </el-checkbox>
                  </div>
                  <div style="display: flex; align-items: center; width: 100%; margin-top: -1px;">
                    <el-checkbox v-model="pwdForm.agree" :style="{ color: subtitleColor }" @change="pwdAgreeError = ''">
                      <span style="font-size: 11px">登录即同意 <button class="link-btn" @click.prevent="showAgreement = true">《用户协议》</button></span>
                    </el-checkbox>
                    <span style="flex: 1;"></span>
                    <button class="link-btn" style="font-size: 11px; flex-shrink: 0; padding: 4px 8px; margin: -16px -4px 0; border-radius: 4px;" @click="goPage('forgot')">忘记密码？</button>
                  </div>
                  <Transition name="err-fade">
                    <div v-if="pwdAgreeError" class="field-error" style="margin-top: -3px">{{ pwdAgreeError }}</div>
                  </Transition>
                </div>
              </el-form-item>
              <el-button type="primary" size="large" :loading="loading" :disabled="lockCountdown > 0" class="submit-btn" @click="handlePwdLogin">
                {{ lockCountdown > 0 ? `${lockCountdown}s 后重试` : '登 录' }}
                <svg v-if="!loading && lockCountdown === 0" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left:6px"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </el-button>
            </el-form>

            <!-- 验证码登录 -->
            <el-form v-show="loginMode === 'code'" ref="codeFormRef" :model="codeForm" :rules="codeRules" label-position="top" hide-required-asterisk>
              <el-form-item prop="email">
                <el-input v-model="codeForm.email" placeholder="邮箱地址" :prefix-icon="Message" size="large" :style="inputStyle" :disabled="lockCountdown > 0">
                  <template #suffix>
                    <button class="code-send-btn-inline" :class="{ dark: isDark }" :disabled="!codeForm.email || codeCountdown.running || codeSending" @click="sendCode('login')" :style="{ color: (!codeForm.email || codeCountdown.running || codeSending) ? '#404040' : '#3b82f6', fontWeight: 700 }">
                      {{ codeCountdown.running ? `${codeCountdown.sec}s 重发` : codeSending ? '发送中...' : '获取验证码' }}
                    </button>
                  </template>
                </el-input>
              </el-form-item>
              <div style="margin-bottom: 10px">
                <p class="code-hint" :style="{ color: subtitleColor }">输入发送至邮箱的 6 位验证码</p>
                <div class="code-inputs">
                  <input
                    v-for="i in 6" :key="i"
                    ref="codeInputRefs"
                    type="text"
                    maxlength="1"
                    class="code-input"
                    :class="{ dark: isDark }"
                    :value="codeDigits[i - 1]"
                    :disabled="lockCountdown > 0"
                    @input="onCodeInput($event, i - 1)"
                    @keydown.backspace="onCodeBackspace($event, i - 1)"
                    @focus="onCodeFocus($event, i - 1)"
                  />
                </div>
              </div>
              <el-form-item prop="agree" style="margin-bottom: 6px">
                <el-checkbox v-model="codeForm.agree" :style="{ color: subtitleColor }">
                  <span style="font-size: 11px">登录即同意 <button class="link-btn" @click.prevent="showAgreement = true">《用户协议》</button></span>
                </el-checkbox>
              </el-form-item>
              <el-button type="primary" size="large" :loading="loading" :disabled="lockCountdown > 0" class="submit-btn" @click="handleCodeLogin">
                {{ lockCountdown > 0 ? `${lockCountdown}s 后重试` : '登 录' }}
                <svg v-if="!loading && lockCountdown === 0" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left:6px"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </el-button>
            </el-form>
          </template>

          <!-- ==================== 注册模式 ==================== -->
          <template v-if="page === 'register'">
            <div class="form-header">
              <h3 :style="{ color: titleColor }">{{ regStep === 1 ? '创建账号' : '设置信息' }}</h3>
              <p class="form-subtitle" :style="{ color: subtitleColor }">{{ regStep === 1 ? '输入邮箱并完成验证' : '设置您的用户名和密码' }}</p>
            </div>

            <!-- 步骤指示器 -->
            <div class="step-bar">
              <div class="step-dot" :class="{ active: regStep >= 1, done: regStep > 1 }"><span>1</span></div>
              <div class="step-line" :class="{ active: regStep > 1 }"></div>
              <div class="step-dot" :class="{ active: regStep >= 2 }"><span>2</span></div>
            </div>

            <!-- 步骤1: 邮箱 + 验证码 -->
            <el-form v-show="regStep === 1" ref="regStep1Ref" :model="regForm" :rules="regStep1Rules" label-position="top" hide-required-asterisk>
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="regForm.email" placeholder="邮箱地址" :prefix-icon="Message" size="large" :style="inputStyle">
                  <template #suffix>
                    <button class="code-send-btn-inline" :class="{ dark: isDark }" :disabled="!regForm.email || regCodeCountdown.running || codeSending" @click="sendCode('register')" :style="{ color: (!regForm.email || regCodeCountdown.running || codeSending) ? '#404040' : '#3b82f6', fontWeight: 700 }">
                      {{ regCodeCountdown.running ? `${regCodeCountdown.sec}s` : codeSending ? '...' : '获取验证码' }}
                    </button>
                  </template>
                </el-input>
              </el-form-item>
              <div style="margin-bottom: 10px">
                <p class="code-hint" :style="{ color: subtitleColor }">输入发送至邮箱的 6 位验证码</p>
                <div class="code-inputs">
                  <input
                    v-for="i in 6" :key="i"
                    ref="regCodeInputRefs"
                    type="text"
                    maxlength="1"
                    class="code-input"
                    :class="{ dark: isDark }"
                    :value="regCodeDigits[i - 1]"
                    @input="onRegCodeInput($event, i - 1)"
                    @keydown.backspace="onRegCodeBackspace($event, i - 1)"
                    @focus="onRegCodeFocus($event, i - 1)"
                  />
                </div>
              </div>
              <el-button type="primary" size="large" class="submit-btn" @click="regNextStep">
                下一步
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left:6px"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </el-button>
            </el-form>

            <!-- 步骤2: 用户名 + 密码 -->
            <el-form v-show="regStep === 2" ref="regStep2Ref" :model="regForm" :rules="regStep2Rules" label-position="top" hide-required-asterisk>
              <el-form-item label="用户名" prop="username">
                <el-input v-model="regForm.username" placeholder="3-30位字母、数字或下划线" :prefix-icon="User" size="large" :style="inputStyle" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input v-model="regForm.password" type="password" placeholder="至少6位密码" :prefix-icon="Lock" size="large" show-password :style="inputStyle" />
              </el-form-item>
              <el-form-item label="确认密码" prop="confirmPassword">
                <el-input v-model="regForm.confirmPassword" type="password" placeholder="再次输入密码" :prefix-icon="Lock" size="large" show-password :style="inputStyle" @keyup.enter="handleRegister" />
              </el-form-item>
              <div class="step-back-row">
                <button class="link-btn" @click="regStep = 1">← 返回上一步</button>
              </div>
              <el-button type="primary" size="large" :loading="loading" class="submit-btn" @click="handleRegister">
                {{ loading ? '注册中...' : '注 册' }}
              </el-button>
            </el-form>
          </template>

          <!-- ==================== 忘记密码 ==================== -->
          <template v-if="page === 'forgot'">
            <div class="form-header">
              <h3 :style="{ color: titleColor }">重置密码</h3>
              <p class="form-subtitle" :style="{ color: subtitleColor }">通过邮箱验证码重置您的密码</p>
            </div>

            <el-form ref="forgotFormRef" :model="forgotForm" :rules="forgotRules" label-position="top" hide-required-asterisk>
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="forgotForm.email" placeholder="请输入注册时使用的邮箱" :prefix-icon="Message" size="large" :style="inputStyle">
                  <template #suffix>
                    <button class="code-send-btn-inline" :class="{ dark: isDark }" :disabled="!forgotForm.email || forgotCodeCountdown.running || codeSending" @click="sendCode('reset')" :style="{ color: (!forgotForm.email || forgotCodeCountdown.running || codeSending) ? '#404040' : '#3b82f6', fontWeight: 700 }">
                      {{ forgotCodeCountdown.running ? `${forgotCodeCountdown.sec}s` : codeSending ? '...' : '获取验证码' }}
                    </button>
                  </template>
                </el-input>
              </el-form-item>
              <div style="margin-bottom: 10px">
                <p class="code-hint" :style="{ color: subtitleColor }">输入发送至邮箱的 6 位验证码</p>
                <div class="code-inputs">
                  <input
                    v-for="i in 6" :key="i"
                    ref="forgotCodeInputRefs"
                    type="text"
                    maxlength="1"
                    class="code-input"
                    :class="{ dark: isDark }"
                    :value="forgotCodeDigits[i - 1]"
                    @input="onForgotCodeInput($event, i - 1)"
                    @keydown.backspace="onForgotCodeBackspace($event, i - 1)"
                    @focus="onForgotCodeFocus($event, i - 1)"
                  />
                </div>
              </div>
              <el-form-item label="新密码" prop="newPassword">
                <el-input v-model="forgotForm.newPassword" type="password" placeholder="至少6位新密码" :prefix-icon="Lock" size="large" show-password :style="inputStyle" />
              </el-form-item>
              <div class="step-back-row">
                <button class="link-btn" @click="goPage('login')">← 返回登录</button>
              </div>
              <el-button type="primary" size="large" :loading="loading" class="submit-btn" @click="handleResetPassword">
                {{ loading ? '提交中...' : '重置密码' }}
              </el-button>
            </el-form>
          </template>

          <!-- ==================== 分割线 + 切换（仅登录/注册显示） ==================== -->
          <template v-if="page !== 'forgot'">
            <div class="divider-row">
              <div class="divider-line"></div>
              <span class="divider-text">或</span>
              <div class="divider-line"></div>
            </div>
            <p class="switch-text" :style="{ color: subtitleColor }">
              <template v-if="page === 'login'">还没有账号？<button class="link-btn" @click="goPage('register')">立即注册</button></template>
              <template v-else>已有账号？<button class="link-btn" @click="goPage('login')">返回登录</button></template>
            </p>
          </template>
        </div>
      </div>
    </div>

    <!-- ==================== 用户协议弹窗 ==================== -->
    <el-dialog v-model="showAgreement" title="用户协议" width="520px" :close-on-click-modal="false" class="agreement-dialog">
      <div class="agreement-content">
        <h4>1. 服务说明</h4>
        <p>BTC Quant 是一个量化交易策略管理平台，为用户提供自动化交易策略管理、回测分析等服务。用户应充分了解量化交易风险，自行承担交易结果。</p>
        <h4>2. 账户安全</h4>
        <p>用户应妥善保管账户信息及 API 密钥，因用户自身原因导致的信息泄露，平台不承担任何责任。平台采用加密存储技术保护用户的 API 密钥。</p>
        <h4>3. 风险提示</h4>
        <p>量化交易存在市场风险、技术风险等。历史回测收益不代表未来表现，用户应根据自身风险承受能力谨慎决策。平台不对交易盈亏承担任何责任。</p>
        <h4>4. 免责声明</h4>
        <p>因不可抗力、交易所系统故障、网络中断等原因导致的服务中断或数据异常，平台不承担责任。平台有权在提前通知的情况下对服务进行调整。</p>
        <h4>5. 隐私保护</h4>
        <p>平台重视用户隐私保护，未经用户授权不会向第三方提供用户的个人信息及交易数据。具体隐私政策详见《隐私政策》。</p>
      </div>
      <template #footer>
        <el-button @click="showAgreement = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, shallowRef, markRaw, h, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const loading = ref(false)
const codeSending = ref(false)
const page = ref('login')       // login | register | forgot
const loginMode = ref('password') // password | code
const showAgreement = ref(false)

// 登录失败锁定
const MAX_FAIL = 5
const LOCK_SEC = 300
const failCount = ref(0)
const lockCountdown = ref(0)
let lockTimer = null

// ---- 登录页表单引用 ----
const pwdFormRef = ref(null)
const codeFormRef = ref(null)

// 密码登录表单
const pwdForm = reactive({ email: '', password: '', remember: false, agree: false })
const pwdEmailError = ref('')
const pwdPasswordError = ref('')
const pwdAgreeError = ref('')
const pwdRules = {
  email: [{ required: true, message: '请输入邮箱或用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  agree: [{ validator: (_, v) => v ? Promise.resolve() : Promise.reject('请先阅读并同意用户协议'), trigger: 'change' }]
}

// 验证码登录表单
const codeForm = reactive({ email: '', agree: false })
const codeDigits = reactive(['', '', '', '', '', ''])
const codeInputRefs = ref([])
const codeRules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式有误', trigger: 'blur' }],
  agree: [{ validator: (_, v) => v ? Promise.resolve() : Promise.reject('请先阅读并同意用户协议'), trigger: 'change' }]
}

// 验证码倒计时
function makeCountdown() {
  const state = reactive({ running: false, sec: 0 })
  let timer = null
  return {
    state,
    start(sec = 60) {
      if (state.running) return
      state.running = true
      state.sec = sec
      timer = setInterval(() => {
        state.sec--
        if (state.sec <= 0) { clearInterval(timer); timer = null; state.running = false }
      }, 1000)
    }
  }
}
const codeCountdown = makeCountdown()
const regCodeCountdown = makeCountdown()
const forgotCodeCountdown = makeCountdown()

// 注册表单
const regStep = ref(1)
const regForm = reactive({ email: '', username: '', password: '', confirmPassword: '' })
const regCodeDigits = reactive(['', '', '', '', '', ''])
const regCodeInputRefs = ref([])
const regStep1Ref = ref(null)
const regStep2Ref = ref(null)

const regStep1Rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式有误', trigger: 'blur' }]
}
const regStep2Rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度 3-30 位', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '只允许字母、数字和下划线', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  confirmPassword: [{ required: true, message: '请确认密码', trigger: 'blur' }, { validator: (_, v) => v === regForm.password ? Promise.resolve() : Promise.reject('两次输入的密码不一致'), trigger: 'blur' }]
}

// 忘记密码表单
const forgotFormRef = ref(null)
const forgotForm = reactive({ email: '', newPassword: '' })
const forgotCodeDigits = reactive(['', '', '', '', '', ''])
const forgotCodeInputRefs = ref([])
const forgotRules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式有误', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '密码至少 6 位', trigger: 'blur' }]
}

// ---- 登录模式切换 ----
const loginTabs = [
  { label: '密码登录', value: 'password' },
  { label: '验证码登录', value: 'code' }
]
function switchLoginMode(mode) {
  loginMode.value = mode
}

// ---- 页面切换 ----
function goPage(p) {
  page.value = p
  if (p === 'login') { regStep.value = 1; lockCountdown.value = 0 }
  if (p === 'register') regStep.value = 1
}

// ---- 验证码输入通用逻辑 ----
function handleCodeDigit(e, index, digits, refs, cb) {
  const val = e.target.value.replace(/[^0-9]/g, '')
  e.target.value = val
  digits[index] = val
  if (val && index < 5) {
    nextTick(() => { const arr = Array.isArray(refs.value) ? refs.value : []; arr[index + 1]?.focus() })
  }
  cb?.()
}

function handleCodeBackspace(e, index, digits, refs) {
  if (!e.target.value && index > 0) {
    digits[index] = ''
    nextTick(() => { const arr = Array.isArray(refs.value) ? refs.value : []; arr[index - 1]?.focus() })
  } else {
    digits[index] = ''
  }
}

function handleCodeFocus(e, index, digits) {
  e.target.select()
}

// 登录验证码
const onCodeInput = (e, i) => handleCodeDigit(e, i, codeDigits, codeInputRefs)
const onCodeBackspace = (e, i) => handleCodeBackspace(e, i, codeDigits, codeInputRefs)
const onCodeFocus = (e, i) => handleCodeFocus(e, i, codeDigits)

// 注册验证码
const onRegCodeInput = (e, i) => handleCodeDigit(e, i, regCodeDigits, regCodeInputRefs)
const onRegCodeBackspace = (e, i) => handleCodeBackspace(e, i, regCodeDigits, regCodeInputRefs)
const onRegCodeFocus = (e, i) => handleCodeFocus(e, i, regCodeDigits)

// 忘记密码验证码
const onForgotCodeInput = (e, i) => handleCodeDigit(e, i, forgotCodeDigits, forgotCodeInputRefs)
const onForgotCodeBackspace = (e, i) => handleCodeBackspace(e, i, forgotCodeDigits, forgotCodeInputRefs)
const onForgotCodeFocus = (e, i) => handleCodeFocus(e, i, forgotCodeDigits)

// ---- 发送验证码 ----
async function sendCode(purpose) {
  let email = ''
  if (purpose === 'login') email = codeForm.email
  else if (purpose === 'register') email = regForm.email
  else email = forgotForm.email
  if (!email) return
  codeSending.value = true
  try {
    await axios.post('/api/auth/send-code', { email, purpose })
    ElMessage.success('验证码已发送，请查收邮箱')
    if (purpose === 'login') codeCountdown.start(60)
    else if (purpose === 'register') regCodeCountdown.start(60)
    else forgotCodeCountdown.start(60)
  } catch (e) {
    const detail = e.response?.data?.detail || '发送失败，请稍后重试'
    ElMessage.error(detail)
  } finally {
    codeSending.value = false
  }
}

function getCodeStr(digits) { return digits.join('') }

// ---- 密码登录 ----
async function handlePwdLogin() {
  pwdEmailError.value = ''
  pwdPasswordError.value = ''
  pwdAgreeError.value = ''
  if (!pwdForm.email) { pwdEmailError.value = '请输入邮箱或用户名'; return }
  if (!pwdForm.password) { pwdPasswordError.value = '请输入密码'; return }
  if (!pwdForm.agree) { pwdAgreeError.value = '请先阅读并同意用户协议'; return }
  loading.value = true
  try {
    const { data } = await axios.post('/api/auth/login', { email: pwdForm.email, password: pwdForm.password })
    if (data.access_token) {
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user || {}))
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  } catch {
    failCount.value++
    if (failCount.value >= MAX_FAIL) startLock()
    ElMessage.error('账号或密码错误')
  } finally {
    loading.value = false
  }
}

// ---- 验证码登录 ----
async function handleCodeLogin() {
  try { await codeFormRef.value.validate() } catch { return }
  if (!codeForm.agree) { ElMessage.warning('请先阅读并同意用户协议'); return }
  const code = getCodeStr(codeDigits)
  if (code.length !== 6) { ElMessage.warning('请输入完整验证码'); return }
  loading.value = true
  try {
    const { data } = await axios.post('/api/auth/login-by-code', { email: codeForm.email, code })
    if (data.access_token) {
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user || {}))
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  } catch (e) {
    const detail = e.response?.data?.detail || '验证码错误或已过期'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

// ---- 注册：步骤1→2 ----
async function regNextStep() {
  try { await regStep1Ref.value.validate() } catch { return }
  const code = getCodeStr(regCodeDigits)
  if (code.length !== 6) { ElMessage.warning('请输入完整验证码'); return }
  regStep.value = 2
}

// ---- 注册提交 ----
async function handleRegister() {
  try { await regStep2Ref.value.validate() } catch { return }
  const code = getCodeStr(regCodeDigits)
  loading.value = true
  try {
    const payload = { email: regForm.email, username: regForm.username, password: regForm.password, code, nickname: regForm.username }
    const { data } = await axios.post('/api/auth/register', payload)
    if (data.access_token) {
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user || {}))
      ElMessage.success('注册成功，欢迎使用！')
      router.push('/dashboard')
    }
  } catch (e) {
    const detail = e.response?.data?.detail || '注册失败，请稍后重试'
    if (detail.includes('验证码')) {
      regStep.value = 1
      for (let i = 0; i < 6; i++) regCodeDigits[i] = ''
    }
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

// ---- 重置密码 ----
async function handleResetPassword() {
  try { await forgotFormRef.value.validate() } catch { return }
  const code = getCodeStr(forgotCodeDigits)
  if (code.length !== 6) { ElMessage.warning('请输入完整验证码'); return }
  loading.value = true
  try {
    await axios.post('/api/auth/reset-password', { email: forgotForm.email, code, new_password: forgotForm.newPassword })
    ElMessage.success('密码重置成功，请重新登录')
    goPage('login')
  } catch (e) {
    const detail = e.response?.data?.detail || '验证码错误或已过期'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

// ---- 登录锁定 ----
function startLock() {
  lockCountdown.value = LOCK_SEC
  lockTimer = setInterval(() => {
    lockCountdown.value--
    if (lockCountdown.value <= 0) { clearInterval(lockTimer); lockTimer = null; failCount.value = 0 }
  }, 1000)
}

// ---- 功能特性图标 ----
const IconShield = markRaw({ render() { return h('svg', { xmlns:'http://www.w3.org/2000/svg', width:'11', height:'11', viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', 'stroke-width':'2' }, [h('path', { d:'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' })]) }})
const IconZap = markRaw({ render() { return h('svg', { xmlns:'http://www.w3.org/2000/svg', width:'11', height:'11', viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', 'stroke-width':'2' }, [h('polygon', { points:'13 2 3 14 12 14 11 22 21 10 12 10 13 2' })]) }})
const IconBarChart = markRaw({ render() { return h('svg', { xmlns:'http://www.w3.org/2000/svg', width:'11', height:'11', viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', 'stroke-width':'2' }, [h('line',{x1:'18',y1:'20',x2:'18',y2:'10'}), h('line',{x1:'12',y1:'20',x2:'12',y2:'4'}), h('line',{x1:'6',y1:'20',x2:'6',y2:'14'})]) }})

const features = [
  { icon: IconShield, label: 'API 密钥加密存储' },
  { icon: IconZap, label: '15种量化策略引擎' },
  { icon: IconBarChart, label: '124天历史回测验证' }
]

// ---- 主题切换 (暗色/亮色) ----
const isDark = ref(localStorage.getItem('theme') === 'dark')

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  // 同步 body 背景色（Login 页面独立于 Layout）
  document.body.style.background = isDark.value ? '#000' : '#f5f5f5'
}

const darkTheme = {
  pageBg: '#000',
  formBg: '#1a1a1a',
  titleColor: '#fff',
  subtitleColor: '#737373',
  cardShadow: '0 25px 60px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.06)',
}
const lightTheme = {
  pageBg: '#f5f5f5',
  formBg: '#ffffff',
  titleColor: '#111',
  subtitleColor: '#737373',
  cardShadow: '0 25px 60px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.06)',
}

const pageBgStyle = computed(() => ({ background: isDark.value ? darkTheme.pageBg : lightTheme.pageBg }))
const formBg = computed(() => isDark.value ? darkTheme.formBg : lightTheme.formBg)
const titleColor = computed(() => isDark.value ? darkTheme.titleColor : lightTheme.titleColor)
const subtitleColor = computed(() => isDark.value ? darkTheme.subtitleColor : lightTheme.subtitleColor)
const cardShadow = computed(() => ({ boxShadow: isDark.value ? darkTheme.cardShadow : lightTheme.cardShadow }))
const inputStyle = shallowRef({ borderRadius: '10px' })
</script>

<style scoped>
/* ===== 主题系统：暗色 (默认) + 亮色 ===== */

/* 页面基础 */
.login-page {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  overflow: hidden;
  transition: background 0.35s ease;
}
.login-page.dark { background: #000; }
.login-page.light { background: #f5f5f5; }

/* 主题切换按钮 */
.theme-toggle {
  position: fixed; top: 20px; right: 20px;
  height: 40px; padding: 0 14px; font-size: 13px; font-weight: 600;
  backdrop-filter: blur(12px);
  cursor: pointer; display: flex; align-items: center; gap: 8px;
  transition: all 0.3s; z-index: 100;
  border-radius: 20px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
  color: #a3a3a3;
}
.theme-toggle:hover { background: rgba(255,255,255,0.12); color: #fff; }
.theme-toggle.light {
  background: rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.08);
  color: #737373;
}
.theme-toggle.light:hover { background: rgba(0,0,0,0.08); color: #111; }

.login-wrapper {
  display: flex; flex-direction: column; align-items: center;
  width: auto; margin: 0;
}

.brand-title { margin-bottom: 20px; }
.brand-title span { font-size: 28px; font-weight: 700; letter-spacing: -0.6px; }
.brand-title .dark-text { color: #fff; }
.brand-title .light-text { color: #111; }

/* 主卡片 */
.login-card {
  display: flex; flex-direction: row; width: 100%;
  border-radius: 16px; transition: all 0.35s ease;
  overflow: hidden;
}
.login-page.dark .login-card {
  border: 1px solid rgba(255,255,255,0.06);
}
.login-page.light .login-card {
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}

/* 左侧品牌面板 */
.brand-panel {
  position: relative; width: 320px; min-width: 320px;
  padding: 44px 28px;
  display: none; flex-direction: column; justify-content: space-between;
  overflow: hidden; flex-shrink: 0;
  transition: background 0.35s ease;
}
.login-page.dark .brand-panel {
  background: linear-gradient(150deg, #0a0f1e 0%, #0d1a3a 40%, #0f2057 100%);
}
.login-page.light .brand-panel {
  background: linear-gradient(150deg, #1e40af 0%, #2563eb 40%, #3b82f6 100%);
}
@media (min-width: 900px) { .brand-panel { display: flex; } }

.brand-circle { position: absolute; border-radius: 50%; pointer-events: none; }
.brand-circle.c1 { width: 280px; height: 280px; top: -80px; right: -80px; }
.brand-circle.c2 { width: 160px; height: 160px; bottom: 20px; left: -50px; }
.login-page.dark .brand-circle.c1 { background: rgba(59,130,246,0.06); }
.login-page.dark .brand-circle.c2 { background: rgba(59,130,246,0.04); }
.login-page.light .brand-circle.c1 { background: rgba(255,255,255,0.08); }
.login-page.light .brand-circle.c2 { background: rgba(255,255,255,0.06); }

.brand-grid { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; opacity: 0.04; }
.brand-content { position: relative; z-index: 10; }
.brand-logo { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
.logo-icon { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 9px; }
.login-page.dark .logo-icon { background: rgba(59,130,246,0.2); border: 1px solid rgba(59,130,246,0.3); }
.login-page.light .logo-icon { background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); }
.logo-text { font-size: 14px; font-weight: 600; }
.login-page.dark .logo-text { color: #60a5fa; }
.login-page.light .logo-text { color: #fff; }
.brand-headline { font-size: 21px; font-weight: 700; line-height: 1.35; margin: 0 0 8px 0; color: #fff; }
.brand-desc { font-size: 12px; line-height: 1.7; margin: 0; }
.login-page.dark .brand-desc { color: #737373; }
.login-page.light .brand-desc { color: rgba(255,255,255,0.8); }
.brand-features { position: relative; z-index: 10; display: flex; flex-direction: column; gap: 9px; margin-top: 24px; }
.feature-item { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.login-page.dark .feature-item { color: #737373; }
.login-page.light .feature-item { color: rgba(255,255,255,0.85); }
.feature-icon { width: 26px; height: 26px; border-radius: 7px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.login-page.dark .feature-icon { background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); color: #60a5fa; }
.login-page.light .feature-icon { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: #fff; }
.brand-footer { position: relative; z-index: 10; }
.brand-divider { height: 1px; margin-bottom: 12px; }
.login-page.dark .brand-divider { background: rgba(59,130,246,0.1); }
.login-page.light .brand-divider { background: rgba(255,255,255,0.15); }
.brand-footer p { font-size: 10px; margin: 0; }
.login-page.dark .brand-footer p { color: #525252; }
.login-page.light .brand-footer p { color: rgba(255,255,255,0.6); }

/* 右侧表单 */
.form-panel {
  display: flex; flex-direction: column; overflow-y: auto; width: 100%; min-width: 0;
  padding: 44px 28px; flex: 1;
  transition: background 0.35s ease;
}
.login-page.dark .form-panel { background: #1a1a1a; }
.login-page.light .form-panel { background: #fff; }
@media (max-width: 899px) { .form-panel { border-radius: 16px; } }
@media (min-width: 900px) { .form-panel { width: 320px; min-width: 320px; } }

.form-header { margin-bottom: 18px; }
.form-header h3 { font-size: 18px; font-weight: 700; margin: 0 0 3px 0; }
.login-page.dark .form-header h3 { color: #fff; }
.login-page.light .form-header h3 { color: #111; }
.form-subtitle { font-size: 12px; margin: 0; color: #737373; }

/* 锁定提示 */
.lock-notice {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 10px; margin-bottom: 12px;
  font-size: 11px; color: #ef4444; font-weight: 500;
}
.login-page.dark .lock-notice { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); }
.login-page.light .lock-notice { background: #fef2f2; border: 1px solid #fecaca; }
.lock-notice.dark { background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.2); }

/* 登录模式 Tab */
.login-tabs {
  display: flex; gap: 4px; padding: 3px; border-radius: 10px;
  margin-bottom: 14px;
  transition: all 0.25s;
}
.login-page.dark .login-tabs { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.04); }
.login-page.light .login-tabs { background: #f1f5f9; border: 1px solid #e2e8f0; }
.login-tabs.dark { background: rgba(255,255,255,0.04); }
.login-tab {
  flex: 1; height: 32px; border: none; outline: none; cursor: pointer;
  border-radius: 8px; font-size: 12px; font-weight: 500;
  background: transparent; transition: all 0.2s;
}
.login-page.dark .login-tab { color: #525252; }
.login-page.light .login-tab { color: #94a3b8; }
.login-tab.active { background: rgba(59,130,246,0.15); color: #3b82f6; }
.login-page.light .login-tab.active { background: #fff; color: #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.login-tab.dark.active { background: rgba(59,130,246,0.15); color: #3b82f6; }

/* 输入框 */
:deep(.el-input__wrapper) {
  border-radius: 10px !important;
  transition: all 0.15s; caret-color: #3b82f6;
}
.login-page.dark :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08) inset !important;
  background-color: #0a0a0a !important;
}
.login-page.dark :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px rgba(59,130,246,0.3) inset !important; }
.login-page.dark :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1.5px #3b82f6 inset !important; }
.login-page.dark :deep(.el-input__inner) { color: #fff !important; font-size: 13px; }
.login-page.dark :deep(.el-input__inner::placeholder) { color: #404040 !important; }
.login-page.dark :deep(.el-input__prefix .el-icon) { color: #525252; font-size: 14px; }

.login-page.light :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #dde1ea inset !important;
  background-color: #f8fafc !important;
}
.login-page.light :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #3b82f6 inset !important; }
.login-page.light :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1.5px #3b82f6 inset !important; }
.login-page.light :deep(.el-input__inner) { color: #1e293b !important; font-size: 13px; }
.login-page.light :deep(.el-input__inner::placeholder) { color: #94a3b8 !important; }
.login-page.light :deep(.el-input__prefix .el-icon) { color: #94a3b8; font-size: 14px; }

:deep(.el-input-group__append) { padding: 0; background: transparent !important; box-shadow: none !important; border: none !important; }
:deep(.el-form-item__label) { font-size: 11px; padding-bottom: 4px !important; font-weight: 500; }
.login-page.dark :deep(.el-form-item__label) { color: #737373; }
.login-page.light :deep(.el-form-item__label) { color: #6b7280; }
:deep(.el-form-item) { margin-bottom: 10px; }
:deep(.el-form-item.is-error) { margin-bottom: 10px !important; }
:deep(.el-form-item__error) { display: none !important; }

.field-error {
  position: relative; top: -3px; padding-top: 2px;
  line-height: 1.2; font-size: 11px; color: #ef4444;
}
.err-fade-enter-active { transition: opacity 0.15s ease-out, transform 0.15s ease-out; }
.err-fade-leave-active { transition: opacity 0.18s ease-out, transform 0.18s ease-out; }
.err-fade-enter-from { opacity: 0; transform: translateY(-3px); }
.err-fade-leave-to  { opacity: 0; transform: translateY(-3px); }
:deep(.el-checkbox) { display: flex; align-items: flex-start; }
:deep(.el-checkbox__label) { white-space: nowrap; }
:deep(.el-form-item[prop="agree"] .el-checkbox__label) { white-space: normal; word-break: break-all; }
:deep(.el-form-item__content) { flex-wrap: wrap; }
:deep(.el-form-item__content > .el-checkbox) { flex: 0 0 auto; }
:deep(.el-form-item__content > .el-form-item__error) { flex: 0 0 100%; }
:deep(.el-checkbox__label) { font-size: 11px; }
.login-page.dark :deep(.el-checkbox__label) { color: #525252; }
.login-page.light :deep(.el-checkbox__label) { color: #94a3b8; }
.login-page.dark :deep(.el-checkbox__inner) { background: #0a0a0a; border-color: rgba(255,255,255,0.1); }
.login-page.dark :deep(.el-checkbox__input.is-checked .el-checkbox__inner) { background: #3b82f6; border-color: #3b82f6; }
.login-page.dark :deep(.el-checkbox__input.is-checked .el-checkbox__inner::after) { border-color: #fff !important; }
.login-page.light :deep(.el-checkbox__inner) { background: #fff; border-color: #d1d5db; }
.login-page.light :deep(.el-checkbox__inner:hover) { border-color: #3b82f6; }
.login-page.light :deep(.el-checkbox__input.is-checked .el-checkbox__inner) { background: #3b82f6; border-color: #3b82f6; }
.login-page.light :deep(.el-checkbox__input.is-checked .el-checkbox__inner::after) { border-color: #fff !important; transform: translate(-45%,-60%) rotate(45deg) scaleY(1) !important; }
.login-page.light :deep(.el-checkbox__input.is-checked + .el-checkbox__label) { color: #3b82f6; }
.login-page.light :deep(.el-checkbox__input.is-focus .el-checkbox__inner) { border-color: #3b82f6; }

/* 验证码按钮 */
.code-send-btn {
  height: 26px; padding: 0 9px; font-size: 11px; font-weight: 600;
  border-radius: 7px; border: none; outline: none;
  cursor: pointer; white-space: nowrap;
  transition: all 0.2s;
}
.login-page.dark .code-send-btn { background: rgba(59,130,246,0.1); color: #3b82f6; }
.login-page.dark .code-send-btn:disabled { background: rgba(255,255,255,0.03); color: #404040; cursor: not-allowed; }
.login-page.light .code-send-btn { background: #eff6ff; color: #2563eb; }
.login-page.light .code-send-btn:disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
.code-send-btn.dark { background: rgba(59,130,246,0.1); color: #3b82f6; }
.code-send-btn.dark:disabled { background: rgba(255,255,255,0.03); color: #404040; }

.el-input__suffix .code-send-btn-inline,
.code-send-btn-inline {
  height: 24px; padding: 0 8px; font-size: 10px; font-weight: 700;
  border-radius: 6px; border: none; outline: none;
  cursor: pointer; white-space: nowrap;
  background: transparent; color: #3b82f6 !important;
  margin-right: -4px;
}
.el-input__suffix .code-send-btn-inline:disabled,
.code-send-btn-inline:disabled { background: transparent; color: #404040 !important; cursor: not-allowed; }
.el-input__suffix .code-send-btn-inline.dark,
.code-send-btn-inline.dark { background: transparent; color: #3b82f6 !important; }
.el-input__suffix .code-send-btn-inline.dark:disabled,
.code-send-btn-inline.dark:disabled { background: transparent; color: #404040 !important; }

/* 6位验证码输入 */
.code-inputs { display: flex; gap: 6px; justify-content: center; }
.code-input {
  width: 38px; height: 42px; text-align: center; font-size: 16px; font-weight: 600;
  border-radius: 10px; outline: none;
  caret-color: #3b82f6;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.25s;
}
.login-page.dark .code-input {
  border: 1.5px solid rgba(255,255,255,0.08); background: #0a0a0a; color: #fff;
}
.login-page.dark .code-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
.login-page.light .code-input {
  border: 1.5px solid #dde1ea; background: #f8fafc; color: #1e293b;
}
.login-page.light .code-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
.code-input.dark { background: #0a0a0a; border-color: rgba(255,255,255,0.08); color: #fff; }
.code-input.dark:focus { border-color: #3b82f6; }
.code-hint { font-size: 11px; margin: 0 0 6px 0; }
.login-page.dark .code-hint { color: #525252; }
.login-page.light .code-hint { color: #94a3b8; }

/* 步骤指示器 */
.step-bar { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 18px; }
.step-dot {
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; transition: all 0.25s;
}
.login-page.dark .step-dot { color: #525252; border: 1.5px solid rgba(255,255,255,0.08); background: #0a0a0a; }
.login-page.light .step-dot { color: #94a3b8; border: 1.5px solid #e2e8f0; background: #fff; }
.step-dot.active { border-color: #3b82f6; color: #3b82f6; }
.step-dot.done { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.step-line { width: 60px; height: 2px; transition: background 0.25s; }
.login-page.dark .step-line { background: rgba(255,255,255,0.06); }
.login-page.light .step-line { background: #e2e8f0; }
.step-line.active { background: #3b82f6; }

.form-actions { display: flex; align-items: center; justify-content: space-between; flex-wrap: nowrap; gap: 8px; width: 100%; }
.el-form-item[prop="agree"] .form-actions:last-child { flex-wrap: nowrap; }
.step-back-row { margin-bottom: 12px; }

/* 链接按钮 */
.link-btn { font-size: 11px; color: #3b82f6; font-weight: 600; background: none; border: none; cursor: pointer; padding: 0; }
.link-btn:hover { text-decoration: underline; }

/* 提交按钮 */
.submit-btn {
  width: 100%; height: 42px !important; border-radius: 10px !important;
  font-size: 13px !important; font-weight: 600 !important;
  border: none !important;
  letter-spacing: 1px; transition: all 0.2s;
}
.login-page.dark .submit-btn {
  background: #fff !important; color: #000 !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
}
.login-page.dark .submit-btn:hover { background: #e5e5e5 !important; }
.login-page.dark .submit-btn.is-disabled { background: #262626 !important; color: #525252 !important; box-shadow: none !important; }

.login-page.light .submit-btn {
  background: #3b82f6 !important; color: #fff !important;
  box-shadow: 0 2px 8px rgba(59,130,246,0.3) !important;
}
.login-page.light .submit-btn:hover { background: #2563eb !important; }
.login-page.light .submit-btn.is-disabled { background: #94a3b8 !important; color: #fff !important; box-shadow: none !important; }

/* 分割线 */
.divider-row { display: flex; align-items: center; gap: 8px; margin: 12px 0; }
.divider-line { flex: 1; height: 1px; transition: background 0.25s; }
.login-page.dark .divider-line { background: rgba(255,255,255,0.06); }
.login-page.light .divider-line { background: #e2e8f0; }
.divider-text { font-size: 10px; }
.login-page.dark .divider-text { color: #404040; }
.login-page.light .divider-text { color: #94a3b8; }
.switch-text { text-align: center; font-size: 11px; margin: 0; }
.login-page.dark .switch-text { color: #525252; }
.login-page.light .switch-text { color: #94a3b8; }

/* 用户协议弹窗 */
.agreement-content h4 { font-size: 13px; font-weight: 600; margin: 16px 0 6px 0; }
.agreement-content h4:first-child { margin-top: 0; }
.agreement-content p { font-size: 12px; line-height: 1.8; margin: 0; }
.login-page.dark .agreement-content h4 { color: #fff; }
.login-page.dark .agreement-content p { color: #737373; }
.login-page.light .agreement-content h4 { color: #1e293b; }
.login-page.light .agreement-content p { color: #64748b; }
</style>
