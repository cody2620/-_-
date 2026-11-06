# 나만의 용돈 기입장 프로그램 만들기

수입/지출을 기록하고, 검색하고, 월별 요약과 예산을 관리하는 CLI 프로그램입니다.
**Python 3.9 이상 + 표준 라이브러리만** 사용합니다. (`pip install` 필요 없음)

## 실행 방법
```
# 이 README가 있는 폴더(프로젝트 루트)에서 실행
cd 용돈기입장_기능별분류

python3 -m budget_app --help              # 전체 명령 목록
python3 -m budget_app <command> --help    # 명령별 사용법 (모든 명령/하위 명령 지원)

python3 -m budget_app add                 # 대화형으로 거래 추가
python3 -m budget_app list --limit 5
```
- 입력 기본 방식은 **대화형**(`add`, 그리고 `--name` 없이 실행한 `category add`)입니다.
- `list`, `search`, `update`, `delete`, `summary`, `budget`, `category`, `import`, `export`는 **옵션 인자 방식**입니다.
- 옵션은 모두 리눅스 표준인 `--` 표기를 씁니다. (`--help`, `--limit`, `--from`, `--to`, `--month`, `--top`, `--data-dir` ...)
- 공통 옵션 `--data-dir DIR`(저장 폴더 변경), `--verbose`(실행 로그 출력)는 명령 앞/뒤 어디에 써도 됩니다.
  - 예: `python3 -m budget_app --data-dir ./mydata list` 또는 `python3 -m budget_app list --data-dir ./mydata`

### 종료 코드
| 코드 | 의미 |
| --- | --- |
| 0 | 정상 종료 |
| 1 | 예기치 못한 오류 |
| 2 | 입력/옵션 검증 실패 (잘못된 날짜·금액·타입, 필수 옵션 누락 등) |
| 3 | 없는 데이터 (없는 id, 등록되지 않은 카테고리, 없는 CSV 파일, 예산 미설정) |
| 4 | 상태 충돌 (중복 카테고리, 사용 중인 카테고리 삭제 시도) |
| 5 | 저장 파일 읽기/쓰기 실패, 저장 파일 손상 |
| 130 | 사용자가 입력을 취소함 (Ctrl+C / EOF) |

오류는 스택트레이스 없이 `[오류] 원인` + `[힌트] 해결 방법` 형태로 표준 오류(stderr)에 출력됩니다.

## 저장 파일 위치와 형식
- 저장 위치: 기본 `./data` (실행한 폴더 기준), `--data-dir`로 변경 가능
- 저장 형식: **JSONL** (UTF-8, 한 줄에 JSON 객체 1개)
- 저장 파일 3개로 분리해 영구 저장합니다.

| 파일 | 내용 | 한 줄 예시 |
| --- | --- | --- |
| `transactions.jsonl` | 거래 내역 | `{"id": "85df636e", "type": "expense", "date": "2026-11-07", "amount": 12000, "category": "food", "memo": "친구랑 저녁", "tags": ["dinner", "friend"], "created_at": "2026-11-06T17:46:04.798556"}` |
| `categories.jsonl` | 카테고리 목록 | `{"name": "food", "created_at": "2026-11-06T17:46:04.701234"}` |
| `budgets.jsonl` | 월 예산 (월별 1건) | `{"month": "2026-11", "amount": 300000, "updated_at": "2026-11-06T17:50:00.123456"}` |

- **초기 실행**: 저장 폴더/파일이 없으면 자동으로 만들고 `[안내]` 메시지를 출력합니다.
- **기본 카테고리 (안 A)**: `categories.jsonl`이 비어 있으면 `food, transport, rent, shopping, allowance, salary, etc`를 자동 생성합니다.
- **안정성**: `update`/`delete`/카테고리 삭제/예산 저장/`export`는 같은 폴더의 임시 파일에 전체를 다시 쓴 뒤 `os.replace`로 **원자적 교체**합니다. 도중에 실패해도 원본 파일은 그대로 남습니다.
- **스트리밍**: 거래 파일은 제너레이터로 한 줄씩 읽습니다. `list --limit N`은 `heapq.nlargest`로 상위 N건만 메모리에 유지합니다.

