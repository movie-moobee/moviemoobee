"""
3_visualize.py

PoC-B 결과를 한 지도에 종합 시각화:
    - 회색: 미시청 영화 (배경)
    - ⭐ 빨강 별: 사용자가 본 영화 (별점 클수록 큼)
    - 📍 자홍 X: 사용자 좌표 (별점 가중 평균)
    - 🟦 파랑 원: 코사인 추천 Top 10
    - 🟧 주황 원: 밀도 기반 미탐색에서 추천
    - 점선 영역: 미탐색 영역 (밀도 기반)

사용법:
    python 3_visualize.py
"""

import json
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).parent
POC_A_OUTPUT = BASE_DIR.parent / "poc-a" / "output" / "movies_2d.json"
USER_PATH = BASE_DIR / "output" / "virtual_user.json"
REC_PATH = BASE_DIR / "output" / "recommendations.json"
OUTPUT_DIR = BASE_DIR / "output"


def setup_korean_font():
    candidates = [
        "AppleGothic", "Apple SD Gothic Neo",
        "Malgun Gothic",
        "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            print(f"✅ 한글 폰트: {font}")
            return
    print("⚠️  한글 폰트 못 찾음")


def visualize_three_zone_methods(
    all_movies, user, rec, output_path,
):
    """미탐색 영역 3가지 방법을 나란히 비교."""
    setup_korean_font()
    
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    method_names = ["distance", "density", "variance"]
    method_titles = ["거리 기반", "밀도 기반", "분산 기반"]

    watched = user["watched"]
    watched_ids = {w["movie_id"] for w in watched}
    user_coord = rec["user_coordinate"]["weighted"]

    for ax, method, title in zip(axes, method_names, method_titles):
        zone = rec["unexplored_zones"][method]
        unexplored_ids = {m["id"] for m in zone["movies"]}

        # 1. 배경: 전체 영화 (회색)
        for m in all_movies:
            if m["id"] in unexplored_ids:
                continue
            if m["id"] in watched_ids:
                continue
            ax.scatter(m["x"], m["y"], c="lightgray", s=20, alpha=0.5)

        # 2. 미탐색 영역 (주황색 강조)
        for m in zone["movies"]:
            ax.scatter(m["x"], m["y"], c="orange", s=30, alpha=0.4, edgecolors="darkorange", linewidths=0.5)

        # 3. 사용자가 본 영화 (빨강 별, 별점 크기 반영)
        for w in watched:
            size = 60 + w["rating"] * 30  # 1점=90, 5점=210
            color = "red" if w["rating"] >= 3.5 else "darkred" if w["rating"] >= 2.5 else "gray"
            ax.scatter(w["x"], w["y"], c=color, s=size, marker="*", 
                       alpha=0.8, edgecolors="white", linewidths=1, zorder=5)

        # 4. 사용자 좌표 (자홍 X)
        ax.scatter(user_coord[0], user_coord[1], c="magenta", s=300, marker="X",
                   edgecolors="black", linewidths=2, zorder=10, label="사용자 좌표")

        ax.set_title(f"{title}: 미탐색 {zone['count']}편", fontsize=14, pad=10)
        ax.set_xlabel("UMAP-1")
        ax.set_ylabel("UMAP-2")
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        f"미탐색 영역 정의 3가지 비교 (취향: {user['profile']['primary_genre']})",
        fontsize=16, y=1.02
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    print(f"✅ 비교 시각화: {output_path}")
    plt.close()


def visualize_final_recommendation(all_movies, user, rec, output_path):
    """최종 추천 결과 — 가장 직관적인 한 장."""
    setup_korean_font()

    fig, ax = plt.subplots(figsize=(14, 10))

    watched = user["watched"]
    watched_ids = {w["movie_id"] for w in watched}
    user_coord = rec["user_coordinate"]["weighted"]

    # 밀도 기반 미탐색 영역 사용 (가장 합리적)
    zone = rec["unexplored_zones"]["density"]
    unexplored_ids = {m["id"] for m in zone["movies"]}

    cosine_rec_ids = {r["movie_id"] for r in rec["recommendations"]["cosine"][:10]}
    unexplored_rec_ids = {r["movie_id"] for r in rec["recommendations"]["from_unexplored"]}

    # 1. 배경 영화 (회색)
    for m in all_movies:
        if m["id"] in watched_ids or m["id"] in cosine_rec_ids or m["id"] in unexplored_rec_ids:
            continue
        color = "moccasin" if m["id"] in unexplored_ids else "lightgray"
        ax.scatter(m["x"], m["y"], c=color, s=25, alpha=0.6)

    # 2. 사용자가 본 영화 (빨강 별)
    for w in watched:
        size = 80 + w["rating"] * 35
        color = "red" if w["rating"] >= 3.5 else "gray"
        ax.scatter(w["x"], w["y"], c=color, s=size, marker="*",
                   alpha=0.85, edgecolors="white", linewidths=1.5, zorder=5)

    # 3. 코사인 추천 Top 10 (파란 원)
    for r in rec["recommendations"]["cosine"][:10]:
        ax.scatter(r["x"], r["y"], c="dodgerblue", s=200, marker="o",
                   edgecolors="navy", linewidths=2, zorder=6, alpha=0.9)

    # 4. 미탐색 영역 추천 (주황 원)
    for r in rec["recommendations"]["from_unexplored"]:
        ax.scatter(r["x"], r["y"], c="orange", s=250, marker="o",
                   edgecolors="darkorange", linewidths=2.5, zorder=7, alpha=0.95)

    # 5. 사용자 좌표 (자홍 X)
    ax.scatter(user_coord[0], user_coord[1], c="magenta", s=500, marker="X",
               edgecolors="black", linewidths=2.5, zorder=10)

    # 범례 (수동)
    legend_items = [
        plt.scatter([], [], c="red", s=150, marker="*", edgecolors="white", linewidths=1.5, label="시청 영화 (별점 높음)"),
        plt.scatter([], [], c="gray", s=80, marker="*", edgecolors="white", linewidths=1.5, label="시청 영화 (별점 낮음)"),
        plt.scatter([], [], c="magenta", s=200, marker="X", edgecolors="black", linewidths=2, label="사용자 좌표"),
        plt.scatter([], [], c="dodgerblue", s=150, marker="o", edgecolors="navy", linewidths=2, label="안전 추천 (코사인 Top 10)"),
        plt.scatter([], [], c="orange", s=180, marker="o", edgecolors="darkorange", linewidths=2.5, label="도전 추천 (미탐색)"),
        plt.scatter([], [], c="moccasin", s=60, label="미탐색 영역"),
        plt.scatter([], [], c="lightgray", s=60, label="기타 영화"),
    ]
    ax.legend(handles=legend_items, loc="upper right", fontsize=10, framealpha=0.95)

    primary = user["profile"]["primary_genre"]
    secondary = user["profile"].get("secondary_genre", "")
    ax.set_title(
        f"취향 지도 + 추천 결과 (취향: {primary} + {secondary})",
        fontsize=15, pad=15
    )
    ax.set_xlabel("UMAP-1")
    ax.set_ylabel("UMAP-2")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    print(f"✅ 최종 시각화: {output_path}")
    plt.close()


def main():
    for path in [POC_A_OUTPUT, USER_PATH, REC_PATH]:
        if not path.exists():
            raise SystemExit(f"❌ {path}가 없습니다.")

    all_movies = json.loads(POC_A_OUTPUT.read_text(encoding="utf-8"))
    user = json.loads(USER_PATH.read_text(encoding="utf-8"))
    rec = json.loads(REC_PATH.read_text(encoding="utf-8"))

    visualize_three_zone_methods(
        all_movies, user, rec,
        OUTPUT_DIR / "unexplored_comparison.png",
    )
    visualize_final_recommendation(
        all_movies, user, rec,
        OUTPUT_DIR / "final_recommendation.png",
    )

    print("\n🎉 PoC-B 시각화 완료!")
    print("\n검토 항목:")
    print("  1. final_recommendation.png — 추천이 시각적으로 합리적인가?")
    print("     ✅ 빨강 별(시청 영화) 근처에 파랑 원(안전 추천)이 모여있어야 함")
    print("     ✅ 주황 원(도전 추천)은 별과 적당히 떨어진 곳에 있어야 함")
    print("  2. unexplored_comparison.png — 어느 미탐색 정의가 가장 합리적인가?")
    print("     → 페어와 토론하여 본 프로젝트에서 사용할 방법 결정")


if __name__ == "__main__":
    main()
