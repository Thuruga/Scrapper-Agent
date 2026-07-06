import { create } from 'zustand'
import { toast } from 'sonner'
import { ApiClient, type AppNotification } from '../api/client'

interface NotificationStoreState {
  notifications: AppNotification[]
  unreadCount: number
  panelOpen: boolean
  poll: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
  remove: (id: string) => Promise<void>
  clearAll: () => Promise<void>
  setPanelOpen: (open: boolean) => void
}

// Dedup entre polls: o primeiro fetch popula seenIds sem toast (backlog
// não deve re-toastar ao abrir o app); os seguintes toastam só ids novos.
let initialized = false
const seenIds = new Set<string>()

function toastFor(notification: AppNotification) {
  const { type, title, message, metadata } = notification
  if (type === 'price_change' || type === 'category_price_change') {
    toast.warning(title, { description: message })
    return
  }
  if (type === 'scan_finished') {
    const status = metadata?.status
    if (status === 'error') toast.error(title, { description: message })
    else if (status === 'cancelled') toast.info(title, { description: message })
    else toast.success(title, { description: message })
    return
  }
  toast.info(title, { description: message })
}

export const useNotificationStore = create<NotificationStoreState>()((set, get) => ({
  notifications: [],
  unreadCount: 0,
  panelOpen: false,

  poll: async () => {
    try {
      const { notifications, unread_count } = await ApiClient.getNotifications(false, 50)
      if (initialized) {
        for (const item of notifications) {
          if (!seenIds.has(item.id)) toastFor(item)
        }
      }
      for (const item of notifications) seenIds.add(item.id)
      initialized = true
      set({ notifications, unreadCount: unread_count })
    } catch {
      // Polling de fundo — falhas são silenciosas para não poluir a UI.
    }
  },

  markRead: async (id) => {
    set(state => {
      const target = state.notifications.find(n => n.id === id)
      if (!target || target.read) return state
      return {
        notifications: state.notifications.map(n => (n.id === id ? { ...n, read: true } : n)),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }
    })
    try {
      await ApiClient.markNotificationRead(id)
    } catch {
      void get().poll()
    }
  },

  markAllRead: async () => {
    set(state => ({
      notifications: state.notifications.map(n => ({ ...n, read: true })),
      unreadCount: 0,
    }))
    try {
      await ApiClient.markAllNotificationsRead()
    } catch {
      void get().poll()
    }
  },

  remove: async (id) => {
    set(state => {
      const target = state.notifications.find(n => n.id === id)
      return {
        notifications: state.notifications.filter(n => n.id !== id),
        unreadCount: target && !target.read
          ? Math.max(0, state.unreadCount - 1)
          : state.unreadCount,
      }
    })
    try {
      await ApiClient.deleteNotification(id)
    } catch {
      void get().poll()
    }
  },

  clearAll: async () => {
    set({ notifications: [], unreadCount: 0 })
    try {
      await ApiClient.clearNotifications()
    } catch {
      void get().poll()
    }
  },

  setPanelOpen: (open) => set({ panelOpen: open }),
}))