### 파일구조
```
용돈기입장_기능별분류/
├── README.md
├── samples/
│   ├── sample_import.csv       # import 예제 (정상 6건)
│   └── invalid_import.csv      # import 검증 오류 예제
└── budget_app/
    ├── __init__.py             # 버전
    ├── __main__.py             # python -m budget_app 진입점
    ├── cli.py                  # 인자 파서 조립, 로깅 설정, 명령 실행/종료 코드
    ├── config.py               # 파일 이름, 기본값, CSV 스키마, 종료 코드 등 상수
    ├── app_context.py          # 저장소·서비스 조립, 초기 파일 생성, 기본 카테고리 생성
    │
    ├── commands/               # [CLI] 기능별 명령 (파서 등록 + 화면 입출력)
    │   ├── _common.py          #   공통 옵션(--data-dir, --verbose), argparse 도우미
    │   ├── add.py              #   add      거래 추가 (대화형)
    │   ├── list_cmd.py         #   list     최신순 목록
    │   ├── search.py           #   search   조건 검색
    │   ├── update.py           #   update   거래 수정 (옵션 방식)
    │   ├── delete.py           #   delete   거래 삭제
    │   ├── summary.py          #   summary  월별 요약 + 예산 사용률
    │   ├── budget.py           #   budget   set / show / list
    │   ├── category.py         #   category add / list / remove
    │   ├── import_cmd.py       #   import   CSV 가져오기
    │   └── export_cmd.py       #   export   CSV 내보내기
    │
    ├── services/               # [서비스] 비즈니스 로직
    │   ├── transaction_service.py  # 거래 생성/조회/검색/수정/삭제
    │   ├── category_service.py     # 카테고리 관리, 사용 중 카테고리 처리
    │   ├── budget_service.py       # 월 예산
    │   ├── summary_service.py      # 월별 집계, 예산 사용률
    │   ├── csv_service.py          # CSV import/export
    │   └── _clock.py               # 현재 시각
    │
    ├── storage/                # [저장소] 파일 I/O
    │   ├── jsonl_file.py           # JSONL 스트리밍 읽기/추가/원자적 재작성
    │   ├── transaction_repository.py
    │   ├── category_repository.py
    │   └── budget_repository.py
    │
    ├── models/                 # [모델] dataclass 데이터 구조
    │   ├── transaction.py          # Transaction
    │   ├── category.py             # Category
    │   ├── budget.py               # Budget
    │   └── filters.py              # TransactionFilter (검색 조건)
    │
    └── core/                   # [공통] 여러 계층이 함께 쓰는 기능
        ├── errors.py               # AppError 계열 예외 (원인 + 힌트 + 종료 코드)
        ├── decorators.py           # @handle_errors, @log_execution
        ├── validators.py           # 날짜/월/타입/금액/카테고리/태그 검증
        ├── prompts.py              # 대화형 입력 (오류 시 재입력)
        └── formatting.py           # 표 출력, 금액 표기, 오류 출력
```
의존 방향: `commands → services → storage → models`, 모든 계층 → `core`

## 주요 명령

| 명령 | 설명 | 예시 |
| --- | --- | --- |
| `add` | 거래 추가 (대화형) | `python3 -m budget_app add` |
| `list` | 최신순 목록 (`--limit` 기본 10) | `python3 -m budget_app list --limit 20` |
| `search` | 조건 검색 (최신순) | `python3 -m budget_app search --from 2026-11-01 --to 2026-11-30 --category food --type expense --q 점심 --tag lunch` |
| `update` | 거래 수정 (**옵션 방식으로 고정**) | `python3 -m budget_app update --id 85df636e --amount 15000 --memo "저녁 회식"` |
| `delete` | 거래 삭제 | `python3 -m budget_app delete --id 85df636e` |
| `summary` | 월별 요약 (`--top` 기본 3) | `python3 -m budget_app summary --month 2026-11 --top 5` |
| `budget set` | 월 예산 저장(덮어쓰기) | `python3 -m budget_app budget set --month 2026-11 --amount 300000` |
| `budget show` | 월 예산/사용률 조회 | `python3 -m budget_app budget show --month 2026-11` |
| `budget list` | 전체 예산 목록 | `python3 -m budget_app budget list` |
| `category list` | 카테고리 + 사용 건수 | `python3 -m budget_app category list` |
| `category add` | 카테고리 추가 | `python3 -m budget_app category add --name hobby` |
| `category remove` | 카테고리 삭제 | `python3 -m budget_app category remove --name hobby --replace etc` |
| `import` | CSV 일괄 등록 | `python3 -m budget_app import --from samples/sample_import.csv` |
| `export` | 조건에 맞는 거래를 CSV로 | `python3 -m budget_app export --out out/2026-11.csv --month 2026-11` |

