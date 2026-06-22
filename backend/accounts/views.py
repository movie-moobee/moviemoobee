from rest_framework.response import Response
from rest_framework.views import APIView

ONBOARDING_MIN = 5


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
