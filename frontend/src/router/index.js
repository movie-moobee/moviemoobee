import { createRouter, createWebHistory } from "vue-router";

// 화면 라우팅 (와이어프레임 01~13 기준). 페이지는 lazy import.
const routes = [
  { path: "/login", component: () => import("../views/LoginView.vue") },
  { path: "/onboarding", component: () => import("../views/OnboardingView.vue") },
  { path: "/", component: () => import("../views/MainView.vue") },
  { path: "/search", component: () => import("../views/SearchView.vue") },
  { path: "/movies/:id", component: () => import("../views/MovieDetailView.vue") },
  { path: "/profile", component: () => import("../views/ProfileView.vue") },
  { path: "/map", component: () => import("../views/MapView.vue") },          // 개발자 A
  { path: "/recommend", component: () => import("../views/RecommendView.vue") }, // 개발자 A
  { path: "/friends", component: () => import("../views/FriendsView.vue") },
  { path: "/friends/:id", component: () => import("../views/FriendDetailView.vue") },
];

export default createRouter({ history: createWebHistory(), routes });
