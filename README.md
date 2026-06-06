# 무비무비 (MovieMoobee)

"좋아하는 영화"가 아니라 **"좋아하게 될 영화"** 를 추천하는 웹앱. 취향 지도에서 안 가본 영역(미탐색)을 찾아 필터 버블을 벗어나게 한다.

- **스택:** Vue 3 (Composition API) · Django REST Framework · PostgreSQL
- **범위:** 로컬 시연
- 작업 규칙은 `CLAUDE.md`, 협업 규칙은 별도 문서, 화면/기능은 기능명세서(F-ID) 기준.

## 폴더 구조
```
movie-moobee/
├─ CLAUDE.md                      # 바이브 코딩 가이드(도메인 불변식 포함)
├─ docker-compose.yml             # 로컬 PostgreSQL
├─ .env.example                   # 환경변수 예시 (.env 는 커밋 금지)
├─ .gitignore
├─ .gitlab-ci.yml                 # lint/test/build 파이프라인
├─ .gitlab/merge_request_templates/Default.md
├─ backend/                       # Django REST Framework
│  ├─ manage.py
│  ├─ requirements.txt            # 웹앱 의존성
│  ├─ requirements-ml.txt         # 데이터·추천(개발자 A): numpy/sklearn/umap...
│  ├─ config/                     # settings·urls·wsgi·asgi
│  ├─ accounts/                   # User·인증·프로필         (개발자 B)
│  ├─ movies/                     # Movie·Genre·Keyword·WatchRecord (개발자 B)
│  ├─ social/                     # Friendship              (개발자 B)
│  └─ taste/                      # 좌표·영역·추천·지도 데이터 (개발자 A)
│     ├─ services/  coords.py · areas.py · recommend.py
│     └─ management/commands/  import_movies.py · build_coords.py · seed_demo.py
└─ frontend/                      # Vue 3 + Vite (Composition API)
   ├─ package.json · vite.config.js · .eslintrc.cjs · index.html
   └─ src/
      ├─ main.js · App.vue
      ├─ router/index.js          # 화면 01~13 라우팅
      ├─ api/client.js            # axios (/api 프록시)
      ├─ views/                   # 페이지(화면별)
      ├─ components/
      └─ composables/  useTasteMap.js   (개발자 A)
```

## 담당 (수직 분담)
- **개발자 A — 지도·추천·데이터:** `backend/taste/`, 데이터 파이프라인(`management/commands`), `frontend/src/views/MapView·RecommendView`, `composables/useTasteMap`
- **개발자 B — 인증·콘텐츠·소셜:** `backend/accounts·movies·social/`, 그 외 프론트 화면
- **공통:** `config/`, 공통 셸·라우팅, 모델 변경 → MR + 상대 승인

## 처음 시작 (pull 받은 페어 포함)
```bash
# 0) 루트에서 환경변수
cp .env.example .env            # TMDB_API_KEY 채우기

# 1) DB 띄우기
docker compose up -d            # docker compose ps 로 healthy 확인

# 2) 백엔드
cd backend
python -m venv .venv && source .venv/bin/activate   # (윈도우: .venv\Scripts\activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver       # http://localhost:8000

# 3) 프론트 (새 터미널)
cd frontend
npm install
npm run dev                      # http://localhost:5173

# 4) 데이터(개발자 A) — 준비되면
cd backend && pip install -r requirements-ml.txt
python manage.py import_movies --count 2000
python manage.py build_coords
python manage.py seed_demo
```

자세한 DB 세팅·트러블슈팅은 Docker 가이드 문서 참고.
