from django.urls import path

from accounts.views import (
    AccountDeleteView,
    AvailabilityCheckView,
    AvatarDeleteView,
    OnboardingCompleteView,
)

urlpatterns = [
    # GET: 회원가입용 이메일·닉네임 중복 확인(공개) — F-AUTH-01
    path("check-availability/", AvailabilityCheckView.as_view(), name="check-availability"),
    # POST: 온보딩 완료(시청 5편 검증 후 onboarded=True) — F-ONB-01
    path("onboarding/complete/", OnboardingCompleteView.as_view(), name="onboarding-complete"),
    # DELETE: 본인 계정 삭제(Hard) — F-AUTH-05
    path("me/", AccountDeleteView.as_view(), name="account-delete"),
    # DELETE: 프로필 사진 삭제 — F-AUTH-04
    path("me/avatar/", AvatarDeleteView.as_view(), name="avatar-delete"),
]
