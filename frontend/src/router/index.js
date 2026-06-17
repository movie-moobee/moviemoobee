import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

const routes = [
  { path: '/login',      name: 'login',      component: () => import('@/views/LoginView.vue'),      meta: { public: true } },
  { path: '/signup',     name: 'signup',     component: () => import('@/views/SignupView.vue'),     meta: { public: true } },
  { path: '/onboarding', name: 'onboarding', component: () => import('@/views/OnboardingView.vue') },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '',            name: 'map',            component: () => import('@/views/MapView.vue') },
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

router.beforeEach((to) => {
  const isAuthed = !!localStorage.getItem('token')
  if (!to.meta.public && !isAuthed && to.name !== 'login') {
    return { name: 'login' }
  }
})

export default router
