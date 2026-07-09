"""공통 설정 — 환경별 설정(local·ci)이 이를 상속한다.

prod/sandbox 설정은 만들지 않는다(YAGNI — Spec 000 R6). 도메인 모델이 없으므로
DATABASES는 비워 둔다(저장소 선택은 Spec 001 이후).
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 스캐폴딩 단계 키 — 배포 환경 설정이 생기는 시점에 환경 주입으로 교체한다.
SECRET_KEY = 'insecure-scaffold-only-key'

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    'apps.conformance_a',
    'apps.conformance_b',
]

MIDDLEWARE: list[str] = []

ROOT_URLCONF = 'config.urls'

DATABASES: dict = {}

TIME_ZONE = 'Asia/Seoul'
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
