# 자동 실행 시 LLM을 어떻게 붙일까 — API 키 vs Claude 구독

회의 제목을 "내용을 읽고 이해해서 정리"하려면 매 실행마다 LLM(Claude) 호출이 필요하다.
GitHub Actions가 스크립트를 돌리는 것까지는 무료(public repo)지만, **LLM 호출 부분은 인증 수단이 따로 필요**하다.
방법은 두 가지.

| | 방식 A: Anthropic API 키 | 방식 B: Claude 구독 토큰 |
|---|---|---|
| 추가 결제 | 있음 (쓴 만큼, 소액) | 없음 (이미 내는 Pro/Max 구독) |
| 무게 | 가벼움 — API 요청 1번 | 무거움 — Claude Code 에이전트 실행 |
| 한도 | 결제한 만큼 | 구독 사용량 한도 공유 |
| 유지보수 | 키 그대로 두면 됨 | 토큰 만료 시 재발급 |
| 설정 난이도 | 쉬움 | 중간 |
| 추천 대상 | "단순·예측가능·소액이면 OK" | "추가 결제 절대 안 함" |

---

## 공통 구조 (둘 다 동일)

```
[매일 18:00 KST]  GitHub Actions 임시 컴퓨터가 켜짐
        │
        ├─ Notion API 로 회의 페이지 내용 가져오기      (결정적, 코드가 함)
        │
        ├─ 회의 내용을 Claude 에게 보내 제목/목차 받기   ← 여기만 방식 A/B 로 갈림
        │
        └─ 결과를 Notion 에 써넣기                      (결정적, 코드가 함)
```

- 회사 서버는 안 엮임. 전부 GitHub(Microsoft) 임시 컴퓨터에서 돎.
- `NOTION_TOKEN` 은 두 방식 모두 GitHub repo Secrets 에 저장 (코드에 안 적음).
- public repo 라서 GitHub Actions 실행 시간은 무제한 무료.

---

## 방식 A — Anthropic API 키

### 원리
스크립트가 `api.anthropic.com` 에 "이 회의 내용 요약해서 제목 뽑아줘" 요청을 1번 보내고 응답을 받는다.
Notion API 를 부르는 것과 똑같은 방식. 에이전트도, 툴도, 기억도 없음.

### 셋업 순서
1. https://console.anthropic.com 가입
2. **Billing** 에 결제수단 등록 + 소액 크레딧 충전 (예: $5)
3. **API Keys** → 키 발급 (`sk-ant-...`)
4. 그 키를 GitHub repo → Settings → Secrets → `ANTHROPIC_API_KEY` 로 저장
5. workflow 에서 `python rename.py --apply` 실행 시 이 키를 env 로 넘김

### 비용 (추정)

가정: 회의 1건 = 입력 약 5,000토큰(회의록 본문 + 지시문) + 출력 약 1,000토큰(제목 + 목차).

| 모델 | 회의 1건 | 하루 3건 → 월 | 하루 10건 → 월 |
|---|---|---|---|
| Claude Haiku 4.5 | ≈ $0.01 | ≈ $1 | ≈ $3 |
| Claude Sonnet 5 | ≈ $0.02 | ≈ $2 | ≈ $6 |
| Claude Opus 5 | ≈ $0.05 | ≈ $5 | ≈ $15 |

- 실제로는 회의 수가 이보다 적을 가능성이 높아 더 쌈.
- 제목/목차 정리 정도면 **Haiku 4.5 또는 Sonnet 5 로 충분.**
- 정확한 단가는 구현 시점에 https://www.anthropic.com/pricing 에서 재확인.

### 장점
- 설정이 단순하고 한 번 하면 안 건드려도 됨
- 비용이 사용량에 정확히 비례 (예측 가능)
- 요청 1번이라 빠르고 실패 지점이 적음

### 단점
- 구독과 별개로 결제수단·크레딧을 관리해야 함
- (소액이지만) 어쨌든 추가 지출

---

## 방식 B — Claude 구독 토큰 (`claude setup-token`)

### 원리
Claude Code 에는 **로그인 상태(= 내 Pro/Max 구독)를 장기 토큰 하나로 뽑는** 명령이 있다.
그 토큰을 GitHub Secrets 에 넣고, workflow 가 **공식 Claude Code GitHub Action** 을 실행하면
그 토큰으로 인증되어 **내 구독 사용량으로** 처리된다. 별도 청구 없음.

