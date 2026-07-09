"""문서 소유 규칙 테스트(US2, SC-004, BR-5).

핵심 결정 ADR 3건이 근거·대안·트레이드오프와 함께 존재하고, state-model·glossary는
**정식 경로·소유 규칙만 ADR에 기록**될 뿐 파일로 선제 생성되지 않았음을 단언한다
(최초 생성 주체 = 첫 상태/도메인 용어를 도입하는 기능, 로드맵상 P1).
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ADR_DIR = REPO_ROOT / 'docs' / 'adr'
ADRS = {
    '0001': ADR_DIR / '0001-modular-monolith.md',
    '0002': ADR_DIR / '0002-boundary-enforcement-tach.md',
    '0003': ADR_DIR / '0003-shared-kernel-unidirectional.md',
}
REQUIRED_SECTIONS = ('## 맥락', '## 결정', '## 검토한 대안', '## 트레이드오프')
FORBIDDEN_PREEMPTIVE_DOCS = (
    REPO_ROOT / 'docs' / 'domain' / 'state-model.md',
    REPO_ROOT / 'docs' / 'domain' / 'glossary.md',
)


@pytest.mark.parametrize('number', sorted(ADRS))
def test_adr_exists_with_required_sections(number):
    """US2 #1: 결정 ADR가 근거(맥락·결정)·대안·트레이드오프 섹션과 함께 존재."""
    path = ADRS[number]
    assert path.exists(), f'ADR {number} 부재: {path.relative_to(REPO_ROOT)}'
    text = path.read_text()
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    assert not missing, f'ADR {number}에 필수 섹션 누락: {missing}'


def test_adr_0002_records_docs_ownership_rule():
    """FR-006: ADR 0002에 state-model·glossary 정식 경로와 소유 규칙 기록."""
    text = ADRS['0002'].read_text()
    assert 'docs/domain/state-model.md' in text
    assert 'docs/domain/glossary.md' in text
    assert '최초 생성' in text, '소유 규칙(최초 생성 주체) 미기록'


@pytest.mark.parametrize('path', FORBIDDEN_PREEMPTIVE_DOCS, ids=lambda p: p.name)
def test_domain_docs_not_preemptively_created(path):
    """US2 #2, BR-5: state-model·glossary 파일은 선제 생성되지 않는다(디렉터리 무관)."""
    assert not path.exists(), f'{path.relative_to(REPO_ROOT)}가 선제 생성됨(BR-5 위반)'
