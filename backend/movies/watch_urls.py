from django.urls import path

from movies.views import WatchRecordDetailView, WatchRecordListCreateView

# /api/watch-records/  (F-WAT-01/03/04 · 온보딩 F-ONB-01 공용)
urlpatterns = [
    path("", WatchRecordListCreateView.as_view(), name="watchrecord-list"),
    path("<int:pk>/", WatchRecordDetailView.as_view(), name="watchrecord-detail"),
]
