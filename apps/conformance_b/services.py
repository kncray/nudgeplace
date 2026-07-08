"""앱 B의 공개 서비스 인터페이스 — 유일한 공개 진입점(P-SI-1)."""


def ping() -> str:
    return "conformance_b"
