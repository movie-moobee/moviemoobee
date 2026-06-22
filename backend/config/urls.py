from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from .views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health),  # 임시 연결 확인용(세팅 검증). 기능 구현 아님.
    # 인증: 로그인/로그아웃/유저/비번 (F-AUTH-02·03) + 회원가입 (F-AUTH-01)
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/movies/", include("movies.urls")),
    path("api/watch-records/", include("movies.watch_urls")),  # 시청기록 CRUD (F-WAT·온보딩)
    path("api/social/", include("social.urls")),
    path("api/taste/", include("taste.urls")),
]

# 개발(DEBUG) 중 업로드 사진(MEDIA) 서빙. 운영은 웹서버(nginx 등)가 담당.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
