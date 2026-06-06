<script setup>
// 공통 셸 (네비 + 라우터 뷰). 상세 네비는 추후(F-UI).
</script>

<template>
  <div id="shell">
    <nav><!-- TODO: 홈·검색·지도·추천·친구 --></nav>
    <main><router-view /></main>
  </div>
</template>
