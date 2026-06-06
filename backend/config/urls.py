from django.contrib import admin
from django.urls import path, include

from .views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health),  # 임시 연결 확인용(세팅 검증). 기능 구현 아님.
    path("api/accounts/", include("accounts.urls")),
    path("api/movies/", include("movies.urls")),
    path("api/social/", include("social.urls")),
    path("api/taste/", include("taste.urls")),
]
