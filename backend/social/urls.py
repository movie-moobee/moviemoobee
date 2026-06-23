from django.urls import path

from . import views

# 친구 (F-FRD-01~04). 마운트: config.urls 의 "api/social/".
urlpatterns = [
    path("users/search/", views.UserSearchView.as_view()),            # 친구 검색
    path("friendships/", views.FriendRequestView.as_view()),          # 요청 생성(POST)
    path("friendships/received/", views.ReceivedRequestsView.as_view()),  # 받은 요청 목록
    path("friendships/<int:pk>/accept/", views.FriendRequestAcceptView.as_view()),  # 수락
    path("friendships/<int:pk>/", views.FriendRequestRejectView.as_view()),         # 거절(DELETE)
    path("friends/", views.FriendListView.as_view()),                 # 친구 목록 (5.2)
    path("friends/<int:pk>/", views.FriendDetailView.as_view()),      # 친구 프로필 / 끊기 (5.2)
    path("friends/<int:pk>/compare/", views.FriendCompareView.as_view()),  # 취향 비교 지도 (5.3)
    path("notifications/", views.NotificationListView.as_view()),         # 알림 목록 / 모두읽음 (5.5)
    path("notifications/unread/", views.NotificationUnreadView.as_view()),  # 안읽음 배지 개수 (5.5)
]
