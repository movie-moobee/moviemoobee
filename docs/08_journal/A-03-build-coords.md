# A-03 · `build_coords` — TF-IDF + UMAP 전역 좌표 생성·적재

- 날짜 / 일정ID / 담당: 2026-06-07 · 일정 0.5(후반부) · 개발자 A
- 브랜치 / 커밋: `feat/data-01-build-coords` · (커밋 예정)
- 한 줄 요약: 전체 영화를 장르·키워드·감독 TF-IDF로 임베딩하고 UMAP으로 2D **전역 좌표(umap_x/y)** 를 만들어 DB에 적재. 취향 지도의 좌표 공간을 만드는 단계(0.5 완료).

## 만진 파일 (폴더/파일 — 역할)
- `backend/taste/management/commands/build_coords.py` — TODO 스텁을 실제 구현으로 교체.
  - 실행법: `python manage.py build_coords` (사전: `pip install -r requirements-ml.txt`)
- `backend/taste/artifacts/coords_model.pkl` *(생성물, gitignore)* — 학습된 벡터라이저 + UMAP reducer + 가중치. 신규 영화 `transform` 전용.

## 어떻게 / 왜
- **레퍼런스**: `docs/poc-bundle/poc-a/2_embed_and_map.py`를 DB 적재로 이식.
- **피처**: 장르(×3.0) + 키워드(×1.0) + 감독(×0.5)을 각각 TF-IDF → `hstack`. 가중치는 PoC 튜닝값(장르가 가장 강한 신호).
  - 토큰화: 공백 포함 항목은 언더스코어로 묶어 한 토큰 처리(`Christopher Nolan` → `Christopher_Nolan`), `token_pattern=r"[^ ]+"`.
  - 키워드는 `min_df=2`(1편에만 나온 키워드는 노이즈라 제외).
- **차원 축소**: UMAP(`n_components=2, n_neighbors=15, min_dist=0.1, metric=cosine, random_state=42`). TF-IDF엔 cosine이 적합.
- **불변식(중요)**: 좌표는 **전 사용자 공통·전역 고정값**. 여기서 **한 번만 `fit`** 하고, 학습된 모델을 `.pkl`로 저장한다. 신규 영화는 이 모델로 **`transform`만** 해야 한다 — 다시 `fit`하면 모든 영화 좌표가 바뀌어 친구 취향 비교가 깨짐.
- **적재**: `bulk_update(["umap_x","umap_y"])`로 일괄 갱신(영화당 save 안 함).
- **무거운 import는 함수 안에서**: `umap/scipy/sklearn`은 커맨드 실행 시점에만 import → 웹 부팅(runserver)은 ML 스택 없이도 동작.
- **재실행 주의**: build_coords를 다시 돌리면 전체를 재-fit → 좌표가 바뀐다. "초기 1회 굽기"용. 사용자가 생긴 뒤엔 함부로 재실행 금지(신규 영화는 transform 경로로).

## UMAP 채택 근거 (왜 t-SNE/PCA가 아니라)
PoC 단계에선 "TF-IDF+UMAP이 의미 있는 2D 지도를 만드는가"만 검증했고(합격), 대안 비교는 문서화 안 됐다. 사후적으로 정리하면 UMAP이 우리 요구에 맞는 이유:
- **`transform()` 지원 = 결정타**: 불변식상 좌표는 전역 고정이고 신규 영화는 재-fit 없이 `transform`만 해야 한다(재학습하면 전원 좌표가 바뀌어 친구 취향 비교가 깨짐). **t-SNE는 `transform`이 없어** 새 점 투영 시 전체 재계산 → 우리 설계와 양립 불가(사실상 탈락). PCA는 transform 있지만 **선형**이라 장르 같은 비선형 매니폴드를 2D로 못 풀어 군집이 뭉개짐. UMAP은 비선형 + transform → 둘 다 만족하는 거의 유일한 선택.
- **이웃 보존 + 어느 정도 전역 구조**: "가까운 영화=비슷한 취향"(지도·안전추천 전제)이 성립하고, t-SNE보다 전역 구조를 더 보존해 거리 기반(유클리드) 추천에 유리.
- **결정성**: `random_state=42`로 언제 돌려도 동일(전역 고정 좌표 요건).
- **희소 고차원(896D) 처리·2,000+편 확장성** 양호.
- **트레이드오프(인지)**: 2D 축소는 정보손실이 있다(고차원에선 뭉친 군집이 2D에서 흩어질 수 있음 — A-06 demo_a 사례). 추천 정밀도 일부를 내주고 *눈에 보이는 2D 취향 지도*(제품 정체성)를 얻는 의도된 선택. 정밀도가 더 필요하면 추천만 고차원에서(입장 B, A-06) 분리하는 길이 열려 있음.

## 기능 동작 (흐름)
```
manage.py build_coords
 └ DB 영화 로드(prefetch genres/keywords) — id 순 정렬
     └ 장르/키워드/감독 문서화 → TF-IDF(가중치) → hstack (896차원)
         └ UMAP.fit_transform → (N,2) 좌표
             └ movies.umap_x/umap_y 일괄 적재
             └ 벡터라이저+reducer+weights → artifacts/coords_model.pkl 저장
```

## 검증
- 299/299 영화 좌표 채워짐, 좌표쌍 **299개 모두 고유**(붕괴 없음).
- x 범위 -3.63~12.74 · y 0.27~11.15 (적절히 퍼짐).
- **이웃 sanity**: 기준 영화(스릴러·범죄·드라마)의 최근접 4편이 전부 같은 장르군 → 군집 형성(PoC 합격 기준 충족).
- 모델 pkl 키: vec_genre / vec_keyword / vec_director / reducer / weights.
- `makemigrations --check` 변경 없음(페어의 User FK 컨벤션 변경과도 정합).

## 배운 점 · 주의
- UMAP은 `random_state` 지정 시 단일 스레드로 강제(경고 출력) — 재현성 위해 의도된 동작(전역 고정 좌표라 결정적이어야 함).
- `coords_model.pkl`은 `*.pkl` 규칙으로 gitignore. 페어에겐 좌표가 담긴 **fixture(dumpdata)** 로 공유 예정 — 그러면 페어는 ML 스택/TMDB 키 없이 `loaddata`만으로 동일 좌표 확보.
- 다음 작업: **3.1 사용자 좌표 계산(별점 가중)·캐싱 API** (선행 0.5 완료). 사용자 좌표 = 시청 영화 좌표의 (rating-3.0) 가중 평균.
