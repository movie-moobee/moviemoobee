# 무비무비 (MovieMoobee)

무비무비는 사용자가 본 영화와 별점을 바탕으로 취향 지도를 만들고, 다음에 볼 만한 영화를 추천하는 영화 추천 커뮤니티 서비스입니다. 단순히 "좋아했던 영화와 비슷한 작품"만 보여주는 대신, 안전 추천과 미탐색 추천을 함께 제공해 익숙한 취향과 새로운 취향을 모두 탐색할 수 있게 합니다.

## 1. 팀원 정보 및 업무 분담

| 역할 | 담당 영역 | 주요 구현 |
|---|---|---|
| 김호준 | 지도·추천·데이터 | TMDB 데이터 수집, 영화 좌표 생성, 취향 지도, 안전/미탐색 추천, AI 추천 챗봇 |
| 제하얀 | 인증·콘텐츠·소셜 | 회원가입/로그인, 온보딩, 영화 검색·상세, 시청기록·리뷰, 친구·알림 |
| 공통 | 공통 구조·문서 | ERD, 라우팅, 공통 API 구조, 협업 규칙, 제출 문서 |

## 2. 목표 서비스 및 실제 구현 정도

목표는 데이터를 기반으로 개인화된 영화 추천과 커뮤니티 기능을 제공하는 Vue SPA + Django REST Framework 서비스입니다.

구현된 주요 범위는 다음과 같습니다.

- 회원가입, 로그인, 로그아웃, 프로필 수정, 계정 삭제
- 온보딩 시 영화 5편 이상 등록
- 영화 검색, 영화 상세, OTT 제공 정보, 예고편 정보
- 시청 기록 등록/수정/삭제, 별점, 감상평
- 리뷰 반응, 댓글
- 친구 검색, 친구 요청/수락/거절/삭제
- 친구 취향 비교 지도, 같이 볼 영화 추천 챗봇
- 알림 목록, 안 읽은 알림, SSE 기반 알림 갱신
- 취향 지도, 지도 탐색, 안전 추천, 미탐색 추천, 오늘의 추천
- GMS 기반 영화 추천 AI 챗봇

배포는 최종 범위에서 제외했고, 로컬 시연을 기준으로 구성했습니다.

## 3. 기술 스택 및 라이브러리

| 영역 | 사용 기술 |
|---|---|
| Frontend | Vue 3, Vue Router, Vite, Axios, CSS |
| Backend | Python 3.11, Django 5.2, Django REST Framework |
| DB | PostgreSQL, Docker Compose |
| Auth | dj-rest-auth, django-allauth, DRF Token Authentication |
| Data/API | TMDB API, requests, python-dotenv |
| Recommendation/ML | numpy, scipy, scikit-learn, pandas |
| AI | SSAFY GMS API, SSE streaming |

명세서의 Bootstrap 5.3 항목은 검토했으나, 최종 UI는 Bootstrap 컴포넌트 대신 Vue 컴포넌트와 자체 CSS 토큰으로 구현했습니다.

## 4. 데이터베이스 모델링 (ERD)

ERD 산출물은 `docs/02_erd.png`, `docs/02_erd.svg`, `docs/02_erd.dbml`에 정리했습니다.

핵심 모델은 다음과 같습니다.

- `accounts.User`: 사용자, 닉네임, 프로필 이미지, 온보딩 완료 여부
- `movies.Movie`: 영화 기본 정보, TMDB ID, 장르/키워드, 출연진, 예고편, 취향 지도 좌표
- `movies.Genre`, `movies.Keyword`: 영화 분류 정보
- `movies.WatchRecord`: 사용자별 시청 영화, 별점, 감상평
- `movies.ReviewReaction`, `movies.ReviewComment`: 리뷰 반응과 댓글
- `social.Friendship`: 친구 요청/수락 상태
- `social.Notification`: 친구 요청/수락 알림

## 5. 데이터 구축

영화 데이터는 TMDB API를 기반으로 수집하고, 서비스에서 바로 로드할 수 있도록 Django fixture로 포함했습니다.

- fixture 경로: `backend/movies/fixtures/movies.json`
- 영화 수: 3,744편
- 장르 수: 19개
- 키워드 수: 14,472개
- 포함 정보: 제목, 원제, 줄거리, 개봉일/연도, 러닝타임, 평점, 투표 수, 언어, 포스터, 감독, 출연진, 장르, 키워드, 예고편 키, 취향 지도 좌표

빠른 시작 시 다음 명령으로 동일한 영화 데이터를 로드할 수 있습니다.

```bash
cd backend
python manage.py loaddata movies
```

## 6. 추천 알고리즘 설명

무비무비의 추천은 전역 영화 좌표와 사용자 시청 기록을 기반으로 동작합니다.

