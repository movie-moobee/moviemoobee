"""
1_create_virtual_user.py

PoC-A 결과(movies_2d.json)에서 가상 사용자를 생성.
취향이 명확한 사용자: 특정 장르 위주로 20편을 선택하고 별점을 부여.

생성 결과:
    output/virtual_user.json — 사용자가 본 영화 + 별점

사용법:
    python 1_create_virtual_user.py
    python 1_create_virtual_user.py --primary-genre "SF" --secondary-genre "액션"
"""

import argparse
import json
import random
from pathlib import Path

# PoC-A 결과 경로 (실제 환경에서는 상대 경로 조정 필요)
BASE_DIR = Path(__file__).parent
POC_A_OUTPUT = BASE_DIR.parent / "poc-a" / "output" / "movies_2d.json"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_movies() -> list[dict]:
    if not POC_A_OUTPUT.exists():
        raise SystemExit(
            f"❌ {POC_A_OUTPUT}가 없습니다.\n"
            "   먼저 poc-a/2_embed_and_map.py를 실행하세요."
        )
    return json.loads(POC_A_OUTPUT.read_text(encoding="utf-8"))


def create_clear_taste_user(
    movies: list[dict],
    primary_genre: str,
    secondary_genre: str | None = None,
    n_movies: int = 20,
    seed: int = 42,
) -> dict:
    """취향 명확한 사용자 생성.
    
    전략:
    - 70% 영화는 primary_genre
    - 20% 영화는 secondary_genre (있을 경우)
    - 10% 영화는 무작위 (현실성: 사람은 가끔 다른 장르도 봄)
    - 별점은 primary에 높게, 무작위 선택엔 낮게 부여
    """
    random.seed(seed)

    # 장르별로 영화 인덱스 분류
    primary_pool = [i for i, m in enumerate(movies) if primary_genre in m["genres"]]
    secondary_pool = (
        [i for i, m in enumerate(movies) if secondary_genre in m["genres"] and primary_genre not in m["genres"]]
        if secondary_genre else []
    )
    random_pool = [
        i for i, m in enumerate(movies)
        if primary_genre not in m["genres"]
        and (not secondary_genre or secondary_genre not in m["genres"])
    ]

    if len(primary_pool) < 5:
        raise SystemExit(f"❌ '{primary_genre}' 영화가 너무 적습니다 ({len(primary_pool)}편).")

    # 영화 수 배분
    n_primary = int(n_movies * 0.7)
    n_secondary = int(n_movies * 0.2) if secondary_genre else 0
    n_random = n_movies - n_primary - n_secondary

    selected_primary = random.sample(primary_pool, min(n_primary, len(primary_pool)))
    selected_secondary = random.sample(secondary_pool, min(n_secondary, len(secondary_pool))) if secondary_pool else []
    selected_random = random.sample(random_pool, min(n_random, len(random_pool)))

    watched = []

    # primary: 별점 3.5 ~ 5.0 (높은 별점)
    for idx in selected_primary:
        watched.append({
            "movie_id": movies[idx]["id"],
            "title": movies[idx]["title"],
            "genres": movies[idx]["genres"],
            "rating": round(random.uniform(3.5, 5.0) * 2) / 2,  # 0.5 단위
            "x": movies[idx]["x"],
            "y": movies[idx]["y"],
            "source": "primary",
        })

    # secondary: 별점 3.0 ~ 4.5 (중간~높음)
    for idx in selected_secondary:
        watched.append({
            "movie_id": movies[idx]["id"],
            "title": movies[idx]["title"],
            "genres": movies[idx]["genres"],
            "rating": round(random.uniform(3.0, 4.5) * 2) / 2,
            "x": movies[idx]["x"],
            "y": movies[idx]["y"],
            "source": "secondary",
        })

    # random: 별점 1.5 ~ 3.5 (낮음~중간) - 취향 안 맞아서 별로였다는 신호
    for idx in selected_random:
        watched.append({
            "movie_id": movies[idx]["id"],
            "title": movies[idx]["title"],
            "genres": movies[idx]["genres"],
            "rating": round(random.uniform(1.5, 3.5) * 2) / 2,
            "x": movies[idx]["x"],
            "y": movies[idx]["y"],
            "source": "random",
        })

    return {
        "profile": {
            "type": "clear_taste",
            "primary_genre": primary_genre,
            "secondary_genre": secondary_genre,
            "total_watched": len(watched),
        },
        "watched": watched,
    }


def print_user_summary(user: dict):
    """사용자 프로필 요약 출력."""
    profile = user["profile"]
    watched = user["watched"]

    print(f"\n👤 가상 사용자 생성 완료")
    print(f"   타입: {profile['type']}")
    print(f"   주 취향: {profile['primary_genre']}")
    if profile.get("secondary_genre"):
        print(f"   부 취향: {profile['secondary_genre']}")
    print(f"   시청 영화: {profile['total_watched']}편")

    print(f"\n📊 별점 분포:")
    print(f"   평균: {sum(w['rating'] for w in watched) / len(watched):.2f}")
    print(f"   5점: {sum(1 for w in watched if w['rating'] == 5)}편")
    print(f"   4점 이상: {sum(1 for w in watched if w['rating'] >= 4)}편")
    print(f"   3점 미만: {sum(1 for w in watched if w['rating'] < 3)}편")

    print(f"\n🎬 시청 영화 샘플 (별점 높은 순 Top 5):")
    top5 = sorted(watched, key=lambda w: -w["rating"])[:5]
    for w in top5:
        genres = ", ".join(w["genres"][:3])
        print(f"   ⭐ {w['rating']} | {w['title']} [{genres}]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-genre", default="SF", help="주 장르")
    parser.add_argument("--secondary-genre", default="액션", help="부 장르 (선택)")
    parser.add_argument("--n-movies", type=int, default=20, help="시청 영화 수")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")
    args = parser.parse_args()

    movies = load_movies()
    print(f"📂 영화 {len(movies)}편 로드")

    # 사용 가능한 장르 확인
    all_genres = set()
    for m in movies:
        all_genres.update(m["genres"])
    print(f"📊 사용 가능한 장르: {sorted(all_genres)}")

    if args.primary_genre not in all_genres:
        raise SystemExit(f"❌ '{args.primary_genre}'가 데이터에 없습니다.")

    user = create_clear_taste_user(
        movies,
        primary_genre=args.primary_genre,
        secondary_genre=args.secondary_genre,
        n_movies=args.n_movies,
        seed=args.seed,
    )

    output_path = OUTPUT_DIR / "virtual_user.json"
    output_path.write_text(
        json.dumps(user, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print_user_summary(user)
    print(f"\n✅ 저장: {output_path}")
    print(f"\n다음 단계: python 2_recommend.py")


if __name__ == "__main__":
    main()
