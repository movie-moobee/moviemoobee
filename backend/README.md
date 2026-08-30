# 무비무비 — Backend (Django REST Framework)

무비무비의 API 서버입니다. **Django 5 + Django REST Framework**로 구현했고, 인증은 **DRF 토큰 인증**(dj-rest-auth + allauth), DB는 **PostgreSQL**을 사용합니다. 추천·좌표·KDE 같은 무거운 계산은 뷰가 아니라 **서비스 레이어/관리 명령**에서 처리합니다.

전체 서비스 개요·회고는 루트 [`../README.md`](../README.md)를 참고하세요.

## 1. 앱 구조

| 앱 | 책임 |
|---|---|
| `config` | settings · 루트 URLconf · WSGI |
| `accounts` | 사용자(`User`), 닉네임/프로필/온보딩, 회원정보 조회·수정 |
| `movies` | 영화·장르·키워드, 시청기록(`WatchRecord`), 리뷰 반응·댓글, OTT/예고편 |
| `social` | 친구(`Friendship`), 알림(`Notification`), 친구 취향 비교, 같이 볼 영화 챗봇, 챗봇 일일 사용량(`CowatchUsage`) |
| `taste` | 취향 지도·추천·지도 탐색·추천 챗봇 (서비스 레이어 + 관리 명령) |

## 2. API 라우트 (루트: `config/urls.py`)

| prefix | 내용 |
|---|---|
| `/api/auth/`, `/api/auth/registration/` | 로그인·로그아웃·회원가입·비밀번호 (dj-rest-auth) |
| `/api/accounts/` | 계정·온보딩·프로필 |
| `/api/movies/` | 영화 목록·상세·장르·리뷰·OTT/예고편 |
| `/api/watch-records/` | 시청기록 CRUD |
| `/api/social/` | 친구·알림·같이 볼 영화 챗봇·사용량 |
| `/api/taste/` | 취향 지도·추천·지도 탐색·추천 챗봇 |
| `/api/health` | 연결 확인용 (배포 시 keep-alive 핑 대상) |

## 3. 인증

- DRF **Token Authentication**. 로그인 시 토큰 발급 → 프론트가 `Authorization: Token <key>`로 전송.
- 기본 권한은 `IsAuthenticated`. 공개는 회원가입·로그인(dj-rest-auth 뷰가 자체 `AllowAny`)과 이메일·닉네임 중복 확인(`/api/accounts/check-availability/`)뿐.
- 이메일+비밀번호 로그인(allauth), 메일 인증은 로컬 시연용으로 생략(`ACCOUNT_EMAIL_VERIFICATION="none"`).

## 4. 서비스 레이어 (`taste/services/`)

무거운 로직은 뷰에서 분리해 여기에 둡니다.

| 모듈 | 역할 |
|---|---|
| `taste_map.py` | 취향 지도/친구 비교 데이터 구성 |
| `recommend.py` | 가까운 취향(시청 집합 고차원 최근접, 라운드로빈)·새로운 취향(KDE 저밀도) 추천 |
| `areas.py` | KDE(`scipy.stats.gaussian_kde`) 기반 탐색 밀도 |
| `chat.py` | 추천/같이 볼 영화 챗봇 메시지 구성 + SSE 제너레이터 |
| `gms.py` | SSAFY GMS(LLM 게이트웨이, OpenAI 호환) 클라이언트 |

### 도메인 불변식 (반드시 유지)
- 영화 좌표(`map_x`, `map_y`)는 **전역 고정·공유**. 신규 영화는 저장된 모델의 `transform()`으로만 투영하고 **재학습 금지**.
- **사용자 1점 좌표(센트로이드) 개념은 폐기**. 추천·지도·비교 모두 사용자의 *시청 영화 집합*과 KDE 기준.
- 시청기록은 별점 필수(0.5 단위). 리뷰는 선택.

## 5. 관리 명령 (`taste/management/commands/`)

좌표 생성 등 오프라인 파이프라인은 여기서 실행합니다(런타임 아님).

| 명령 | 역할 |
|---|---|
| `import_movies` | TMDB에서 영화 수집 |
| `build_coords` | 영화 전역 좌표 생성(TF-IDF→SVD→MDS, scikit-learn) |
| `prune_catalog` / `backfill_trailers` | 카탈로그 정리 / 예고편 보강 |
| `seed_demo` / `seed_genre_demos` | 데모 데이터 시드 |
| `gms_smoke` / `show_areas` | GMS 연결 점검 / KDE 영역 점검 |

## 6. 의존성

- `requirements.txt` — 런타임(웹 구동). Django·DRF·인증·`psycopg`·`requests`·`Pillow` + 런타임 계산용 `numpy`·`scipy`(KDE/추천) + 배포용 `gunicorn`·`whitenoise`.
- `requirements-ml.txt` — 좌표 생성(`build_coords`) 오프라인 전용. `-r requirements.txt` 위에 `scikit-learn`만 추가. 로컬에서만 필요.

> 런타임 코드(`areas.py`/`recommend.py`/`chat.py`)는 numpy·scipy를 import합니다. `scikit-learn`은 `build_coords`(오프라인)에서만 사용합니다.

## 7. 환경변수 (`.env`, 레포 루트)

```
POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_HOST / POSTGRES_PORT
DJANGO_SECRET_KEY / DJANGO_DEBUG
TMDB_API_KEY
GMS_KEY            # SSAFY LLM 게이트웨이 (서버 .env 에만, 클라이언트 노출 금지)
GMS_BASE_URL / GMS_MODEL   # 기본값 있음

# --- 배포 전용 (로컬은 생략 가능) ---
DJANGO_ALLOWED_HOSTS       # 콤마 구분 허용 도메인 (DEBUG=1 이면 전체 허용)
CSRF_TRUSTED_ORIGINS       # 예: https://my-app.onrender.com
CORS_ALLOWED_ORIGINS       # 배포 프론트 도메인 (기본: http://localhost:5173)
POSTGRES_SSLMODE           # Supabase 등 관리형 DB 는 require (기본 prefer)
```
`.env`는 커밋 금지(`.gitignore`). 예시는 루트 `.env.example` 참고.

## 8. 로컬 실행

```bash
# (레포 루트) DB
docker compose up -d

cd backend
python -m venv .venv && .venv\Scripts\Activate.ps1   # (bash: source .venv/Scripts/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata movies      # 영화 데이터(좌표 포함) 적재
python manage.py runserver            # http://localhost:8000
```

좌표를 직접 재생성하려면(선택):
```bash
pip install -r requirements-ml.txt
python manage.py import_movies --count 2000
python manage.py build_coords
```
