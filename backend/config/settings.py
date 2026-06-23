from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")  # 레포 루트의 .env 로드

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # allauth 의존
    # 3rd party
    "rest_framework",
    "rest_framework.authtoken",  # DRF 토큰 인증
    "corsheaders",
    "dj_rest_auth",  # 로그인/로그아웃/유저/비번
    "allauth",
    "allauth.account",
    "allauth.socialaccount",  # 미사용이나 dj-rest-auth registration이 import
    "dj_rest_auth.registration",  # 회원가입
    # local apps
    "accounts",
    "movies",
    "social",
    "taste",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # allauth 65 필수
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

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

AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"

# 업로드 파일(프로필 사진 등). 개발: 로컬 media/ 폴더 + DEBUG 시 static() 서빙(config/urls).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    # 09_tech_notes: Session → Token 전환 (모든 API 기본 인증)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    # 로그인 필수가 기본. 공개는 회원가입·로그인뿐(dj-rest-auth 뷰가 자체 AllowAny).
    # 영화 검색·조회 등 나머지 전 API는 IsAuthenticated 유지 — 로컬 뷰에 AllowAny 금지.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# --- 인증 (dj-rest-auth + allauth) · F-AUTH-01~05 ---
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # admin/username
    "allauth.account.auth_backends.AuthenticationBackend",  # 이메일 로그인
]
# allauth 65 신형 설정: 이메일+비번 로그인, 회원가입 입력 필드
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"  # 로컬 시연: 메일 인증 생략
ACCOUNT_UNIQUE_EMAIL = True
REST_AUTH = {
    "USE_JWT": False,  # DRF 토큰 방식 (09_tech_notes)
    "SESSION_LOGIN": False,
    "TOKEN_MODEL": "rest_framework.authtoken.models.Token",
    # 회원가입에 nickname(필수) 추가 (F-AUTH-01). 사진은 프로필 수정에서만.
    "REGISTER_SERIALIZER": "accounts.serializers.CustomRegisterSerializer",
    # /api/auth/user/ 조회·수정(F-AUTH-04): nickname·사진·onboarded
    "USER_DETAILS_SERIALIZER": "accounts.serializers.UserDetailsSerializer",
    # 비밀번호 변경 시 현재 비밀번호 확인 요구 (와이어프레임 09)
    "OLD_PASSWORD_FIELD_ENABLED": True,
}
# 로컬: 메일 발송 대신 콘솔 출력
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Vue 개발 서버
CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]

# TMDB
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

# GMS (SSAFY LLM 게이트웨이) — OpenAI 호환. 키는 .env 에만(절대 커밋·클라이언트 노출 금지).
GMS_KEY = os.environ.get("GMS_KEY", "")
GMS_BASE_URL = os.environ.get("GMS_BASE_URL", "https://gms.ssafy.io/gmsapi/api.openai.com/v1")
GMS_MODEL = os.environ.get("GMS_MODEL", "gpt-5-nano")