### add (대화형)
```
$ python3 -m budget_app add
새 거래를 입력합니다. (취소: Ctrl+C)
날짜 (YYYY-MM-DD, 엔터=2026-11-06): 2026-11-31
  ! 존재하지 않는 날짜입니다: '2026-11-31'
    → 월(01~12)과 일(해당 월의 마지막 날 이하)을 확인하세요.
날짜 (YYYY-MM-DD, 엔터=2026-11-06): 2026-11-08
타입 (income/expense, 단축 i/e): e
  (등록된 카테고리: food, transport, rent, shopping, allowance, salary, etc)
카테고리: food
금액 (양의 정수): 7,000
메모 (선택, 엔터=건너뛰기): 학식
태그 (선택, 쉼표로 구분): lunch, school

저장 완료! 생성된 거래 id: ab6490c1
```
- 잘못된 날짜/타입/금액(0·음수·문자)은 이유를 보여주고 **다시 입력**받습니다.
- 등록되지 않은 카테고리는 안내 후 "새로 등록할까요? [y/N]"으로 등록을 유도하고, `n`이면 다시 입력받습니다.

<details>
<summary>add 호출 순서 (어떤 파일의 어떤 함수가 쓰이는지)</summary>

```
python -m budget_app add
│
├─ 1. __main__.py            → cli.main()을 호출
├─ 2. cli.py                 main() → build_parser() → parse_args()   # "add"를 해석
│                            run()  [@handle_errors 적용]
│                              └ app_context.build_context()          # 저장소·서비스 조립
│                              └ args.handler(args, ctx)              # = add.handle
│
├─ 3. commands/add.py        handle(args, ctx)                        # 화면 입출력 담당
│     │
│     ├ core/prompts.py      ask()  ← 날짜/타입/금액/메모/태그를 입력받고 검증, 틀리면 재입력
│     │   └ core/validators.py  parse_date / parse_type / parse_amount / parse_memo / parse_tags
│     │
│     ├ add.py               _ask_category(ctx.categories)            # 카테고리 입력
│     │   └ services/category_service.py  names()                     # 등록된 목록 조회
│     │       └ storage/category_repository.py  names()
│     │
│     └ ctx.transactions.create(...)                                  # 저장 요청
│
├─ 4. services/transaction_service.py   TransactionService.create()   # 규칙 담당
│     ├ category_service.ensure_exists()      # 카테고리 존재 확인 (없으면 NotFoundError)
│     ├ transaction_repository.iter_ids()     # 기존 id 목록 수집
│     ├ _new_id()                             # 중복 없는 8자리 id 생성
│     ├ _clock.now_iso()                      # 생성 시각 기록
│     └ Transaction(...)                      # models/transaction.py, 거래 객체 생성
│
├─ 5. storage/transaction_repository.py add(tx)
│     └ tx.to_dict()                          # 객체 → dict
│
├─ 6. storage/jsonl_file.py             append() → append_many()
│     └ transactions.jsonl 끝에 한 줄 추가 + fsync
│
└─ 7. add.py handle()로 복귀            "저장 완료! 생성된 거래 id" 출력
      └ core/formatting.py describe(tx)
```

| 계층 | 파일 | 하는 일 |
| --- | --- | --- |
| 명령(commands) | `add.py` | 질문하고 입력받기, 결과 출력 |
| 서비스(services) | `transaction_service.py` | 카테고리 확인, id·시간 부여 |
| 저장소(storage) | `transaction_repository.py`, `jsonl_file.py` | 파일에 한 줄 쓰기 |
| 모델(models) | `transaction.py` | 거래 데이터 구조 |
| 공통(core) | `prompts.py`, `validators.py`, `formatting.py` | 입력 검증과 출력 |

</details>

### update (옵션 방식 - 안 A로 고정)
`update --id <id> [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]`
- 지정한 필드만 바뀝니다. 아무 필드도 없으면 오류입니다.
- `--memo ""` / `--tags ""` 로 메모/태그를 비울 수 있습니다. `--tags`는 기존 태그를 **대체**합니다.
- 없는 id는 `없는 데이터` 메시지와 함께 종료 코드 3으로 끝납니다. (`delete`도 동일)

### search 조건
- `--from`, `--to`: 기간 (양 끝 포함), `--category`, `--type income|expense`
- `--q`: 메모 부분 일치 (대소문자 무시), `--tag`: 태그 (반복 지정 시 모두 포함한 거래)
- `--limit N`(선택): 최대 출력 건수. 조건은 모두 AND로 결합됩니다.

### summary / budget
- 총 수입, 총 지출, 잔액(총수입-총지출), 카테고리별 지출 TOP N을 출력합니다.
- 거래가 없는 달은 `데이터 없음`을 출력합니다.
- 예산이 설정되어 있으면 사용률(%)을 보여주고, 초과하면 `⚠ 경고: 예산을 N원 초과했습니다!`, 80% 이상이면 주의 문구를 출력합니다.

### category remove (사용 중인 카테고리 처리)
- 해당 카테고리를 쓰는 거래가 있으면 **삭제를 막고** 종료 코드 4로 끝납니다.
- `--replace <대체카테고리>`를 지정하면 그 거래들을 대체 카테고리로 옮긴 뒤 삭제합니다.

## import/export CSV 스키마

| column | required | 설명 |
| --- | --- | --- |
| date | Y | YYYY-MM-DD |
| type | Y | income / expense |
| category | Y | 등록된 카테고리 |
| amount | Y | 양수 정수 |
| memo | N | 문자열 |
| tags | N | 쉼표(,) 구분 문자열 (CSV 안에서는 `"lunch,school"` 처럼 따옴표로 감쌈) |
| 공통: UTF-8, 헤더 포함 |   |   |

```csv
date,type,category,amount,memo,tags
2026-11-01,income,allowance,300000,11월 용돈,monthly
2026-11-02,expense,food,8500,편의점 점심,"lunch,school"
2026-11-05,expense,shopping,45000,운동화,
```

- **import** `--from <csv>`: 먼저 모든 행을 검증합니다. 잘못된 행이 하나라도 있으면 **아무것도 반영하지 않고** 행 번호별 오류를 출력합니다(종료 코드 2). `--skip-invalid`를 주면 잘못된 행만 건너뛰고 나머지를 반영합니다. 완료 시 처리 건수를 출력합니다.
- **export** `--out <csv>`: `--month YYYY-MM` 또는 `--from YYYY-MM-DD --to YYYY-MM-DD`(둘 다) 중 **하나가 필수**입니다(둘을 섞어 쓸 수는 없음). 선택으로 `--category`, `--type`도 쓸 수 있습니다. 출력 폴더가 없으면 만들고, 같은 파일이 있으면 덮어씁니다.

--- 

## 트러블 슈팅

| 증상 | 원인 / 해결 |
| --- | --- |
| `No module named budget_app` | 프로젝트 루트(README가 있는 폴더)에서 실행하세요. |
| `error: unrecognized arguments: -top 2` | 옵션은 `--top`처럼 대시 두 개(`--`)를 씁니다. |
| `등록되지 않은 카테고리입니다` | `category list`로 확인하고, 없으면 `category add --name <이름>`으로 등록하세요. |
| `카테고리를 사용하는 거래가 N건 있어 삭제할 수 없습니다` | `category remove --name X --replace <다른카테고리>`로 거래를 옮기며 삭제하세요. |
| `transactions.jsonl N번째 줄이 올바른 JSON이 아닙니다` | 파일을 직접 고치다 생긴 문제입니다. 해당 줄을 고치거나 지우세요. |
| `CSV 파일이 UTF-8 인코딩이 아닙니다` | 엑셀에서는 **CSV UTF-8(쉼표로 분리)** 형식으로 저장하세요. (BOM 있어도 됨) |
| `CSV에 잘못된 행이 N건 있어 가져오기를 중단했습니다` | 출력된 행 번호를 고치거나 `--skip-invalid`를 사용하세요. |
| `입력이 끝나(EOF)...` | `add`는 대화형입니다. 터미널에서 직접 실행하세요. |
| 실행 흐름을 보고 싶을 때 | `--verbose`를 붙이면 명령 시작/종료/소요 시간이 stderr로 출력됩니다. |
| 데이터를 처음부터 다시 | 저장 폴더(기본 `./data`)를 지우면 다음 실행 때 다시 초기화됩니다. |

## 용어 및 개념

