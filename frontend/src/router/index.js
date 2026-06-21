import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { fetchOnboarded } from '@/api/auth'

const routes = [
  { path: '/login',      name: 'login',      component: () => import('@/views/LoginView.vue'),      meta: { public: true } },
  { path: '/signup',     name: 'signup',     component: () => import('@/views/SignupView.vue'),     meta: { public: true } },
  { path: '/onboarding', name: 'onboarding', component: () => import('@/views/OnboardingView.vue') },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '',            name: 'home',           component: () => import('@/views/MainView.vue') },
      { path: 'map',         name: 'map',            component: () => import('@/views/MapView.vue') },
      { path: 'movies',      name: 'movies',         component: () => import('@/views/MovieSearchView.vue') },
      { path: 'movies/:id',  name: 'movie-detail',   component: () => import('@/views/MovieDetailView.vue') },
      { path: 'records',     name: 'records',        component: () => import('@/views/WatchRecordsView.vue') },
      { path: 'friends',     name: 'friends',        component: () => import('@/views/FriendsView.vue') },
      { path: 'friends/:id', name: 'friend-compare', component: () => import('@/views/FriendCompareView.vue') },
      { path: 'profile',     name: 'profile',        component: () => import('@/views/ProfileView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const isAuthed = !!localStorage.getItem('token')
  // 비로그인: 공개 라우트만 허용, 나머지는 로그인으로
  if (!isAuthed) {
    return to.meta.public ? true : { name: 'login' }
  }
  // 로그인됨: 온보딩·공개 라우트는 그대로 통과
  if (to.name === 'onboarding' || to.meta.public) return true
  // 온보딩 미완이면 내부 진입 차단 → 온보딩으로 (onboarded는 1회 조회 후 캐시)
  const onboarded = await fetchOnboarded()
  if (!onboarded) return { name: 'onboarding' }
  return true
})

export default router
