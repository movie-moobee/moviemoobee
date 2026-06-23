from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # ERD: users.  email 로그인 등 세부 정책은 추후(F-AUTH).
    nickname = models.CharField(max_length=50, unique=True)
    # 프로필 사진: 파일 업로드(MEDIA/avatars). 선택. 응답은 URL(profile_image_url)로 노출.
    profile_image = models.ImageField(upload_to="avatars/", blank=True, null=True)
    # 온보딩(영화 5편 등록) 완료 여부. 한 번 True면 유지(시청 편수가 줄어도 안 풀림).
    # → 가입 후 온보딩 미완 유저의 내부 진입 차단용 (F-ONB-01).
    onboarded = models.BooleanField(default=False)

    def __str__(self):
        return self.nickname or self.username
