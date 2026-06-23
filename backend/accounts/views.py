from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

ONBOARDING_MIN = 5


class AvailabilityCheckView(APIView):
    """회원가입용 이메일·닉네임 중복 확인 (F-AUTH-01). 가입 흐름의 공개 엔드포인트
    (비로그인에서 1단계 '다음' 시 즉시 검사 → 비번까지 안 가고 중복 안내).
    이메일은 allauth와 동일하게 대소문자 무시, 닉네임은 DB unique(정확히 일치) 기준."""

    permission_classes = [AllowAny]

    def get(self, request):
        out = {}
        email = request.query_params.get("email", "").strip()
        nickname = request.query_params.get("nickname", "").strip()
        if email:
            out["email_taken"] = User.objects.filter(email__iexact=email).exists()
        if nickname:
            out["nickname_taken"] = User.objects.filter(nickname=nickname).exists()
        return Response(out)


class OnboardingCompleteView(APIView):
    """온보딩 완료 처리 (F-ONB-01). 시청 5편 이상일 때만 onboarded=True.
    클라이언트가 5편 미만으로 임의로 켜지 못하게 백엔드가 편수를 검증한다."""

    def post(self, request):
        user = request.user
        if user.watch_records.count() < ONBOARDING_MIN:
            return Response(
                {"detail": f"영화를 {ONBOARDING_MIN}편 이상 등록해야 합니다."},
                status=400,
            )
        if not user.onboarded:
            user.onboarded = True
            user.save(update_fields=["onboarded"])  # 좌표 시그널과 무관(필드 한정 저장)
        return Response({"onboarded": True})


class AccountDeleteView(APIView):
    """계정 삭제 (F-AUTH-05). Hard delete — 본인 계정을 즉시 영구 삭제.
    cascade로 시청기록·친구관계·알림·토큰까지 함께 삭제됨(복구 불가)."""

    def delete(self, request):
        request.user.delete()
        return Response(status=204)


class AvatarDeleteView(APIView):
    """프로필 사진 삭제 (F-AUTH-04). 미디어 파일 제거 + 필드 비움 → 기본 아바타로.
    응답 키는 프로필 응답과 동일하게 profile_image_url(null)."""

    def delete(self, request):
        user = request.user
        if user.profile_image:
            user.profile_image.delete(save=False)  # 저장된 미디어 파일도 삭제
            user.profile_image = None
            user.save(update_fields=["profile_image"])
        return Response({"profile_image_url": None})
