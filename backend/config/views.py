from django.db import connection
from django.http import JsonResponse


def health(_request):
    """임시 연결 확인용 엔드포인트(기능 아님). 프론트↔백↔DB 한 줄 연결을 증명한다.
    초기 세팅 검증이 끝나면 제거해도 된다."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        db_ok = True
    except Exception:
        db_ok = False
    return JsonResponse({"status": "ok", "db": db_ok})
