from rest_framework import serializers

from accounts.serializers import build_image_url
from .models import Friendship


class UserCardSerializer(serializers.Serializer):
    """친구 검색 결과 카드 (F-FRD-01). 닉네임·아바타·본 영화 편수 + 나와의 관계상태.

    watch_count 는 뷰에서 annotate(Count("watch_records")) 로 주입.
    relation 은 context["relation_map"][user_id] 에서 조회
    (none / friend / pending_sent / pending_received). 주취향 장르는 추후(F-FRD-05).
    """

    id = serializers.IntegerField()
    nickname = serializers.CharField()
    profile_image_url = serializers.SerializerMethodField()
    watch_count = serializers.IntegerField(read_only=True)
    relation = serializers.SerializerMethodField()

    def get_profile_image_url(self, obj):
        return build_image_url(obj.profile_image, self.context)

    def get_relation(self, obj):
        return self.context.get("relation_map", {}).get(obj.id, "none")


class ReceivedRequestSerializer(serializers.Serializer):
    """받은 친구 요청 카드 (F-FRD-03). friendship id + 요청자(requester) 정보."""

    id = serializers.IntegerField()          # friendship id (수락/거절 대상)
    created_at = serializers.DateTimeField()
    requester = serializers.SerializerMethodField()

    def get_requester(self, obj):
        u = obj.requester
        return {
            "id": u.id,
            "nickname": u.nickname,
            "profile_image_url": build_image_url(u.profile_image, self.context),
            "watch_count": u.watch_records.count(),
        }
