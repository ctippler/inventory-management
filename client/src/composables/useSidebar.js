import { ref, computed } from 'vue'

const STORAGE_KEY = 'sidebar-collapsed'
const NARROW_QUERY = '(max-width: 1023px)'

const readStored = () => {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === null ? null : value === 'true'
  } catch {
    return null
  }
}

const narrowMedia = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia(NARROW_QUERY)
  : null

// A manual toggle wins over the screen-width default and is remembered.
// Without one, the sidebar follows the viewport: collapsed below 1024px.
const userChoice = ref(readStored())
const isNarrow = ref(narrowMedia ? narrowMedia.matches : false)

if (narrowMedia) {
  narrowMedia.addEventListener('change', (e) => {
    isNarrow.value = e.matches
  })
}

const collapsed = computed(() => userChoice.value ?? isNarrow.value)

export function useSidebar() {
  const toggleSidebar = () => {
    userChoice.value = !collapsed.value
    try {
      localStorage.setItem(STORAGE_KEY, String(userChoice.value))
    } catch {
      // Storage unavailable (private mode etc.): keep the in-memory choice.
    }
  }

  return {
    collapsed,
    toggleSidebar
  }
}
