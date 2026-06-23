from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Friendship, Notification


@receiver(post_save, sender=Friendship)
def friendship_notification(sender, instance, created, update_fields=None, **kwargs):
    """친구 요청·수락 시 알림 자동 생성 (F-NTF-01, 와이어프레임 14).

    - 요청 생성(pending) → 받는 사람(addressee)에게 friend_request
    - 상태 accepted 전환 → 요청자(requester)에게 friend_accept
      (수락 뷰가 save(update_fields=["status", ...]) 하므로 그때만 발화 → 중복 방지)
    """
    if created and instance.status == Friendship.Status.PENDING:
        Notification.objects.create(
            recipient=instance.addressee,
            actor=instance.requester,
            type=Notification.Type.FRIEND_REQUEST,
            friendship=instance,
        )
    elif (
        not created
        and instance.status == Friendship.Status.ACCEPTED
        and update_fields
        and "status" in update_fields
    ):
        Notification.objects.create(
            recipient=instance.requester,
            actor=instance.addressee,
            type=Notification.Type.FRIEND_ACCEPT,
            friendship=instance,
        )