- 전역 영화 좌표: 영화의 장르, 키워드 등 특징을 기반으로 2D 취향 지도 좌표를 생성하고 fixture에 저장합니다.
- 안전 추천: 사용자가 높게 평가한 영화 집합과 가까운 미시청 영화를 추천합니다.
- 미탐색 추천: 사용자의 시청 분포가 낮은 영역에서 대륙별 다양성을 고려해 새로운 영화를 추천합니다.
- 지도 탐색 추천: 취향 지도 위에서 안전 추천과 미탐색 추천을 함께 보여줍니다.
- 친구 추천: 두 사용자의 시청 영화 집합 모두와 가까운 영화를 같이 볼 영화 후보로 제공합니다.
- AI 챗봇 추천: 서버가 만든 후보 목록 안에서만 GMS가 자연어 추천 이유를 생성하도록 제한해 환각을 줄입니다.

세부 결정과 실험 기록은 `docs/08_journal/`에 작업 단위로 정리했습니다.

## 7. 핵심 기능

### 인증 및 온보딩

사용자는 회원가입 후 영화 5편 이상을 등록해야 서비스 내부로 진입할 수 있습니다. 온보딩 완료 여부는 사용자 모델에 저장됩니다.

### 영화 검색 및 상세

영화 검색, 상세 정보, OTT 제공 정보, 예고편, 리뷰와 댓글을 제공합니다. OTT 정보는 TMDB watch providers를 서버에서 조회하고 캐싱합니다.

### 시청 기록과 리뷰

사용자는 본 영화에 별점과 감상평을 남길 수 있습니다. 별점은 추천과 취향 지도에 활용됩니다.

### 취향 지도

사용자가 본 영화는 지도 위의 별 또는 포스터로 표시됩니다. 영화 좌표는 모든 사용자에게 동일하고, 사용자의 시청 기록에 따라 지도 경험이 달라집니다.

### 추천

안전 추천, 미탐색 추천, 오늘의 추천, 지도 탐색 추천을 제공합니다. 추천 후보는 사용자가 아직 보지 않은 영화 중에서 구성됩니다.

### 커뮤니티

친구 요청, 친구 목록, 친구 취향 비교, 같이 볼 영화 추천, 알림, 리뷰 반응과 댓글을 제공합니다.

### 생성형 AI 활용

GMS API를 사용해 영화 추천 챗봇과 같이 볼 영화 챗봇을 구현했습니다. AI는 후보 목록 밖의 영화를 추천하지 않도록 서버 프롬프트에서 제한합니다.

## 8. REST API 구조

주요 API는 다음과 같이 구성했습니다.

- `/api/auth/`, `/api/auth/registration/`: 인증
- `/api/accounts/`: 계정, 온보딩, 프로필
- `/api/movies/`: 영화 목록, 상세, 장르, 리뷰, OTT/예고편
- `/api/watch-records/`: 시청 기록
- `/api/social/`: 친구, 알림, 같이 볼 영화
- `/api/taste/`: 취향 지도, 추천, 지도 탐색, 챗봇

HTTP Method와 상태 코드는 DRF의 generic view/APIView를 기반으로 기능별 의미에 맞게 사용했습니다.

## 9. 로컬 실행 방법

### 9.1 환경변수

```bash
cp .env.example .env
```

`.env`에 다음 값을 채웁니다.

- `TMDB_API_KEY`
- `GMS_KEY`
- 필요 시 `DJANGO_SECRET_KEY`

`.env`는 `.gitignore`에 포함되어 있으며 커밋하지 않습니다.

### 9.2 DB 실행

```bash
docker compose up -d
```

### 9.3 백엔드 실행

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata movies
python manage.py runserver
```

추천 데이터 파이프라인을 직접 재생성하려면 ML 의존성을 추가로 설치합니다.

```bash
pip install -r requirements-ml.txt
python manage.py import_movies --count 2000
python manage.py build_coords
```

### 9.4 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

기본 접속 주소는 `http://localhost:5173`입니다.

## 10. 문서 산출물

| 문서 | 위치 |
|---|---|
| 기능 명세서 | `docs/01_functional_spec.docx` |
| ERD | `docs/02_erd.png`, `docs/02_erd.svg`, `docs/02_erd.dbml` |
| 와이어프레임 | `docs/03_wireframe.html` |
| 일정/WBS | `docs/04_schedule.xlsx`, `docs/04_gantt.png` |
| 협업 규칙 | `docs/05_collaboration_rules.docx`, `docs/notion/collaboration_rules.md` |
| GitHub Flow 다이어그램 | `docs/06_github_flow.png` |
| Docker/PostgreSQL 가이드 | `docs/07_docker_postgres_guide.md` |
| 개발 일지 | `docs/08_journal/` |
| 기술 노트 | `docs/09_tech_notes.docx` |
| 프로젝트 구조 | `docs/10_project_structure.md` |
| 로컬 세팅 | `docs/11_local_setup.md` |

