"""시청기록 변경 → 사용자 좌표 재계산 (F-MAP-00).
movies.WatchRecord 를 구독하고, 핸들러 로직은 taste(김호준 담당)에 둔다.
"""
from django.db.models.signals import post_delete, post_save     # Django 모델 객체가 데이터베이스에 완전히 저장(생성/수정)된 직후, 그리고 삭제된 직후에 발송되는 내장 신호(Signal)
from django.dispatch import receiver                            # 특정 신호가 발생했을 때 이를 감지하여 연결된 함수(핸들러)를 실행시키는 데코레이터

from movies.models import WatchRecord               # 신호의 발신자(Sender)가 될 시청 기록 모델

from .services.coords import recompute_user_coord   # 앱 내부(coords.py)에 정의된 유저 좌표 재계산 함수

# WatchRecord (시청 기록에 변경 및 삭제가 발생할 때 실행되는 로직)
@receiver(post_save, sender=WatchRecord)
@receiver(post_delete, sender=WatchRecord)
def update_user_coord(sender, instance, **kwargs):
    recompute_user_coord(instance.user)