### 셋업 순서
1. 내 PC 에서 (Claude 에 Pro/Max 로그인된 상태):
   ```
   claude setup-token
   ```
   → 브라우저 인증 후 긴 토큰(`CLAUDE_CODE_OAUTH_TOKEN`) 출력
2. 그 토큰을 GitHub repo → Settings → Secrets → `CLAUDE_CODE_OAUTH_TOKEN` 로 저장
3. workflow 를 raw API 호출 대신 **Claude Code 를 headless 로 실행**하는 형태로 작성
   (Notion 읽기/쓰기는 그대로 파이썬이 하고, "내용 이해" 단계만 Claude Code 에 위임)

### 제약 / 주의
- **플랜 확인 필요**: Max 는 확실히 됨. **Pro 에서도 되는지는 시점에 따라 다를 수 있어** 실제로 `claude setup-token` 을 돌려봐야 확실.
- **사용량 한도 공유**: 구독의 5시간·주간 한도를 대화용과 같이 씀. 하루 회의 몇 건이면 문제없지만, 한 번에 수십 건 몰리면 한도에 걸릴 수 있음.
- **토큰 만료**: 장기 토큰이지만 영구는 아님. 만료되면 `claude setup-token` 다시 돌려 Secret 갱신.
- **무거움**: API 요청 1번이 아니라 Claude Code 에이전트가 통째로 도는 구조라 실행이 더 느리고, 결과가 매번 조금씩 달라질 수 있음.
- Anthropic 정책상 자동화에 구독 토큰을 쓰는 건 허용되지만, 대량·상용 트래픽엔 API 를 쓰라는 게 공식 권장.

### 장점
- **추가 결제 0원** — 이미 쓰는 구독 그대로
- 결제수단·크레딧 관리 안 해도 됨

### 단점
- 셋업 단계가 A 보다 많음 (headless 설정 + 토큰 관리)
- 구독 한도에 묶임
- 토큰 주기적 갱신 필요
- 실행이 무겁고 덜 예측적

---

## 비교표 (상세)

| 항목 | 방식 A (API 키) | 방식 B (구독 토큰) |
|---|---|---|
| 월 비용 | Haiku ~$1–3 / Sonnet ~$2–6 | $0 |
| 결제수단 등록 | 필요 (Anthropic Console) | 불필요 |
| 인증 저장 | `ANTHROPIC_API_KEY` Secret | `CLAUDE_CODE_OAUTH_TOKEN` Secret |
| 실행 방식 | 파이썬이 API 1회 호출 | Claude Code Action 실행 |
| 속도 | 빠름 (수 초) | 느림 (수십 초~분) |
| 결과 일관성 | 높음 (단일 호출) | 중간 (에이전트) |
| 한도 | 충전액까지 | 구독 rate limit |
| 유지보수 | 거의 없음 | 토큰 만료 시 재발급 |
| 중단 위험 | 크레딧 소진 시 | 구독 한도 초과 시 / 토큰 만료 시 |

---

## 추천

**하루 회의 몇 건 수준이면 둘 다 잘 돌아간다.**

- **추가 결제를 절대 안 하고 싶다** → 방식 B. 단, `claude setup-token` 이 내 플랜(Pro)에서 되는지 먼저 확인.
- **가장 단순하고 예측 가능한 걸 원한다** → 방식 A + Haiku 4.5. 이 물량에서 비용은 사실상 커피 한 잔 미만.

개인적으로는 **방식 A + Haiku 4.5** 를 먼저 권함: 셋업이 10분이고, 한 번 해두면 신경 쓸 게 없고, 회의록이 Anthropic 으로만 가고(제3자 최소화), 월 비용이 무시할 수준이라서.
"결제수단 등록 자체가 싫다"면 방식 B 로 가되 토큰 관리 부담을 감수하면 됨.

---

## 어느 쪽이든 공통으로 필요한 것

1. **방식 A / B 결정**
2. **제목·목차 규칙** — 제목 길이·언어·형식(예: `2026-08-27 | RAGbuilder·Wiki 논의`), 본문 정리 수준(제목만 / 요약블록 추가 / 본문 재작성)
3. **Notion integration 토큰** + **회의 DB 링크**
4. (방식 A) Anthropic API 키  /  (방식 B) `CLAUDE_CODE_OAUTH_TOKEN`
5. `gh auth refresh -h github.com -s workflow` — workflow 파일을 GitHub 에 올리기 위한 1회 권한 부여
