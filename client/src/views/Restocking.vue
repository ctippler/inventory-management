<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <label class="budget-label" for="budget-slider">
          <span>{{ t('restocking.budget') }}</span>
          <strong class="budget-value">{{ formatMoney(budget) }}</strong>
        </label>
        <input
          id="budget-slider"
          v-model.number="budget"
          class="budget-slider"
          type="range"
          min="0"
          :max="budgetMax"
          :step="BUDGET_STEP"
          :aria-valuetext="formatMoney(budget)"
        />
        <div class="budget-range">
          <span>{{ formatMoney(0) }}</span>
          <span>{{ formatMoney(budgetMax) }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ formatMoney(budget) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.allocated') }}</div>
          <div class="stat-value">{{ formatMoney(allocated, 2) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatMoney(budget - allocated, 2) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.itemsSelected') }}</div>
          <div class="stat-value">{{ recommendations.length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ recommendations.length }})</h3>
          <button
            class="place-order-btn"
            type="button"
            :disabled="recommendations.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="submitResult" class="notice success" role="status">
          {{ t('restocking.success', { number: submitResult.order_number, days: submitResult.lead_time_days }) }}
          <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
        </div>
        <div v-if="submitError" class="notice danger" role="alert">{{ submitError }}</div>

        <div v-if="candidates.length === 0" class="empty-state">{{ t('restocking.noCandidates') }}</div>
        <div v-else-if="recommendations.length === 0" class="empty-state">{{ t('restocking.empty') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in recommendations" :key="line.item_sku">
                <td><strong>{{ line.item_sku }}</strong></td>
                <td>{{ translateProductName(line.item_name) }}</td>
                <td>
                  <span :class="['badge', line.trend]">{{ t(`trends.${line.trend}`) }}</span>
                </td>
                <td class="num">
                  {{ line.quantity.toLocaleString() }}
                  <span v-if="line.partial" class="partial-tag">{{ t('restocking.partial') }}</span>
                </td>
                <td class="num">{{ formatMoney(line.unit_cost, 2) }}</td>
                <td class="num"><strong>{{ formatMoney(line.line_total, 2) }}</strong></td>
                <td class="num">{{ t('orders.submittedOrders.days', { count: line.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const BUDGET_STEP = 50

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const submitResult = ref(null)
    const submitError = ref(null)

    // Only items whose demand is forecast to grow need restocking; the quantity
    // to order is the gap between forecasted and current demand. Rising-trend
    // items come first, then the largest relative growth.
    const candidates = computed(() => {
      return forecasts.value
        .filter(f => f.forecasted_demand > f.current_demand && f.unit_cost > 0)
        .map(f => ({
          ...f,
          gap: f.forecasted_demand - f.current_demand,
          growth: (f.forecasted_demand - f.current_demand) / f.current_demand
        }))
        .sort((a, b) => {
          const aUp = a.trend === 'increasing' ? 0 : 1
          const bUp = b.trend === 'increasing' ? 0 : 1
          return aUp - bUp || b.growth - a.growth
        })
    })

    const budgetMax = computed(() => {
      const total = candidates.value.reduce((sum, c) => sum + c.gap * c.unit_cost, 0)
      return Math.max(BUDGET_STEP, Math.ceil(total / 500) * 500)
    })

    // Greedy fill in priority order. Math is done in cents to avoid float drift
    // pushing the total a fraction over budget. The first item that doesn't fit
    // completely gets a partial quantity and the fill stops there, so priority
    // order is respected (no cheaper low-priority item jumps the queue).
    const recommendations = computed(() => {
      let remainingCents = Math.round(budget.value * 100)
      const lines = []
      for (const c of candidates.value) {
        const unitCents = Math.round(c.unit_cost * 100)
        const affordable = Math.floor(remainingCents / unitCents)
        const quantity = Math.min(c.gap, affordable)
        if (quantity > 0) {
          lines.push({
            item_sku: c.item_sku,
            item_name: c.item_name,
            trend: c.trend,
            unit_cost: c.unit_cost,
            lead_time_days: c.lead_time_days,
            quantity,
            line_total: (quantity * unitCents) / 100,
            partial: quantity < c.gap
          })
          remainingCents -= quantity * unitCents
        }
        if (quantity < c.gap) break
      }
      return lines
    })

    const allocated = computed(() => {
      return recommendations.value.reduce((sum, l) => sum + l.line_total, 0)
    })

    const formatMoney = (amount, decimals = 0) => {
      return formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)
    }

    const loadForecasts = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        budget.value = Math.round(budgetMax.value / 2 / BUDGET_STEP) * BUDGET_STEP
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (recommendations.value.length === 0 || submitting.value) return
      try {
        submitting.value = true
        submitError.value = null
        submitResult.value = null
        submitResult.value = await api.createRestockingOrder({
          budget: budget.value,
          items: recommendations.value.map(l => ({ sku: l.item_sku, quantity: l.quantity }))
        })
      } catch (err) {
        const detail = err.response?.data?.detail
        submitError.value = `${t('restocking.submitError')}${typeof detail === 'string' ? ': ' + detail : ''}`
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      translateProductName,
      BUDGET_STEP,
      loading,
      error,
      budget,
      budgetMax,
      candidates,
      recommendations,
      allocated,
      submitting,
      submitResult,
      submitError,
      formatMoney,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
}

.budget-label {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.75rem;
}

.budget-value {
  font-size: 1.5rem;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #3b82f6;
  cursor: pointer;
}

.budget-range {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.place-order-btn {
  background: #0f172a;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.notice {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
}

.notice.success {
  background: #dcfce7;
  color: #166534;
}

.notice.success a {
  margin-left: 0.5rem;
  color: #166534;
  font-weight: 600;
}

.notice.danger {
  background: #fee2e2;
  color: #991b1b;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.num {
  text-align: right;
}

.partial-tag {
  margin-left: 0.375rem;
  font-size: 0.688rem;
  color: #92400e;
  background: #fef3c7;
  padding: 0.063rem 0.375rem;
  border-radius: 4px;
}
</style>
