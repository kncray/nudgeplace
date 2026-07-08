"""앱 B의 내부 모듈 — 경계 테스트의 위반-샘플 표적(공개 표면 아님).

다른 앱이 이 모듈을 import하면 경계 검사가 차단해야 한다(AC-1).
Django 구성 파일(apps.py)을 내부 모듈 샘플로 쓰지 않기 위해 존재한다.
"""


def internal_detail() -> str:
    return "conformance_b internal"