## 11. 협업 방식

협업 규칙은 GitHub Flow 기반으로 정리했습니다.

- `master` 직접 push 금지
- 기능별 브랜치 생성
- Conventional Commits 사용
- MR 작성 및 상대 1명 승인 후 머지
- `.gitlab/merge_request_templates/Default.md` 템플릿 사용
- `.env`, API Key 등 시크릿 커밋 금지

상세 내용은 `docs/notion/collaboration_rules.md`와 `docs/05_collaboration_rules.docx`를 참고합니다.

## 12. 서비스 URL

현재 프로젝트는 로컬 시연 범위로 진행했습니다.

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

별도 배포 URL은 없습니다.

> 하위 문서: 백엔드 상세는 [`backend/README.md`](backend/README.md), 프론트엔드 상세는 [`frontend/README.md`](frontend/README.md)를 참고하세요.

## 13. 회고 — 배운 점과 어려웠던 점

구현 과정에서 학습한 내용·시행착오·개선 결정을 정리했습니다. 작업 단위의 상세 기록은 `docs/08_journal/`(A-01 ~ A-15)에 있습니다.

### 가장 크게 헤맸고, 그래서 가장 많이 배운 것 — "사용자 좌표"의 폐기

처음에는 사용자의 평점 가중 평균점을 지도에 한 점("사용자 좌표")으로 찍고, 그 점에서 가까운 영화를 추천하는 직관적인 방식으로 시작했습니다(A-05). 그런데 한 사람이 액션과 멜로를 모두 좋아하는 **멀티모달 취향**이면, 두 봉우리의 평균점이 **아무것도 없는 골짜기**에 떨어져 엉뚱한 장르를 추천하는 문제가 드러났습니다(A-08). 또 좌표의 원점 자체가 임의적이라 "중심점"이 취향을 의미 있게 담지 못했습니다(A-06).

결국 **"사용자 좌표/센트로이드" 개념을 완전히 폐기**하고, 추천·지도·친구 비교 전부를 **사용자의 "시청 영화 집합"과 그 밀도(KDE)** 기준으로 다시 설계했습니다(A-15). "당연해 보이는 평균"이 왜 틀렸는지를 데이터로 확인한 것이 이번 프로젝트에서 가장 값진 학습이었습니다.

### 그 외 기술적 도전과 배운 점

- **전역 좌표 불변식**: 영화 좌표는 모든 사용자에게 동일하고 고정되어야 합니다. 새 영화가 들어와도 저장된 모델의 `transform()`만 쓰고 **절대 재학습(re-fit)하지 않습니다** — 재학습하면 모두의 좌표가 흔들려 친구 취향 비교가 깨지기 때문입니다(A-14).
- **추천 쏠림 해결**: 단일 점/2D kNN은 가장 밀집한 한 장르로만 추천이 쏠렸습니다. 좋아한 영화 *각각*의 고차원 임베딩 최근접을 **라운드로빈**으로 돌려 모든 취향 봉우리를 골고루 추천하도록 바꿨습니다(A-15).
- **미탐색(새로운 취향) 다양성**: KDE 저밀도 영역을 장르 "대륙"별로 분산해, 필터 버블 밖이면서도 한쪽으로 치우치지 않게 했습니다(A-13).
- **SSE 스트리밍 + 토큰 인증**: 챗봇·알림 실시간 갱신을 `EventSource` 대신 `fetch` + `ReadableStream`으로 구현해 `Authorization` 헤더를 실어 보냈고, 멀티바이트(한글) 청크 경계를 안전하게 합쳤습니다.
- **LLM 환각 억제**: 추천 챗봇이 후보 목록 **밖의 영화를 지어내지 않도록** 서버에서 grounding 후보를 프롬프트에 고정했습니다.
- **지도 시각화**: 컴포넌트 라이브러리 없이 SVG로 직접 그렸고, 좌표가 겹치는 별·핀은 황금각 나선으로 분산했습니다.

### 어려웠던 점

- 추천 "품질"은 테스트로 잡기 어려워, 실제 데이터로 결과를 눈으로 확인하며 여러 번 재설계해야 했습니다.
- 전역 좌표의 안정성(재현성)과 ML 의존성(numpy/scipy/scikit-learn)의 빌드·런타임 분리를 신경 써야 했습니다.

### 느낀 점

<!-- 팀원 각자의 소감을 채워주세요. 예: 협업(GitLab Flow)에서 배운 점, 데이터 기반 의사결정의 가치, 다음에 시도해보고 싶은 것 등 -->

- 김호준:
- 제하얀:
