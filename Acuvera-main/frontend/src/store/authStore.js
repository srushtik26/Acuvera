import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { AuthAPI } from '../api/client'

// If a token was already persisted in localStorage, start with isLoading=true
// so RequireAuth shows a spinner instead of instantly redirecting to /login
// before fetchUser() has a chance to run on app mount.
const hasPersistedToken = !!localStorage.getItem('acuvera_token')

export const useAuthStore = create(
    persist(
        (set, get) => ({
            user: null,
            token: null,
            isLoading: hasPersistedToken,

            setToken: (token) => {
                localStorage.setItem('acuvera_token', token)
                set({ token })
            },

            fetchUser: async () => {
                set({ isLoading: true })
                try {
                    const user = await AuthAPI.whoami()
                    console.log("[useAuthStore] Whoami fetched successfully:", user)
                    set({ user, isLoading: false })
                } catch (error) {
                    console.error("[useAuthStore] Whoami fetch failed:", error)
                    // Clear invalid/expired token so user is sent to login cleanly
                    localStorage.removeItem('acuvera_token')
                    set({ user: null, token: null, isLoading: false })
                }
            },

            logout: () => {
                localStorage.removeItem('acuvera_token')
                localStorage.removeItem('acuvera_bypass_user_id')
                set({ user: null, token: null })
                window.location.href = '/login'
            },
        }),
        { name: 'acuvera-auth', partialize: (s) => ({ token: s.token }) }
    )
)
