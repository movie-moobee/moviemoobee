"""
1_fetch_movies.py

TMDB에서 인기 영화 N편을 가져와 movies.json으로 저장.
각 영화에 대해 장르, 키워드, 감독, overview, 개봉년도 등을 수집.

사용법:
    python 1_fetch_movies.py

필요:
    - .env 파일에 TMDB_API_KEY 설정
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

# ---------- 환경 설정 ----------
load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
LANGUAGE = os.getenv("TMDB_LANGUAGE", "ko-KR")
MOVIE_COUNT = int(os.getenv("MOVIE_COUNT", "300"))

if not API_KEY:
    raise SystemExit("❌ TMDB_API_KEY가 .env에 설정되지 않았습니다.")

BASE_URL = "https://api.themoviedb.org/3"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "movies.json"


# ---------- API 호출 헬퍼 ----------
def get(path: str, params: dict | None = None) -> dict:
    """TMDB API GET 요청 (재시도 포함)."""
    params = {**(params or {}), "api_key": API_KEY, "language": LANGUAGE}

    for attempt in range(3):
        try:
            res = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
            if res.status_code == 429:  # rate limit
                wait = int(res.headers.get("Retry-After", 1))
                time.sleep(wait)
                continue
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    return {}


def fetch_popular_movie_ids(target_count: int) -> list[int]:
    """인기 영화 ID 리스트 수집 (페이지당 20편)."""
    ids: list[int] = []
    page = 1
    pbar = tqdm(total=target_count, desc="영화 ID 수집")
    while len(ids) < target_count:
        data = get("/movie/popular", {"page": page})
        results = data.get("results", [])
        if not results:
            break
        for m in results:
            if m["id"] not in ids:
                ids.append(m["id"])
                pbar.update(1)
            if len(ids) >= target_count:
                break
        page += 1
        if page > 500:  # TMDB 페이지 한계
            break
    pbar.close()
    return ids[:target_count]


def fetch_movie_detail(movie_id: int) -> dict | None:
    """영화 상세 정보 + credits + keywords 한 번에."""
    try:
        data = get(
            f"/movie/{movie_id}",
            {"append_to_response": "credits,keywords"},
        )
    except requests.RequestException:
        return None

    if not data.get("id"):
        return None

    # 감독 추출
    crew = data.get("credits", {}).get("crew", [])
    directors = [c["name"] for c in crew if c.get("job") == "Director"]

    # 키워드 추출
    keywords = [k["name"] for k in data.get("keywords", {}).get("keywords", [])]

    # 장르 추출
    genres = [g["name"] for g in data.get("genres", [])]

    return {
        "id": data["id"],
        "title": data.get("title", ""),
        "original_title": data.get("original_title", ""),
        "overview": data.get("overview", ""),
        "release_date": data.get("release_date", ""),
        "release_year": (data.get("release_date") or "0000")[:4],
        "runtime": data.get("runtime", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "original_language": data.get("original_language", ""),
        "poster_path": data.get("poster_path"),
        "genres": genres,
        "directors": directors,
        "keywords": keywords,
    }


# ---------- 메인 ----------
def main():
    print(f"🎬 TMDB에서 영화 {MOVIE_COUNT}편 수집 시작 (언어: {LANGUAGE})\n")

    ids = fetch_popular_movie_ids(MOVIE_COUNT)
    print(f"\n✅ 영화 ID {len(ids)}개 수집 완료\n")

    movies = []
    for movie_id in tqdm(ids, desc="상세 정보 수집"):
        detail = fetch_movie_detail(movie_id)
        if detail and detail["genres"]:  # 장르 없는 건 제외
            movies.append(detail)
        time.sleep(0.05)  # rate limit 보호

    OUTPUT_PATH.write_text(
        json.dumps(movies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ {len(movies)}편 저장 완료 → {OUTPUT_PATH}")
    print("\n📊 수집 요약:")
    print(f"  - 평균 장르 수: {sum(len(m['genres']) for m in movies) / len(movies):.1f}")
    print(f"  - 평균 키워드 수: {sum(len(m['keywords']) for m in movies) / len(movies):.1f}")
    print(f"  - 평균 감독 수: {sum(len(m['directors']) for m in movies) / len(movies):.1f}")
    print(f"  - 키워드 없는 영화: {sum(1 for m in movies if not m['keywords'])}편")


if __name__ == "__main__":
    main()
