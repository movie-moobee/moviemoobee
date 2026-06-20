from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

User = get_user_model()


class CustomRegisterSerializer(RegisterSerializer):
    """회원가입(F-AUTH-01). dj-rest-auth 기본(email/password1/password2)에
    nickname(필수)·profile_image_url(선택)을 추가한다."""

    # username은 API에서 안 받음 → allauth가 email로부터 자동 생성(충돌 시 suffix)
    username = None

    nickname = serializers.CharField(max_length=50)  # required 기본값=필수
    profile_image_url = serializers.CharField(
        max_length=500, required=False, allow_blank=True,  # 선택
    )

    def validate_nickname(self, value):
        # 모델 unique 제약을 깔끔한 400으로 선검증
        if User.objects.filter(nickname=value).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value

    def get_cleaned_data(self):
        data = super().get_cleaned_data()  # email/password1/password2
        data["nickname"] = self.validated_data.get("nickname", "")
        data["profile_image_url"] = self.validated_data.get("profile_image_url", "")
        return data

    def custom_signup(self, request, user):
        # allauth가 유저 생성(username 자동 채움) 후 호출하는 훅
        user.nickname = self.cleaned_data["nickname"]
        url = self.cleaned_data.get("profile_image_url")
        if url:  # 비었으면 모델 기본값(null) 유지
            user.profile_image_url = url
        user.save()


class UserDetailsSerializer(serializers.ModelSerializer):
    """GET /api/auth/user/ 응답. 프론트 가드가 onboarded로 진입 판단."""

    class Meta:
        model = User
        fields = ["pk", "email", "nickname", "profile_image_url", "onboarded"]
        read_only_fields = ["pk", "email", "onboarded"]  # onboarded는 완료 API로만 변경
