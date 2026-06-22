# 무비무비 — 프로젝트 파일 구조

이 문서는 레포의 **폴더·파일이 각각 무슨 역할인지** 한눈에 보기 위한 지도다. (상세 동작은 기능명세서 01, 데이터는 ERD 02, 작업 기록은 `08_journal/` 참고)

> 담당: **A = 개발자 A(지도·추천·데이터)**, **B = 개발자 B(인증·콘텐츠·소셜)**, **공통 = 함께/협업**
> 상태: ✅ 구현됨 · 🟡 스텁(TODO) · ⚙️ 설정/인프라

---

## 최상위
```
13-pjt/
├─ README.md                  처음 시작·폴더개요·담당
├─ CLAUDE.md                  바이브코딩 가이드+도메인 불변식 (gitignore=개인용)
├─ docker-compose.yml         ⚙️ 로컬 PostgreSQL(+adminer) 컨테이너
├─ .env / .env.example        ⚙️ 환경변수(.env는 커밋 금지)
├─ .gitignore
├─ disabled-gitlab-ci.yml     ⚙️ CI 파이프라인(러너 없어 비활성화됨)
├─ .gitlab/merge_request_templates/Default.md   MR 기본 템플릿
├─ backend/                   Django REST Framework
├─ frontend/                  Vue 3 + Vite
└─ docs/                      기획·설계·일지 문서
```

## backend/ (Django REST Framework)
```
backend/
├─ manage.py                  Django 진입점
├─ requirements.txt           웹앱 의존성(Django/DRF/psycopg/dotenv …)
├─ requirements-ml.txt        데이터·추천(A) 의존성(numpy/sklearn/umap …) — 무거워 분리
├─ .ruff.toml                 ⚙️ 린트 설정(line-length=100)
│
├─ config/                    프로젝트 공통(셸)            [공통]
│  ├─ settings.py             설정(.env 로드, DB, DRF, CORS)
│  ├─ urls.py                 루트 라우팅(/admin, /api/*, /api/health)
│  ├─ views.py                ✅ /api/health (임시 연결확인용)
│  └─ asgi.py · wsgi.py
│
├─ accounts/                  User·인증·프로필             [B]
│  ├─ models.py               ✅ User(AbstractUser + nickname, coord_x/y/coord_updated_at)
│  ├─ views.py · serializers.py · urls.py   🟡 인증/프로필(F-AUTH)
│  └─ admin.py
│
├─ movies/                    영화·장르·키워드·시청기록     [B]
│  ├─ models.py               ✅ Genre/Keyword/Movie(umap_x/y)/WatchRecord
│  ├─ fixtures/movies.json    ✅ 영화+좌표 시드(loaddata movies) [A가 생성]
│  ├─ views.py · serializers.py · urls.py   🟡 검색/상세/시청등록(F-MOV,F-WAT)
│  └─ admin.py
│
├─ social/                    친구·알림                    [B]
│  ├─ models.py               ✅ Friendship, Notification(F-NTF)
│  └─ views.py · serializers.py · urls.py   🟡 친구/알림(F-FRD,F-NTF)
│
└─ taste/                     좌표·영역·추천·지도 데이터     [A]
   ├─ models.py               (모델 없음 — movies/accounts 읽어 좌표 갱신)
   ├─ apps.py                 ✅ ready()에서 시그널 등록
   ├─ signals.py              ✅ WatchRecord 변경 → 사용자 좌표 재계산(F-MAP-00)
   ├─ views.py · urls.py      ✅ GET /api/taste/me/coord (내 좌표)
   ├─ serializers.py          🟡 추천/지도 응답
   ├─ services/               (뷰에 안 두는) 무거운 도메인 로직
   │  ├─ coords.py            ✅ recompute_user_coord (별점 가중 무게중심·캐싱)
   │  ├─ areas.py             ✅ 미탐색·안전 영역(KDE/좌표거리) F-MAP-03
   │  └─ recommend.py         🟡 안전/미탐색 추천 F-REC
   ├─ management/commands/    데이터 파이프라인(manage.py 커맨드)
   │  ├─ import_movies.py     ✅ TMDB 인기영화 수집·적재
   │  ├─ build_coords.py      ✅ TF-IDF+UMAP 전역 좌표 생성·적재(+모델 pkl)
   │  └─ seed_demo.py         ✅ 데모 유저·시청기록·친구 시드
   └─ artifacts/coords_model.pkl   ⚙️ 학습된 좌표 모델(gitignore; 신규영화 transform용)
```
**규칙**: 모델=ERD, 무거운 연산(임베딩/UMAP/KDE/좌표거리)은 **뷰가 아니라 services·management 커맨드**에.

## frontend/ (Vue 3 + Vite · Composition API)
```
frontend/
├─ package.json · vite.config.js(/api 프록시) · .eslintrc.cjs · index.html
└─ src/
   ├─ main.js · App.vue        공통 셸
   ├─ router/index.js          화면 라우팅(01~13)
   ├─ api/client.js            axios(baseURL=/api)
   ├─ composables/useTasteMap.js   🟡 취향 지도 로직 [A]
   ├─ views/                   화면별 페이지
   │  ├─ MapView · RecommendView         🟡 [A]
   │  └─ Login/Onboarding/Main/Search/MovieDetail/Profile/Friends/FriendDetail  🟡 [B]
   ├─ components/  ·  assets/   (.gitkeep)
```
**규칙**: `<script setup>`만(Options API 금지). 지도는 SVG/Canvas(D3 등), 주변 UI는 일반 컴포넌트.

## docs/ (기획·설계·일지)
```
docs/
├─ README.md                  문서 목록(인덱스)
├─ 01_functional_spec.docx    기능명세서(F-ID, 입력/처리/출력/예외)
├─ 02_erd.dbml/.png/.svg      ERD(테이블=모델)
├─ 03_wireframe.html          와이어프레임(화면 01~13)
├─ 04_schedule.xlsx/.gantt    일정/WBS  ·  notion/  노션 임포트용
├─ 05_collaboration_rules.docx · 06_github_flow.png   협업 규칙·플로우
├─ 07_docker_postgres_guide.md   Docker+Postgres 세팅
├─ 08_journal/               ✅ 개발 일지(작업별 A-NN-*.md) [A 작성중]
├─ 09_tech_notes.docx        기술 노트(인증/시그널/라이브러리 단일출처)
├─ 10_project_structure.md   이 문서
└─ poc-bundle/poc-a, poc-b   검증용 PoC(좌표/추천 원형)
```

---

## 한눈 흐름 (데이터 → 좌표 → 추천)
```
import_movies(TMDB) → movies 적재
   → build_coords(TF-IDF+UMAP) → movies.umap_x/y (전역 고정 좌표)
   → (시청기록 별점) → signals → coords.recompute_user_coord → users.coord_x/y
   → recommend/areas(안전=좌표거리, 미탐색=KDE) → 추천/지도
```
페어 빠른 시작: `loaddata movies`(영화+좌표) + `seed_demo`(데모) → 파이프라인 재실행 불필요.
