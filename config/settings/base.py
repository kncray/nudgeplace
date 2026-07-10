"""공통 설정 — 환경별 설정(local·ci)이 이를 상속한다.

prod/sandbox 설정은 만들지 않는다(YAGNI — Spec 000 R6). 저장소는 PostgreSQL 16
(Spec 001 R1) — 멱등 기록·감사 사실의 첫 영속 요구. 접속은 POSTGRES_* 환경변수
계약으로 고정하고(기본값 = docker-compose 로컬 값, 비밀 아님), CI는 잡 env로 주입한다.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 스캐폴딩 단계 키 — 배포 환경 설정이 생기는 시점에 환경 주입으로 교체한다.
SECRET_KEY = 'insecure-scaffold-only-key'

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    'shared_kernel',
    'apps.conformance_a',
    'apps.conformance_b',
]

MIDDLEWARE: list[str] = []

ROOT_URLCONF = 'config.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'NAME': os.environ.get('POSTGRES_DB', 'nudgeplace'),
        'USER': os.environ.get('POSTGRES_USER', 'nudgeplace'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'nudgeplace'),
    }
}

TIME_ZONE = 'Asia/Seoul'
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
