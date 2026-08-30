# 무비무비 — Frontend (Vue 3 SPA)

무비무비의 웹 클라이언트입니다. **Vue 3 (Composition API, `<script setup>`) + Vite** 기반 SPA이며, 백엔드(DRF)와는 `/api`로 통신합니다. 취향 지도는 컴포넌트 라이브러리 없이 **SVG로 직접** 그립니다.

전체 서비스 개요·회고는 루트 [`../README.md`](../README.md), 백엔드는 [`../backend/README.md`](../backend/README.md)를 참고하세요.

## 1. 기술 스택

- **Vue 3** — Composition API만 사용(Options API 금지), 컴포넌트는 `<script setup>`.
- **Vite** — 개발 서버 + 번들러. `/api`는 개발 시 `:8000`(Django)로 프록시.
- **Vue Router** — SPA 라우팅(history mode).
- **Axios** — API 클라이언트(토큰 인터셉터). 단, **SSE 스트리밍은 `fetch`** 사용.
- 스타일은 **Tailwind CSS** + 자체 CSS 토큰(`tokens.css`)의 Carbon 다크 테마 — Bootstrap 미사용.

## 2. 디렉터리 구조 (`src/`)

| 경로 | 내용 |
|---|---|
| `main.js` · `App.vue` | 앱 진입점 |
| `router/index.js` | 라우트 정의·인증 가드 |
| `layouts/` | `AppLayout.vue` (네비/푸터 셸) |
| `views/` | 페이지 — 로그인/회원가입·온보딩·메인·지도(`MapView`)·영화 검색/상세·추천·친구/비교·프로필 등 |
| `components/` | 재사용 컴포넌트 |
| `composables/` | `useCurrentUser`·`useMovieSearch`·`useTasteMap` 등 상태 로직(`use*`) |
| `api/` | 백엔드 호출 모듈 |
| `assets/styles/` | `tokens.css`·`tailwind.css` 디자인 토큰 |

### 핵심 컴포넌트
- **`TasteMapCanvas.vue`** — 취향 지도 렌더러(SVG). 별(평점=크기·밝기·색), 장르 대륙, 추천 핀, 확대/팬·미니맵, 겹침 황금각 분산, 안전 추천 공전 애니메이션, 친구 비교 owner 색/강조 토글까지 담당. 홈 프리뷰·지도 페이지·친구 비교에서 공유.
- **`ChatPanel.vue`** — 재사용 LLM 챗 패널. 부모가 `streamFn`(SSE)을 주입(추천 챗봇/같이 볼 영화 공용). 일일 사용량 카운터(quota) 표시 지원.
- `WatchRecordModal` · `RatingModal` · `NotificationBell` · `ConfirmDialog` · `base/`(공통 입력·별점 등).

## 3. API 계층 (`src/api/`)

| 파일 | 내용 |
|---|---|
| `client.js` | axios 인스턴스(`baseURL: VITE_API_URL \|\| "/api"`) + 토큰 자동 첨부 + 401 자동 로그아웃. SSE(fetch)도 같은 `API_BASE` 사용 |
| `auth.js` · `movies.js` · `watchRecords.js` · `social.js` · `taste.js` | 도메인별 REST 호출 |
| `chat.js` | **SSE 스트리밍**(`fetch` + `ReadableStream`). 멀티바이트(한글) 청크 경계 처리, 응답 헤더로 챗봇 사용량 반환 |

> 토큰은 `localStorage`에 저장하고 모든 요청에 `Authorization: Token <key>`로 첨부합니다.

## 4. 로컬 실행

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

- 백엔드(`http://localhost:8000`)가 함께 떠 있어야 합니다.
- `vite.config.js`의 프록시가 `/api` 요청을 백엔드로 전달합니다.

## 5. 빌드

```bash
npm run build    # 정적 결과물 → dist/
npm run preview  # 빌드 결과 미리보기
```

`dist/`는 정적 파일이므로 어떤 정적 호스팅(예: nginx, Vercel)에도 올릴 수 있습니다. 같은-도메인 배포가 아니면 `VITE_API_URL` 환경변수로 백엔드 API 주소를 지정합니다(예: `VITE_API_URL=https://my-app.onrender.com/api`, 미설정 시 `/api` 프록시 사용).

## 6. 코드 규칙

- Composition API만 사용(`ref`/`reactive`/`computed`/`use*` 컴포저블). `data()`/`methods` 금지.
- 취향 지도는 SVG/Canvas로 직접 그리고, 그 외 UI(패널·카드·폼)는 일반 컴포넌트로 구성합니다.