- **JSONL (JSON Lines)**: 한 줄에 JSON 객체 하나. 파일 전체를 읽지 않고 한 줄씩 처리할 수 있고, 추가(append)가 쉽습니다.
- **제너레이터 스트리밍**: `yield`로 거래를 한 건씩 넘겨주어 파일 크기와 상관없이 메모리를 적게 씁니다. (`TransactionRepository.iter_all`)
- **원자적 교체 (atomic replace)**: 임시 파일에 완성본을 쓴 뒤 `os.replace`로 한 번에 바꿔치기해, 중간에 실패해도 파일이 깨지지 않게 합니다.
- **dataclass**: 필드만 선언하면 생성자/비교 등을 자동으로 만들어 주는 데이터 클래스. (`Transaction`, `Category`, `Budget`, `TransactionFilter`, `MonthlySummary` ...)
- **Repository / Service**: Repository는 파일 읽기·쓰기만, Service는 검증·규칙(카테고리 존재 확인, 사용 중 카테고리 처리 등)을 맡습니다.
- **데코레이터**
  - `@handle_errors` (`core/decorators.py`): 모든 예외를 잡아 `[오류] 원인 / [힌트] 해결법`으로 출력하고 종료 코드를 정합니다. (`cli.run`에 적용)
  - `@log_execution`: 명령 시작/종료/소요 시간을 로그로 남깁니다. (모든 명령 handler에 적용, `--verbose`로 확인)
- **종료 코드 (exit code)**: 프로그램이 끝날 때 운영체제에 돌려주는 숫자. 0은 성공, 0이 아니면 실패입니다. (`echo $?`로 확인)

#

<details> 
  <summary> 최종 결과물 </summary>
  <img width="666" height="641" alt="1" src="https://github.com/user-attachments/assets/11e4a251-5def-4747-a3ae-a3cfd63fe8fb" />
  <img width="666" height="597" alt="2" src="https://github.com/user-attachments/assets/aea6acd6-6fd2-4090-a5e0-33274df41469" />


</details>


#

<details> 
  <summary> 기능 요구 사항 </summary>

  ### 

다음 요구사항을 모두 만족해야 한다.

#### 1. 실행 및 입력 방식

- 실행 예시는 아래 중 하나를 권장합니다.
  - `python -m budget_app <command> [options]`
- 모든 명령은 `--help` 옵션으로 사용 방법이 출력되어야 합니다.
- 입력 기본 방식은 "대화형" 입니다.
  - 예: `add` 실행 시 날짜/타입/카테고리/금액 등을 `input()`으로 순차 입력
- 단, 아래 항목은 옵션 인자 방식도 허용(권장) 합니다.
  - `search`, `list`, `summary`, `export`, `import`, `delete`
  - `update`는 "옵션 방식 또는 대화형" 중 하나를 선택해도 되나, 문서에 명확히 고정해야 합니다(아래 6번 참고).
- 옵션 표기는 리눅스 표준인 `--`로 통일해야 합니다.
  - 예: `--help`, `--limit`, `--from`, `--to`, `--month`

#### 2. 데이터 모델

- 거래 내역(Transaction)은 최소 아래 필드를 포함해야 합니다.
  - `id`(유일), `type`(income/expense), `date`(YYYY-MM-DD), `amount`(양수), `category`, `memo`(선택), `tags`(선택)
- 데이터 모델은 dataclass 또는 그에 준하는 구조로 정의해야 합니다.
- 최소 2개 이상의 클래스를 사용해야 합니다.
  - 예시: Transaction, TransactionRepository, BudgetStore, CategoryStore, BudgetService 등
- 입력 검증
  - 날짜 형식 오류, 음수/0 금액, 허용되지 않은 type, 존재하지 않는 category 등은 재입력 요구 또는 오류 메시지 출력으로 처리합니다.

#### 3. 저장 정책

- 저장 포맷은 JSONL 또는 CSV 중 1개를 선택합니다.
- 저장 파일은 **3개 이상(필수)** 로 분리해 영구 저장합니다.
  - `transactions.<fmt>`, `categories.<fmt>`, `budgets.<fmt>`
- 기본 저장 폴더는 `./data`를 권장하며, 옵션으로 변경 가능해야 합니다(예: `-data-dir`).
- 초기 실행(저장 파일이 없을 때)
  - 파일이 없으면 자동 생성하거나, "초기화 안내 메시지"를 출력해야 합니다.
  - 카테고리 파일이 비어있으면 아래 중 하나를 택해 동작을 명확히 하세요.
    - (안 A) 기본 카테고리 자동 생성(예: food, transport, rent, etc)
    - (안 B) `category add`를 먼저 하도록 안내하고 `add`를 막음      

#### 4. add(거래 추가)

