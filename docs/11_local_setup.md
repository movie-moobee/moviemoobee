# 11 · 다른 PC에서 로컬 환경 세팅 (수동)

회사 PC ↔ 집 PC 처럼 **새 PC에서 프로젝트를 띄우는 방법**. 같은 사람이든 페어든 동일.
핵심 원칙: **옮겨다니는 건 코드(git) + 시크릿(.env)뿐.** `.venv`·`node_modules`·DB 데이터는 **각 PC에 따로** 둔다(동기화 X).

> 파이썬 버전은 PC마다 달라도 됨(우리 의존성은 3.11·3.12 둘 다 OK). venv가 PC-로컬이라 서로 안 섞인다.

---

## 0. 새 PC에 한 번만 설치할 도구
- **Git**
- **Python 3.11** (3.12도 동작. 권장은 팀 통일을 위해 3.11)
- **Node.js** (LTS)
- **Docker Desktop** (PostgreSQL 컨테이너용)

---

## 1. 최초 1회 세팅

### 1-1. 레포 클론
```bash
git clone https://lab.ssafy.com/000304jun/13-pjt.git
cd 13-pjt
```

### 1-2. .env 만들기 (레포 루트)
`.env`는 커밋되지 않으므로 **새 PC에서 직접 생성**한다. 예시를 복사해 값만 채운다.
```bash
cp .env.example .env
```
채울 값:
| 키 | 값 |
|---|---|
| `TMDB_API_KEY` | **본인 TMDB v4 Read Access Token** (필수 — 영화 상세 OTT·import 용) |
| `DJANGO_SECRET_KEY` | 비워도 dev 기본값 동작. 채우려면: `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `POSTGRES_*` | 기본값 그대로 두면 됨(아래 docker-compose와 일치) |

> ⚠️ `.env`는 **절대 커밋 금지**. TMDB 키는 USB/비번관리자 등 안전 채널로만 가져온다.

### 1-3. PostgreSQL 띄우기 (Docker)
```bash
docker compose up -d        # db(+adminer) 컨테이너 기동
docker compose ps           # 상태 확인 (db가 healthy면 OK)
```

### 1-4. 백엔드 (Django)
```bash
cd backend
py -3.11 -m venv .venv                 # (mac/linux: python3.11 -m venv .venv)

# 가상환경 활성화
.venv\Scripts\Activate.ps1             # PowerShell
# source .venv/Scripts/activate        # Git Bash (Windows)
# source .venv/bin/activate            # mac/linux

pip install -r requirements.txt -r requirements-ml.txt   # 웹 + ML 스택(첫 설치 수 분)

python manage.py migrate               # 스키마 생성
python manage.py loaddata movies       # 영화·좌표·예고편 시드(TMDB 재수집 불필요)
python manage.py runserver             # http://localhost:8000
```
검증: `python -c "import numpy,scipy,sklearn,umap,numba,pandas; print('ml ok')"` / `python manage.py check`

### 1-5. 프론트엔드 (Vue) — 새 터미널
```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173 (/api → localhost:8000 자동 프록시)
```

### 1-6. 계정 만들기
브라우저에서 회원가입 → 영화 5편 등록(온보딩)하면 지도·추천이 켜진다.
(테스트 데이터가 필요하면: `python manage.py seed_genre_demos` 또는 `python manage.py seed_demo`)

---

## 2. 매일 — 두 PC 오가며 작업하기
**떠나기 전 commit+push, 도착하면 pull.** 이 습관이 전부.
```bash
# 떠나는 PC
git add -A
git commit -m "wip: 작업 내용"        # feature 브랜치에서!
git push

# 도착한 PC
git pull
```
- 새 작업은 **항상 feature 브랜치부터**(`git switch -c feat/...`). master 직접 편집 금지.
- 어중간하면 `wip:` 커밋으로 밀어두고, 다음에 이어서 → 마무리 시 `git commit --amend`로 다듬기.

---

## 3. 두 번째 PC부터는 (이미 한 번 해봤다면)
처음과 동일하되, **이미 받은 변경이 있으면**:
```bash
git pull
cd backend && source .venv/Scripts/activate   # 기존 venv 재사용
pip install -r requirements.txt -r requirements-ml.txt   # 의존성 추가됐을 때만
python manage.py migrate                       # 새 마이그레이션 있을 때
python manage.py runserver
# 프론트: cd frontend && npm install (package.json 바뀌었으면) && npm run dev
```

---

## 4. 자주 겪는 문제
| 증상 | 해결 |
|---|---|
| `ModuleNotFoundError: django/numpy...` | venv 활성화 안 됨, 또는 `pip install` 누락 → 활성화 후 requirements 2개 설치 |
| DB 연결 실패 | `docker compose ps`로 db healthy 확인. 5432 포트 충돌이면 compose에서 `5433:5432`로 바꾸고 `.env`의 `POSTGRES_PORT`도 맞춤 |
| 지도·추천이 비어 있음 | `loaddata movies` 안 했거나, 시청 5편 미만(게이트). 등록 5편 채우기 |
| `.env` 못 읽음 | 위치가 **레포 루트**여야 함(backend 안 아님) |
| `npm run build`가 죽음 | 호스트 Node/esbuild 환경 이슈 — **개발은 `npm run dev`로** (dev는 정상) |
| venv가 꼬임 | `.venv` 폴더 삭제 후 1-4 다시 |

---

## 5. PC 사이에 **안 따라오는 것** (주의)
- **DB 데이터(내 계정·시청·별점)**: 회사·집 로컬 DB가 각각이라 동기화 안 됨. 영화 카탈로그는 `loaddata movies`로 동일하게 맞춰지지만, 개인 시청 데이터는 각 PC에서 다시 만들거나 seed로 채운다.
- **`.venv` / `node_modules`**: 각 PC에서 생성(복사·동기화 금지).
- **`.env`**: 각 PC에서 직접 생성(커밋 금지).
- **`backend/taste/artifacts/coords_model.pkl`**: gitignore됨. **새 영화를 추가/투영할 때만** 필요. 기존 픽스처로 돌리면 좌표가 이미 들어있어 없어도 앱은 정상.
- **`CLAUDE.md` · `status_by_KHJ.md`**(개인용, gitignore): AI 코딩 가이드와 작업 핸드오프 노트. git으로 안 따라오니 `.env`처럼 PC 옮길 때 직접 복사. 다른 PC에서 작업 이어받을 땐 `status_by_KHJ.md`를 먼저 읽으면 됨.

---

## 6. 한 줄 요약
```
git clone → cp .env.example .env(TMDB키) → docker compose up -d
→ backend: venv + pip(2개) + migrate + loaddata + runserver
→ frontend: npm install + npm run dev
→ 이후 매일: 떠날 때 push / 올 때 pull
```
