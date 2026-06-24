"""'같이 볼 영화' / 범용 추천 챗봇 서비스 (5.4, 김호준).

LLM은 카탈로그 밖 영화를 지어낼 수 있으므로(환각), 서버가 추천 후보를 좌표로 추려 프롬프트에
넣고 '이 목록 안에서만 골라라'로 grounding 한다. 유저 응답은 SSE 스트림(gms.stream).
- 같이 볼 영화: 둘 다 안 본 영화 중 '두 사람 취향 집합 모두에 가까운'(겹침 영역) 후보.
- 범용: 내가 안 본 영화 중 내 취향 집합에 가까운 후보.
무게중심(점 1개)은 안 씀 — 집합 최근접 기반(A-08·A-15 철학과 동일).
"""
import json

import numpy as np

from movies.models import Movie

from .areas import _all_movies, _watched
from .taste_map import genre_summary

COWATCH_POOL = 20
GENERAL_POOL = 20
MIN_VOTE = 6.5
MAX_HISTORY = 12   # 최근 N턴만 LLM에 전달(토큰 절약)


def _candidates_from_ids(ordered_ids):
    """점수순 영화 id → [{id,title,year,vote,genres}] (순서 보존)."""
    info = {m["id"]: m for m in Movie.objects.filter(id__in=ordered_ids)
            .values("id", "title", "release_year", "vote_average")}
    genres = {i: [] for i in ordered_ids}
    for mid, g in Movie.objects.filter(id__in=ordered_ids).values_list("id", "genres__name"):
        if g:
            genres[mid].append(g)
    out = []
    for i in ordered_ids:
        m = info.get(i)
        if m:
            out.append({"id": i, "title": m["title"], "year": m["release_year"],
                        "vote": m["vote_average"], "genres": genres[i]})
    return out


def _nearest_to_set(pts, set_pts):
    """각 후보점 → set_pts 중 최근접 거리(M,)."""
    return np.linalg.norm(pts[:, None, :] - set_pts[None, :, :], axis=2).min(axis=1)


def cowatch_candidates(me, friend, n=COWATCH_POOL):
    """둘 다 안 본 영화 중 '두 취향 집합 모두에 가까운'(겹침) 순 Top n."""
    me_ids, me_pts = _watched(me)
    fr_ids, fr_pts = _watched(friend)
    if len(me_pts) == 0 or len(fr_pts) == 0:
        return []
    ids, _titles, coords, votes = _all_movies()
    seen = me_ids | fr_ids
    mask = np.array([(ids[i] not in seen) and votes[i] >= MIN_VOTE for i in range(len(ids))])
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    pts = coords[idx]
    score = np.maximum(_nearest_to_set(pts, me_pts), _nearest_to_set(pts, fr_pts))  # 둘 다 가까운 곳
    top = [ids[idx[i]] for i in np.argsort(score)[:n]]
    return _candidates_from_ids(top)


def cowatch_map_candidates(me, friend):
    """'같이 볼 영화' 후보를 좌표·포스터와 함께 — [{id,title,poster_path,x,y}] (5.4).
    챗봇이 추천한 제목을 프론트에서 매칭해 '지도에 표시'할 때 쓴다(추천 후보 안에서만 고르므로 신뢰 가능)."""
    ids = [c["id"] for c in cowatch_candidates(me, friend)]
    if not ids:
        return []
    mv = {m["id"]: m for m in Movie.objects.filter(id__in=ids)
          .values("id", "title", "poster_path", "map_x", "map_y")}
    out = []
    for i in ids:
        m = mv.get(i)
        if m and m["map_x"] is not None:
            out.append({"id": i, "title": m["title"], "poster_path": m["poster_path"],
                        "x": m["map_x"], "y": m["map_y"]})
    return out


def general_candidates(user, n=GENERAL_POOL):
    """내가 안 본 영화 중 내 취향 집합에 가까운 순 Top n."""
    me_ids, me_pts = _watched(user)
    if len(me_pts) == 0:
        return []
    ids, _titles, coords, votes = _all_movies()
    mask = np.array([(ids[i] not in me_ids) and votes[i] >= MIN_VOTE for i in range(len(ids))])
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    pts = coords[idx]
    d = _nearest_to_set(pts, me_pts)
    top = [ids[idx[i]] for i in np.argsort(d)[:n]]
    return _candidates_from_ids(top)


def _fmt(cands):
    return "\n".join(
        f"{i + 1}. {c['title']} ({c['year'] or '?'}) · {'/'.join(c['genres']) or '장르?'} · 평점 {c['vote']}"
        for i, c in enumerate(cands)
    )


def _sanitize(history):
    """프론트 대화 이력 → 허용 role·content만, 최근 MAX_HISTORY턴."""
    out = []
    for m in history or []:
        role, content = m.get("role"), (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out[-MAX_HISTORY:]


def cowatch_messages(me, friend, history):
    cands = cowatch_candidates(me, friend)
    if not cands:
        sys = ("너는 무비무비 AI야. 한국어 반말로 친근하게 답해. 두 사람 중 한 명이 아직 평가한 "
               "영화가 적어 같이 볼 후보를 만들지 못했어. 영화를 더 평가하면 추천해줄 수 있다고 안내해줘.")
    else:
        my_main = " · ".join(genre_summary(me)["main"]) or "정보 부족"
        fr_main = " · ".join(genre_summary(friend)["main"]) or "정보 부족"
        sys = (
            f"너는 두 친구가 '같이 볼 영화'를 고르도록 돕는 무비무비 AI야. 한국어 반말로 친근하게 답해.\n"
            f"- 내 취향 장르: {my_main}\n- 친구({friend.nickname})의 취향 장르: {fr_main}\n"
            f"아래 '후보' 목록 안에서만 골라 추천해(목록에 없는 영화는 절대 언급하지 마).\n"
            f"한 번에 한 편만 골라 제목과 2~3문장 이유를 써. 두 사람 취향이 만나는 지점을 짚어줘.\n"
            f"'더 가볍게' 같은 후속 요청엔 후보 안에서 다시 골라줘.\n\n[후보]\n{_fmt(cands)}"
        )
    return [{"role": "developer", "content": sys}] + _sanitize(history)


def general_messages(user, history):
    cands = general_candidates(user)
    if not cands:
        sys = ("너는 무비무비 영화 추천 AI야. 한국어 반말로 친근하게 답해. 아직 평가한 영화가 적어 "
               "추천 후보를 만들지 못했어. 영화를 더 평가하면 추천해줄 수 있다고 안내해줘.")
    else:
        my_main = " · ".join(genre_summary(user)["main"]) or "정보 부족"
        sys = (
            f"너는 무비무비의 영화 추천 AI야. 한국어 반말로 친근하게 답해.\n"
            f"- 사용자의 취향 장르: {my_main}\n"
            f"아래 '후보' 목록 안에서만 골라 추천해(목록에 없는 영화는 절대 언급하지 마).\n"
            f"한 번에 한 편만 골라 제목과 2~3문장 이유를 써. 후속 요청엔 후보 안에서 다시 골라줘.\n\n[후보]\n{_fmt(cands)}"
        )
    return [{"role": "developer", "content": sys}] + _sanitize(history)


def sse(messages):
    """LLM 입력 messages → SSE 제너레이터. 델타를 'data: {delta}', 끝에 'data: [DONE]'."""
    from . import gms
    try:
        for delta in gms.stream(messages):
            yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
    except Exception as e:   # noqa: BLE001 — 스트림 중 오류도 클라이언트에 전달
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