- `add` 실행 후 대화형으로 필드를 입력받아 거래를 저장해야 합니다.
- category는 등록된 목록에 존재해야 합니다(없으면 안내 후 재입력/등록 유도).
- 저장 완료 시 생성된 id를 사용자에게 출력해야 합니다.

#### 5. list(목록 조회)

- `list`는 최신순으로 거래를 출력해야 합니다.
- `--limit N` 옵션을 지원해야 합니다(기본값 제공).
- 파일 전체를 한 번에 로드하지 않고, 제너레이터 기반 스트리밍 처리로 구현해야 합니다.

#### 6. update/delete(수정/삭제)

- `delete --id <id>`로 특정 거래를 삭제할 수 있어야 합니다.
- 존재하지 않는 id는 "없는 데이터"로 처리하고 사용자 메시지를 출력해야 합니다.
- `update`는 아래 중 하나의 방식으로 문서에 명확히 고정해 구현해야 합니다.
  - (안 A) 옵션 기반: `update --id <id> [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]`
  - (안 B) 대화형 기반: 수정할 필드만 선택/재입력 받는 흐름
- 파일 기반 저장에서 update/delete는 "전체 재작성/임시 파일/원자적 교체(권장)" 등 안정성을 고려해야 합니다.

#### 7. search(검색)

- 조건 기반 검색을 지원해야 합니다.
  - 기간: `--from`, `--to`
  - 카테고리: `--category`
  - 타입: `--type`
  - 메모 키워드: `--q`
  - 태그: `--tag`
- 검색 결과는 최신순으로 출력해야 합니다.
- 스트리밍 처리(제너레이터 기반)를 유지해야 합니다.

#### 8. summary(월별 요약)

- `summary --month YYYY-MM` 입력을 받아 해당 월의 요약을 출력해야 합니다.
- 출력 항목:
  - 총 수입, 총 지출, 잔액(총수입-총지출)
  - 카테고리별 지출 합계 TOP N(`-top` 옵션 지원)
- 데이터가 없는 달은 "데이터 없음"을 명확히 출력해야 합니다.

#### 9. budget(예산)

- `budget set --month YYYY-MM --amount <금액>`으로 월 예산을 저장해야 합니다.
- `summary` 실행 시 예산이 설정되어 있으면
  - 예산 대비 사용률(%)
  - 초과 여부(초과 시 경고 문구) 를 함께 출력해야 합니다.
- 예산 데이터도 반드시 영구 저장되어야 합니다.

#### 10. category(카테고리 관리)

- `category add/list/remove`를 제공해야 합니다.
- 카테고리 삭제 시, 해당 카테고리를 사용하는 내역이 존재하면
- 삭제를 막거나
- 대체 카테고리를 요구해야 합니다

#### 11. import/export(가져오기/내보내기)

- `import --from \`로 거래를 일괄 등록한다.
- `export --out \`로 조건에 맞는 거래를 CSV로 저장한다.
- export는 `--month YYYY-MM` 또는 `--from YYYY-MM-DD --to YYYY-MM-DD` 중 하나 이상 조건을 필수로 받는다.
- import/export는 아래 CSV 최소 스키마를 고정한다.
  
| column | required | 설명 |
| --- | --- | --- |
| date | Y | YYYY-MM-DD |
| type | Y | income / expense |
| category | Y | 등록된 카테고리 |
| amount | Y | 양수 정수 |
| memo | N | 문자열 |
| tags | N | 쉼표(,) 구분 문자열 |
| 공통: UTF-8, 헤더 포함 |   |   |

(1) 데코레이터(Decorator)
- 공통 관심사(예: 예외 처리/로그/시간 측정) 데코레이터를 1개 이상 구현하고 실제 적용한다.

(2) 예외 처리 및 종료 코드
- 오류는 스택트레이스 대신 원인 + 해결 힌트로 출력한다.
- 정상 종료는 0, 오류 종료는 0이 아닌 값으로 종료한다.

(3) 모듈화(구조화)
- 한 파일에 몰아넣지 않고 최소 3개 이상 모듈로 분리한다.
- (권장) CLI / 서비스 / 저장소(파일 I/O) / 모델(데이터 구조)로 책임을 나눈다.


</details>

<details>
  <summary>제약사항</summary>
  <img width="658" height="583" alt="제약사항" src="https://github.com/user-attachments/assets/d20d82b0-b0f5-4401-a37e-a4ad768a9180" />

</details> 

