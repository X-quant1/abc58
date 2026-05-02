<template>
  <div class="settings-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover" class="panel-card">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">风控参数</span>
            </div>
          </template>
          <el-form :model="riskForm" label-width="110px" class="settings-form">
            <el-form-item label="单笔风险比例">
              <el-slider v-model="riskForm.riskPerTrade" :min="0.5" :max="5" :step="0.5" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item label="硬止损比例">
              <el-slider v-model="riskForm.stopLoss" :min="1" :max="10" :step="0.5" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item label="最大杠杆">
              <el-input-number v-model="riskForm.maxLeverage" :min="1" :max="5" />
              <span class="unit-label">倍</span>
            </el-form-item>
            <el-form-item label="最大回撤熔断">
              <el-slider v-model="riskForm.maxDrawdown" :min="5" :max="30" :step="1" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item label="日最大亏损">
              <el-slider v-model="riskForm.maxDailyLoss" :min="1" :max="10" :step="0.5" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveRiskConfig">保存风控</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

const riskForm = reactive({
  riskPerTrade: 1,
  stopLoss: 5,
  maxLeverage: 3,
  maxDrawdown: 10,
  maxDailyLoss: 5,
})

const saveRiskConfig = () => ElMessage.success('风控参数已保存')
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

.settings-form {
  padding: 8px 4px 0;
}

.unit-label {
  margin-left: 6px;
  font-size: 13px;
  color: #86909c;
}

@media (max-width: 768px) {
  .el-row .el-col {
    max-width: 100% !important;
    flex: 0 0 100% !important;
  }
}
</style>
