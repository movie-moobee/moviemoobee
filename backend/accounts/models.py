from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # ERD: users.  email 로그인 등 세부 정책은 추후(F-AUTH).
    nickname = models.CharField(max_length=50, unique=True)
    profile_image_url = models.CharField(max_length=500, blank=True, null=True)
    # 온보딩(영화 5편 등록) 완료 여부. 한 번 True면 유지(시청 편수가 줄어도 안 풀림).
    # → 가입 후 온보딩 미완 유저의 내부 진입 차단용 (F-ONB-01).
    onboarded = models.BooleanField(default=False)
    # 파생·캐싱: 별점 가중 사용자 좌표 (개발자 A 가 별점 변경 시 갱신; F-MAP-00)
    coord_x = models.FloatField(null=True, blank=True)
    coord_y = models.FloatField(null=True, blank=True)
    coord_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nickname or self.username
