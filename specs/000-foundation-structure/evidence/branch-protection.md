# Evidence: GitHub 플랫폼 설정 (T014, C-2·C-3·C-5)

**기록일**: 2026-07-08 | **저장소**: `kncray/nudgeplace` (private)

## 완료된 것

### 원격 저장소 생성·push

```
gh repo create nudgeplace --private --source=. --remote=origin --push
→ https://github.com/kncray/nudgeplace.git, main push 완료
```

### CI 실제 실행 증거 (C-1 — ci.yml이 죽은 파일이 아님)

push 트리거로 workflow run **28945248361** 실행 → **success**. 잡/스텝:

```json
{"conclusion":"success","name":"quality-gate","steps":[
  {"conclusion":"success","name":"Run actions/checkout@v4"},
  {"conclusion":"success","name":"Install uv (Python 3.12)"},
  {"conclusion":"success","name":"Sync dependencies"},
  {"conclusion":"success","name":"Boundary check (tach)"},
  {"conclusion":"success","name":"Tests"}]}
```

계약 고정 잡 id `quality-gate`가 tach check → pytest 순서로 GitHub 인프라에서
실제 통과 — required check로 지정할 status context가 존재함을 확인.

## 보류된 것 (플랜 제약 — 2026-07-08 기준)

**required status check 지정(C-2)과 code-owner review 필수화(C-5 플랫폼 절반)**가
GitHub Free 개인 계정의 private 저장소 제약으로 차단됨. 두 메커니즘 모두 시도·기록:

```
PUT /repos/kncray/nudgeplace/branches/main/protection
→ 403 "Upgrade to GitHub Pro or make this repository public to enable this feature."

POST /repos/kncray/nudgeplace/rulesets (required_status_checks, enforcement: active)
→ 403 "Upgrade to GitHub Pro or make this repository public to enable this feature."
```

시도한 보호 페이로드(해제 시 그대로 재사용):

```json
{
  "required_status_checks": {"strict": true, "contexts": ["quality-gate"]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"require_code_owner_reviews": true, "required_approving_review_count": 1},
  "restrictions": null
}
```

## 해제 조건과 재개 절차

다음 중 하나로 해제된다 — **(a)** GitHub Pro 업그레이드, **(b)** 저장소 public 전환.
해제 즉시 위 PUT 호출 재실행 → 응답 JSON을 이 문서에 추가 → T014 완료 표시.

**영향**: 그 전까지 main 직접 push가 기술적으로 가능하므로 FR-003의 "생략 불가능"
보증은 플랫폼이 아니라 운영 규율(PR 경유)에 의존한다. repo-local 층(CI 계약 테스트·
CODEOWNERS 파일)과 CI 실행 자체는 정상 가동 중이다.
