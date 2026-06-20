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
