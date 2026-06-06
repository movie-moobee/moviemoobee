"""
3_inspect.py

PoC-A 결과를 사람 눈으로 검증하는 도구.
"이 영화 주변에 어떤 영화들이 있는가?"를 확인.

사용법:
    python 3_inspect.py                    # 무작위 5편 샘플
    python 3_inspect.py --title "인터스텔라"  # 특정 영화 검색
    python 3_inspect.py --top 10            # 가까운 영화 10편 보기
"""

import argparse
import json
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).parent
COORDS_PATH = BASE_DIR / "output" / "movies_2d.json"


def load_data() -> list[dict]:
    if not COORDS_PATH.exists():
        raise SystemExit(f"❌ {COORDS_PATH}가 없습니다. 먼저 2_embed_and_map.py를 실행하세요.")
    return json.loads(COORDS_PATH.read_text(encoding="utf-8"))


def find_neighbors(movies: list[dict], target_idx: int, top_n: int = 5) -> list[tuple[int, float]]:
    """target_idx 영화에서 가까운 영화들 (유클리드 거리)."""
    target = np.array([movies[target_idx]["x"], movies[target_idx]["y"]])
    coords = np.array([[m["x"], m["y"]] for m in movies])
    dists = np.linalg.norm(coords - target, axis=1)
    
    nearest = np.argsort(dists)
    return [(int(idx), float(dists[idx])) for idx in nearest[1:top_n + 1]]


def print_movie(m: dict, prefix: str = "", distance: float | None = None):
    genres = ", ".join(m["genres"][:3])
    dist_str = f" [거리 {distance:.3f}]" if distance is not None else ""
    print(f"{prefix}🎬 {m['title']} ({m['release_year']}){dist_str}")
    print(f"{prefix}   장르: {genres}")
    if m["directors"]:
        print(f"{prefix}   감독: {', '.join(m['directors'][:2])}")


def inspect_movie(movies: list[dict], target_idx: int, top_n: int):
    print("\n" + "=" * 60)
    print_movie(movies[target_idx])
    print("\n📍 가까운 영화 Top {}:\n".format(top_n))

    neighbors = find_neighbors(movies, target_idx, top_n)
    for rank, (idx, dist) in enumerate(neighbors, 1):
        print_movie(movies[idx], prefix=f"  {rank}. ", distance=dist)
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", type=str, help="검색할 영화 제목 (부분 일치)")
    parser.add_argument("--top", type=int, default=5, help="보여줄 이웃 수")
    parser.add_argument("--samples", type=int, default=5, help="무작위 샘플 수")
    args = parser.parse_args()

    movies = load_data()
    print(f"📂 영화 {len(movies)}편 로드\n")

    if args.title:
        # 제목으로 검색
        matches = [
            i for i, m in enumerate(movies)
            if args.title.lower() in m["title"].lower()
        ]
        if not matches:
            print(f"❌ '{args.title}'을 포함한 영화를 찾을 수 없습니다.")
            return
        for idx in matches[:3]:  # 최대 3편만
            inspect_movie(movies, idx, args.top)
    else:
        # 무작위 샘플
        np.random.seed(None)
        sample_indices = np.random.choice(len(movies), args.samples, replace=False)
        for idx in sample_indices:
            inspect_movie(movies, int(idx), args.top)

    print("\n" + "=" * 60)
    print("\n🤔 판단 기준:")
    print("  ✅ 좋음: 같은 장르/감독/시리즈가 가까이 있다")
    print("  ⚠️  의심: 장르가 비슷한데 거리가 멀다 / 다른 장르가 옆에 있다")
    print("  ❌ 나쁨: 무작위로 보인다 → 가중치 조정 필요\n")


if __name__ == "__main__":
    main()
