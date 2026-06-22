from django.urls import path

from accounts.views import AccountDeleteView, OnboardingCompleteView

urlpatterns = [
    # POST: 온보딩 완료(시청 5편 검증 후 onboarded=True) — F-ONB-01
    path("onboarding/complete/", OnboardingCompleteView.as_view(), name="onboarding-complete"),
    # DELETE: 본인 계정 삭제(Hard) — F-AUTH-05
    path("me/", AccountDeleteView.as_view(), name="account-delete"),
]
