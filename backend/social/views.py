from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .models import Friendship
from .serializers import ReceivedRequestSerializer, UserCardSerializer


def _relation_map(me, user_ids):
    """me 와 user_ids 각각의 관계: {other_id: none|friend|pending_sent|pending_received}.
    한 행이 관계 하나(양방향)라 requester/addressee 두 방향을 모두 본다 (쿼리 1번)."""
    rows = Friendship.objects.filter(
        Q(requester=me, addressee_id__in=user_ids)
        | Q(addressee=me, requester_id__in=user_ids)
    )
    rel = {}
    for f in rows:
        other = f.addressee_id if f.requester_id == me.id else f.requester_id
        if f.status == Friendship.Status.ACCEPTED:
            rel[other] = "friend"
        elif f.requester_id == me.id:
            rel[other] = "pending_sent"
        else:
            rel[other] = "pending_received"
    return rel


class UserSearchView(APIView):
    """GET /api/social/users/search/?q= — 닉네임 부분일치 검색 (F-FRD-01).
    본인 제외, 결과마다 본 영화 편수·관계상태 포함. 최대 20명."""

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response([])
        users = list(
            User.objects.filter(nickname__icontains=q)
            .exclude(pk=request.user.pk)
            .annotate(watch_count=Count("watch_records"))
            .order_by("nickname")[:20]
        )
        ctx = {
            "request": request,
            "relation_map": _relation_map(request.user, [u.id for u in users]),
        }
        return Response(UserCardSerializer(users, many=True, context=ctx).data)


class FriendRequestView(APIView):
    """POST /api/social/friendships/ {addressee} — 친구 요청 생성 (F-FRD-02).
    양방향 중복 방지(이미 친구 / 보낸 요청 / 받은 요청)."""

    def post(self, request):
        addressee_id = request.data.get("addressee")
        if not addressee_id:
            return Response({"addressee": "대상이 필요합니다."}, status=400)
        if str(addressee_id) == str(request.user.pk):
            return Response({"addressee": "자기 자신에게 요청할 수 없습니다."}, status=400)
        addressee = get_object_or_404(User, pk=addressee_id)

        existing = Friendship.objects.filter(
            Q(requester=request.user, addressee=addressee)
            | Q(requester=addressee, addressee=request.user)
        ).first()
        if existing:
            if existing.status == Friendship.Status.ACCEPTED:
                return Response({"detail": "이미 친구입니다."}, status=400)
            if existing.requester_id == request.user.id:
                return Response({"detail": "이미 요청을 보냈습니다."}, status=400)
            return Response(
                {"detail": "이미 받은 요청이 있어요. 받은 요청 탭에서 수락하세요."}, status=400
            )

        f = Friendship.objects.create(requester=request.user, addressee=addressee)
        return Response({"id": f.id, "status": f.status}, status=201)


class ReceivedRequestsView(APIView):
    """GET /api/social/friendships/received/ — 내가 받은 대기중 요청 목록 (F-FRD-03)."""

    def get(self, request):
        qs = (
            Friendship.objects.filter(
                addressee=request.user, status=Friendship.Status.PENDING
            )
            .select_related("requester")
            .order_by("-created_at")
        )
        return Response(
            ReceivedRequestSerializer(qs, many=True, context={"request": request}).data
        )


class FriendRequestAcceptView(APIView):
    """POST /api/social/friendships/<pk>/accept/ — 받은 요청 수락 (F-FRD-03).
    수신자(addressee) 본인의 대기중 요청만 수락 → accepted(양방향 친구 성립)."""

    def post(self, request, pk):
        f = get_object_or_404(
            Friendship,
            pk=pk,
            addressee=request.user,
            status=Friendship.Status.PENDING,
        )
        f.status = Friendship.Status.ACCEPTED
        f.responded_at = timezone.now()
        f.save(update_fields=["status", "responded_at"])
        return Response({"id": f.id, "status": f.status})


class FriendRequestRejectView(APIView):
    """DELETE /api/social/friendships/<pk>/ — 받은 요청 거절 (F-FRD-03).
    수신자 본인의 대기중 요청만 폐기(행 삭제). 친구 끊기(accepted)는 5.2에서."""

    def delete(self, request, pk):
        f = get_object_or_404(
            Friendship,
            pk=pk,
            addressee=request.user,
            status=Friendship.Status.PENDING,
        )
        f.delete()
        return Response(status=204)
