# A-01 · 초기 환경 세팅 & 부팅·연결 검증

- 날짜 / 일정ID / 담당: 2026-06-06 · 일정 0.1 기반 · 공통(A가 작성)
- 브랜치 / 커밋: `master` · `chore(infra): 초기 스캐폴드 + 개발환경 부팅·연결 세팅`
- 한 줄 요약: 페어가 `pull` 받아 바로 작업할 수 있도록 **Django·Vue·PostgreSQL이 한 줄로 연결**되는 것까지 맞춰 두었다. (기능 구현은 아직 없음)

## 만진 파일 (폴더/파일 — 역할)
- **이름 정리** `moviemovie → moviemoobee`: `README.md`, `CLAUDE.md`, `.gitlab-ci.yml`, `docker-compose.yml`(컨테이너명), `frontend/package.json`, `backend/config/settings.py`(DB 기본값), `docs/*`(텍스트·docx 포함) — 프로젝트명 불일치 제거.
- `backend/config/settings.py` — `SECRET_KEY`를 `.env`의 `DJANGO_SECRET_KEY`에서 읽도록(이미 그 구조였음, 점검). DB 기본값을 `moviemoobee`로 정합화.
- `.env.example` / `.env` — `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` 항목 추가. (`.env`는 절대 커밋 안 함 — `.gitignore`에 등록됨)
- `backend/config/views.py` *(신규)* — **임시** 연결 확인용 `/api/health` 뷰. DB에 `SELECT 1`을 날려 `{"status":"ok","db":true}` 반환.
- `backend/config/urls.py` — 위 health 라우트(`path("api/health", health)`) 연결.
- `backend/{accounts,movies,social}/migrations/0001_initial.py` *(신규)* — ERD 모델의 **최초 마이그레이션**. (`taste`는 모델이 없어 마이그레이션 없음 — 정상)
- `frontend/src/views/MainView.vue` — `<script setup>`(Composition API)으로 마운트 시 `/api/health`를 호출해 화면에 "연결 상태: 백엔드 OK · DB OK" 표시. **임시 검증용**.
- `frontend/.eslintrc.cjs` — `ignorePatterns: ["dist/", "node_modules/"]` 추가. (빌드 산출물 `dist/`까지 린트해서 에러나던 문제 차단)
- `frontend/package-lock.json` *(신규)* — `npm install`로 의존성 잠금 생성.

## 어떻게 / 왜
- **왜 health 엔드포인트?** "프론트(5173) → 프록시 → 백엔드(8000) → DB(Postgres)"가 **한 줄로 살아있다**는 걸 코드 한 개로 증명하려고. 기능이 아니라 배선 점검용이라 `config`(공통 영역)에 두고 "임시"라고 표기.
- **왜 `config/`에 뒀나?** health는 특정 도메인(accounts/movies/...) 소속이 아니라 인프라성. 그래서 앱이 아니라 프로젝트 공통 `config`에 배치.
- **왜 마이그레이션을 지금?** DB 스키마가 있어야 `migrate`가 돌고 `/admin`·health가 동작. ERD = 모델 = 마이그레이션 순서로 고정.

## 기능 동작 (흐름)
```
브라우저(MainView, 5173) --onMounted--> GET /api/health
   └ vite 프록시가 /api 를 :8000 으로 전달
        └ Django health 뷰가 DB에 SELECT 1
             └ {"status":"ok","db":true} 반환 → 화면에 "백엔드 OK · DB OK"
```

## 검증
- `python manage.py migrate` 성공 · `/admin/` 302(정상) · `/api/health` 200 `{"db":true}`
- `npm run lint`/`build` 통과 · vite 프록시 통과 health 200
- `.env` 미커밋 확인, 무시 산출물(node_modules/.venv/dist) 제외 확인

## 배운 점 · 주의
- **Docker가 안 뜨던 원인**: Docker Desktop의 `EnableDockerAI`(Model Runner/Inference)가 소켓 경로 초기화에 실패 → 엔진 부팅을 막음. `settings-store.json`에서 `EnableDockerAI/ModelRunnerEnabled/EnableInference`를 끄면 해결.
- 포트 **8000**은 다른 프로젝트가 점유할 수 있음(겪었음). 비우고 시작할 것.
- Docker는 **PostgreSQL 컨테이너 용도로만** 씀. Django/Vue는 호스트에서 실행.
