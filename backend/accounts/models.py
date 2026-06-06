from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # ERD: users.  email 로그인 등 세부 정책은 추후(F-AUTH).
    nickname = models.CharField(max_length=50, unique=True)
    profile_image_url = models.CharField(max_length=500, blank=True, null=True)
    # 파생·캐싱: 별점 가중 사용자 좌표 (개발자 A 가 별점 변경 시 갱신; F-MAP-00)
    coord_x = models.FloatField(null=True, blank=True)
    coord_y = models.FloatField(null=True, blank=True)
    coord_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nickname or self.username
