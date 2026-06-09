"""TMDB 인기 영화 수집 → movies/genres/keywords 적재 (By 인간 대동여지도, 0.5 데이터 파이프라인).

PoC-A(1_fetch_movies.py) 로직을 Django DB 적재로 이식.
- 인증: .env 의 TMDB_API_KEY 는 v4 Read Access Token(JWT) → Authorization: Bearer 헤더 사용.
- 멱등성: tmdb_id 기준 update_or_create 라 재실행해도 중복 안 생김.
- 좌표(umap_x/y)는 여기서 안 건드림 → build_coords 가 채움(전역 고정 좌표 불변식).
"""
import time
from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError   # -> 이걸로 python manage.py import_movies 할 수 있다 개신기.

from movies.models import Genre, Keyword, Movie

BASE_URL = "https://api.themoviedb.org/3"
LANGUAGE = "ko-KR"


def _parse_date(s):
    """'YYYY-MM-DD' → date, 빈 값/형식오류 → None."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


class Command(BaseCommand):
    help = "TMDB에서 인기 영화 수집 → movies 적재 (김호준)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2000)
        
    # python manage.py import_movies.py 의 진입점
    def handle(self, *args, **opts):
        api_key = settings.TMDB_API_KEY
        if not api_key:
            raise CommandError("TMDB_API_KEY가 .env에 없습니다.")
        self.session = requests.Session() # API 호출마다 새로운 Session 안맺음. 연결 유지(Session), 속도 향상될 것 - 김호준
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})     # TMDB v4 방식으로 하기 위해 (TMDB API_KEY 中 READ_ONLY 훨씬 더 긴 KEY 사용하는거임.)

        target = opts["count"]
        self.stdout.write(f"[수집] TMDB 인기 영화 {target}편 시작 (언어: {LANGUAGE})")

        ids = self._fetch_popular_ids(target)
        self.stdout.write(f"[수집] 영화 ID {len(ids)}개")

        saved = 0
        for i, movie_id in enumerate(ids, 1):
            detail = self._fetch_detail(movie_id)
            if detail and detail["genres"]:  # 장르 없는 건 제외(PoC와 동일)
                self._save(detail)
                saved += 1
            if i % 50 == 0:
                self.stdout.write(f"  ...{i}/{len(ids)} 처리 (적재 {saved})")
            time.sleep(0.05)  # rate limit 보호 (IP 차단 방지 ㅠㅠㅜ) TMDB docs보면 초당 약 40여건만 허용한대요, 안그러면 429 줄거라함.

        self.stdout.write(self.style.SUCCESS(
            f"[완료] {saved}편 적재 "
            f"(genres={Genre.objects.count()}, keywords={Keyword.objects.count()}, "
            f"movies={Movie.objects.count()})"
        ))

    # ---------- TMDB ----------
    def _get(self, path, params=None):
        for attempt in range(3):    # 3번까지 재시도 함
            res = self.session.get(
                f"{BASE_URL}{path}",
                params={**(params or {}), "language": LANGUAGE},
                timeout=10,
            )
            if res.status_code == 429:
                time.sleep(int(res.headers.get("Retry-After", 1)))
                continue
            res.raise_for_status()
            return res.json()
        return {}

    def _fetch_popular_ids(self, target):
        ids, page = [], 1
        seen = set()
        while len(ids) < target and page <= 500:    # TMDB 최대 허용 페이지가 500페이지래요.
            results = self._get("/movie/popular", {"page": page}).get("results", [])
            if not results:
                break
            for m in results:
                if m["id"] not in seen:
                    seen.add(m["id"])
                    ids.append(m["id"])
                if len(ids) >= target:
                    break
            page += 1
        return ids[:target]

    def _fetch_detail(self, movie_id):
        try:
            data = self._get(
                f"/movie/{movie_id}",
                {"append_to_response": "credits,keywords"},                     #  TMDB에서 이렇게 짜라함.  -> 여러개 정보 받으려고 여러번 api 호출하지 말고 한꺼번에 하래요.
            )
        except requests.RequestException:
            return None
        if not data.get("id"):
            return None
        crew = data.get("credits", {}).get("crew", [])                          # crew = 스태프 목록 추출
        directors = [c["name"] for c in crew if c.get("job") == "Director"]     # 리스트 컴프리헨션 멋지다. 말그대로 dirctors 감독 뽑아내는거고, 공동 감독이면 여러명 리스트 안에 담김
        return {
            "tmdb_id": data["id"],
            "title": data.get("title", ""),
            "original_title": data.get("original_title", ""),
            "overview": data.get("overview", ""),
            "release_date": _parse_date(data.get("release_date")),
            "release_year": int((data.get("release_date") or "0")[:4] or 0) or None,    # 날짜에서 연도만 떼어내기
            "runtime": data.get("runtime") or None,
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "original_language": data.get("original_language", ""),
            "poster_path": data.get("poster_path") or "",
            "director": directors[0] if directors else "",                          # ㅋㅋ 근데 여러명 저장하긴 해도 한명만 반환하자 그래
            "genres": [(g["id"], g["name"]) for g in data.get("genres", [])],       # (id, "장르")
            "keywords": [k["name"] for k in data.get("keywords", {}).get("keywords", [])],  # ex) ["superhero", "based on comic"]
        }

    # ---------- DB ----------

    def _save(self, d):
        # 멱.등.성 (Idempotency) : 재실행해도 문제없어. 같은 영화가 들어오면? 평점이나 줄거리 등 업데이트 된 내역있을수 도 있으니 업데이트함.
        # .update_or_create은 (저장된 영화 객체, 새로 생성되었는지 여부를 나타내는 True/False)가 나옴. 뒤에껀 무시하려고 _를 썼다.
        # 결론적으로 만약 영화가 DB에 없으면, 이 데이터들로 새로 만들고 영화가 이미 있으면, 이 데이터들로 기존 데이터를 덮어씀(업데이트).
        movie, _ = Movie.objects.update_or_create(          
            tmdb_id=d["tmdb_id"],                           
            defaults={                                      
                "title": d["title"],
                "original_title": d["original_title"],
                "overview": d["overview"],
                "release_date": d["release_date"],
                "release_year": d["release_year"],
                "runtime": d["runtime"],
                "vote_average": d["vote_average"],
                "vote_count": d["vote_count"],
                "original_language": d["original_language"],
                "poster_path": d["poster_path"],
                "director": d["director"],
            },
        )
        
        # 장르, 키워드도 (객체, 생성여부) 반환해서 0번 인덱스만 사용
        genres = [
            Genre.objects.get_or_create(name=name, defaults={"tmdb_genre_id": gid})[0]
            for gid, name in d["genres"]
        ]
        

        keywords = [
            Keyword.objects.get_or_create(name=name)[0] for name in d["keywords"]
        ]
        
        # movie 데이터와 장르 리스트를 다대다(Many-to-Many) 관계로 연결
        # set -> 우리의 중간 테이블인 movie_genres에 항상 최신 값을 유지시킴. 아주 방어적이죠?
        movie.genres.set(genres)
        movie.keywords.set(keywords)
