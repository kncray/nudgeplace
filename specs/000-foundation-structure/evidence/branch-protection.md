# Evidence: GitHub 플랫폼 설정 (T014, C-2·C-3·C-5)

**기록일**: 2026-07-08 (보류) → **2026-07-09 (해제·적용 완료)** | **저장소**: `kncray/nudgeplace`

> 최종 상태는 [해제 및 적용 (2026-07-09)](#해제-및-적용-2026-07-09) 절 참조.
> 아래 2026-07-08 기록은 보류 사유의 원본 증거로 보존한다.

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

## 해제 조건과 재개 절차 (2026-07-08 기록)

다음 중 하나로 해제된다 — **(a)** GitHub Pro 업그레이드, **(b)** 저장소 public 전환.
해제 즉시 위 PUT 호출 재실행 → 응답 JSON을 이 문서에 추가 → T014 완료 표시.

---

## 해제 및 적용 (2026-07-09)

**(b) public 전환**으로 해제(사람 결정, cray.j):

```
gh repo edit kncray/nudgeplace --visibility public --accept-visibility-change-consequences
→ {"visibility": "PUBLIC"}
```

### C-2 적용: required status check (관리자 포함 강제)

```
PUT /repos/kncray/nudgeplace/branches/main/protection → 200
GET 검증:
{"allow_force_pushes":false,"enforce_admins":true,
 "required_status_checks":{"contexts":["quality-gate"],"strict":true}}
```

- `quality-gate` 성공 status가 없는 커밋은 main에 진입 불가(직접 push 포함).
- `enforce_admins: true` — 저장소 관리자도 우회 불가.
- `strict: true` — 오래된 base 위의 머지 금지. force-push·브랜치 삭제 금지.

### AC-5 실증: 미검증 커밋의 직접 push 거부

`quality-gate` status가 없는 커밋(이 문서를 담은 커밋 자신)을 main에 직접 push 시도:

```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Required status check "quality-gate" is expected.
 ! [remote rejected] main -> main (protected branch hook declined)
```

거부 확인 — 이 커밋은 규칙대로 브랜치 → PR → `quality-gate` 성공 → 머지 경로로
안착했다(이 문서가 main에 있다는 사실 자체가 그 경로의 증거다).

### C-5 플랫폼 절반(code-owner review 필수화): 조건부 유예

`required_pull_request_reviews`는 **의도적으로 이번 적용에서 제외**했다.

- **사유**: GitHub은 PR 작성자의 셀프 승인을 금지한다. 작성자가 소유자 1인뿐인
  현재, code-owner review를 켜면 `.github/workflows/` 변경 PR을 승인할 수 있는
  사람이 없어 정당한 워크플로 변경까지 데드락된다. `enforce_admins`를 끄면
  풀리지만 그건 C-2까지 약화시킨다.
- **위협 평가**: C-5가 막는 "의도적 워크플로 변조"의 행위자는 현재 소유자
  본인뿐이며, 소유자는 어떤 플랫폼 게이트든 설정 변경으로 우회 가능하다 —
  솔로 상태에서 이 게이트의 방어 가치는 0이다.
- **활성화 트리거**: **첫 비소유자 협업자(사람·봇·AI 계정) 추가 시** 아래
  페이로드로 즉시 활성화한다. CODEOWNERS 파일(repo-local 절반)은 이미 가동 대기 중.

```json
{"required_pull_request_reviews": {"require_code_owner_reviews": true, "required_approving_review_count": 1}}
```

### 운영 영향

이후 main 반영 절차: 브랜치 push → PR → `quality-gate` 성공 → 머지.
main 히스토리 재작성(amend·force-push)은 보호에 의해 불가 — main은 append-only.
