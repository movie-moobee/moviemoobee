<script setup>
// 메인 (취향 지도 프리뷰 + 최근 추가)
import { ref, onMounted } from "vue";
import { api } from "../api/client";

// 임시: 프론트↔백↔DB 연결 확인용(세팅 검증). 기능 구현 아님 — 검증 후 제거 가능.
const health = ref("확인 중…");
onMounted(async () => {
  try {
    const { data } = await api.get("/health");
    health.value = `백엔드 OK · DB ${data.db ? "OK" : "FAIL"}`;
  } catch {
    health.value = "백엔드 연결 실패";
  }
});
</script>

<template>
  <section>
    <h1>MainView</h1>
    <!-- 임시 연결 확인 배지(세팅 검증용) -->
    <p data-testid="health">
      연결 상태: {{ health }}
    </p>
    <!-- TODO: 메인 (취향 지도 프리뷰 + 최근 추가) -->
  </section>
</template>
