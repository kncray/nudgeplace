"""앱 A의 공개 서비스 인터페이스 — 유일한 공개 진입점(P-SI-1).

경계 적합성 픽스처: 도메인 로직·모델 없음(BR-4). 앱 B 호출은 선언된
dependency edge(A→B) 위에서 B의 공개 표면(services)만 경유한다(AC-SI-1).
"""

from apps.conformance_b import services as conformance_b_services


def ping() -> str:
    return "conformance_a"


def call_b() -> str:
    return conformance_b_services.ping()
