"""공유 커널 Django 앱 설정.

커널은 마이그레이션(멱등·감사 테이블)을 갖기 위해 Django 앱으로 승격되나
도메인 계층(apps/)이 아니다 — 이 테이블들은 인프라 기록이다(BR-6, plan
Structure Decision). tach 경계 계약은 변경 없이 유지된다(depends_on=[]).
"""

from django.apps import AppConfig


class SharedKernelConfig(AppConfig):
    name = 'shared_kernel'
    default_auto_field = 'django.db.models.BigAutoField'
