# 무비무비 · Docker + PostgreSQL 세팅 가이드

> 둘 다 PostgreSQL이 처음이어도 따라만 하면 됩니다. 핵심은 **"Postgres를 다루는 게 아니라, Docker로 한 번 띄우고 Django가 연결되게 설정 한 번"** 입니다.
> 한 번 세팅하면 그 뒤 개발 경험은 SQLite와 똑같습니다.

준비물: **Docker Desktop** 설치 (Windows/Mac). 설치 후 실행해 두세요.

```bash
docker --version
docker compose version     # v2. 안 되면 docker-compose --version (구버전)
```

---

## 1. 파일 배치
레포 루트에 아래 파일이 있어야 합니다(이미 만들어 드림):
- `docker-compose.yml`
- `.env.example` → 복사해서 `.env` 생성:

```bash
cp .env.example .env
# .env 의 TMDB_API_KEY 만 본인 키로 채우면 됩니다. DB 값은 기본값 그대로 OK.
```

---

## 2. PostgreSQL 띄우기 (한 줄)
```bash
docker compose up -d
docker compose ps          # STATUS 가 healthy 면 성공
```
- 처음엔 이미지 다운로드로 30초~1분 걸립니다.
- (선택) 브라우저 DB 뷰어: http://localhost:8080
  - System=**PostgreSQL**, Server=**db**, Username/Password/Database=**moviemoobee**
  - ※ Adminer는 컨테이너끼리라 Server가 `localhost`가 아니라 `db` 입니다.

끄고 켜기:
```bash
docker compose down        # 끄기 (데이터 유지)
docker compose up -d       # 다시 켜기
```

---

## 3. Django 연결

### 3-1. 패키지 설치 (requirements.txt 에 추가)
```
Django==5.2
djangorestframework
psycopg[binary]      # PostgreSQL 드라이버
python-dotenv        # .env 로드 (선택)
```
```bash
pip install -r requirements.txt
```

### 3-2. settings.py
```python
import os
from pathlib import Path
from dotenv import load_dotenv               # python-dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")               # .env 자동 로드

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "moviemoobee"),
        "USER": os.environ.get("POSTGRES_USER", "moviemoobee"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "moviemoobee"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
```

### 3-3. 마이그레이션 & 확인
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
`migrate` 가 에러 없이 끝나면 연결 성공입니다. 끝!

---

## 4. 시연 켜는 순서 (발표 노트북 기준)
1. Docker Desktop 실행
2. `docker compose up -d` → `docker compose ps` healthy 확인
3. `python manage.py migrate`
4. `python manage.py loaddata movies` 로 영화 3,744편 fixture 적재
5. `python manage.py runserver` + 프론트 `npm run dev`

> DB 볼륨은 각자 로컬에만 있습니다. 영화 카탈로그는 `loaddata movies` fixture로 동일하게 맞추고, 개인 시청 데이터는 각 PC에서 직접 만들거나 `seed_demo`로 생성합니다.

---

## 5. 트러블슈팅 (처음에 잘 만나는 것들)

| 증상 | 원인 / 해결 |
|---|---|
| `port 5432 ... already in use` | 로컬에 다른 Postgres가 5432 사용 중. `docker-compose.yml` 포트를 `"5433:5432"` 로 바꾸고 `.env` 의 `POSTGRES_PORT=5433` 도 변경 후 `docker compose up -d` |
| `connection refused` | 컨테이너가 아직 안 떴음 → `docker compose ps` 로 healthy 대기. Django HOST가 `localhost` 인지 확인 |
| `password authentication failed` / `role ... does not exist` / `database ... does not exist` | **볼륨에 처음 만든 계정이 박혀 있어서** `.env` 를 나중에 바꾸면 안 맞음. 개발 초기엔 `docker compose down -v` 로 볼륨 초기화 후 다시 `up -d` (데이터 삭제 주의) |
| `psycopg` 설치 실패 | `pip install "psycopg[binary]"`. 그래도 안 되면 `psycopg2-binary` 사용 |
| Django가 `.env` 를 못 읽음 | `python-dotenv` 설치 + `load_dotenv` 경로 확인. 또는 셸에서 직접 export |
| 컨테이너 로그 보고 싶다 | `docker compose logs -f db` |

---

## 6. 협업 · 안전 수칙
- `.env` 는 **커밋 금지**(`.gitignore` 에 이미 등록). 팀엔 `.env.example` 만 공유하고 키는 별도 채널로.
- DB 데이터는 각자 로컬 → **시드 스크립트**로 재현(다음 단계에서 Django 관리 커맨드로 제공).
- CI 초안은 `disabled-gitlab-ci.yml`에 보관되어 있습니다. 현재는 로컬 시연 기준이라 GitLab Runner 파이프라인은 비활성화되어 있습니다.
- `down` 은 데이터 유지, `down -v` 는 데이터 삭제 — `-v` 는 "초기화하고 싶을 때만".
