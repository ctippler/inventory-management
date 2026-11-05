<template>
  <svg
    class="nav-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="d in paths" :key="d" :d="d" />
  </svg>
</template>

<script>
import { computed } from 'vue'

// Minimal stroke icon set (24x24 grid) so the app needs no icon dependency.
const ICONS = {
  overview: ['M3 3h7v9H3z', 'M14 3h7v5h-7z', 'M14 12h7v9h-7z', 'M3 16h7v5H3z'],
  inventory: ['M21 8l-9-5-9 5 9 5 9-5z', 'M3 8v8l9 5 9-5V8', 'M12 13v8'],
  orders: ['M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z', 'M8 6H6a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-2', 'M9 12h6', 'M9 16h4'],
  finance: ['M3 7h18v12H3z', 'M3 11h18', 'M7 15h3'],
  demand: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'],
  restocking: ['M3 12a9 9 0 0 1 15.5-6.2L21 8', 'M21 3v5h-5', 'M21 12a9 9 0 0 1-15.5 6.2L3 16', 'M3 21v-5h5'],
  reports: ['M4 20V10', 'M10 20V4', 'M16 20v-7', 'M22 20H2'],
  chevronLeft: ['M15 6l-6 6 6 6'],
  chevronRight: ['M9 6l6 6-6 6']
}

export default {
  name: 'NavIcon',
  props: {
    name: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const paths = computed(() => ICONS[props.name] || [])
    return { paths }
  }
}
</script>

<style scoped>
.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}
</style>
