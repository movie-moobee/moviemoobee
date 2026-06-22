from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

User = get_user_model()


def build_image_url(image, context):
    """ImageField → 절대 URL(없으면 None). 리뷰 아바타·프로필 공용."""
    if not image:
        return None
    request = context.get("request")
    return request.build_absolute_uri(image.url) if request else image.url


class CustomRegisterSerializer(RegisterSerializer):
    """회원가입(F-AUTH-01). dj-rest-auth 기본(email/password1/password2)에
    nickname(필수)을 추가한다. 프로필 사진은 가입엔 안 받고 프로필 수정(F-AUTH-04)에서만."""

    # username은 API에서 안 받음 → allauth가 email로부터 자동 생성(충돌 시 suffix)
    username = None

    nickname = serializers.CharField(max_length=50)  # required 기본값=필수

    def validate_nickname(self, value):
        # 모델 unique 제약을 깔끔한 400으로 선검증
        if User.objects.filter(nickname=value).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value

    def get_cleaned_data(self):
        data = super().get_cleaned_data()  # email/password1/password2
        data["nickname"] = self.validated_data.get("nickname", "")
        return data

    def custom_signup(self, request, user):
        # allauth가 유저 생성(username 자동 채움) 후 호출하는 훅
        user.nickname = self.cleaned_data["nickname"]
        user.save()


class UserDetailsSerializer(serializers.ModelSerializer):
    """GET /api/auth/user/ 조회 + PATCH 수정(F-AUTH-04). 가드가 onboarded로 진입 판단.
    사진은 profile_image(파일·write)로 받고, 응답엔 profile_image_url(URL·read)로 노출."""

    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["pk", "email", "nickname", "profile_image", "profile_image_url", "onboarded"]
        read_only_fields = ["pk", "email", "onboarded"]  # onboarded는 완료 API로만 변경
        extra_kwargs = {"profile_image": {"write_only": True, "required": False}}

    def get_profile_image_url(self, obj):
        return build_image_url(obj.profile_image, self.context)

    def validate_nickname(self, value):
        # 수정 시 본인 제외 중복검사 → 깔끔한 400 (없으면 DB IntegrityError 500)
        qs = User.objects.filter(nickname=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value
