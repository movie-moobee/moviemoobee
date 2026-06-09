from django.conf import settings
from django.db import models

class Friendship(models.Model):
    # ERD: friendships.  요청·수락(맞팔), 한 행으로 양방향(F-FRD).
    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        ACCEPTED = "accepted", "accepted"
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_requests")
    addressee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_requests")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["requester", "addressee"], name="uniq_friendship")]

class Notification(models.Model):
    # ERD: notifications.  친구 요청/수락 알림(F-NTF-01). 실시간 push 없이 REST 조회 + 안읽음 배지.
    class Type(models.TextChoices):
        FRIEND_REQUEST = "friend_request", "friend_request"   # 요청 생성 → 수신자에게
        FRIEND_ACCEPT  = "friend_accept",  "friend_accept"    # 수락 → 요청자에게

    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acted_notifications")
    type       = models.CharField(max_length=20, choices=Type.choices)
    friendship = models.ForeignKey(Friendship, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]   # 최신 알림 먼저