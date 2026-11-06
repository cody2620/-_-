"""앱 전역 설정값(상수) 모음.

[파일 역할]
- 저장 폴더/파일 이름, 기본 카테고리, 기본 옵션값, CSV 스키마, 입력 제한값,
  종료 코드처럼 여러 모듈이 함께 쓰는 값을 한 곳에 모아 둔다.
- 값을 바꾸고 싶을 때 이 파일만 고치면 전체에 반영된다.
- 함수/클래스는 없고 상수만 정의한다.
"""

DEFAULT_DATA_DIR = "./data"

# 저장 포맷: JSONL (한 줄 = JSON 객체 1개)
STORAGE_FORMAT = "jsonl"
TRANSACTIONS_FILE = f"transactions.{STORAGE_FORMAT}"
CATEGORIES_FILE = f"categories.{STORAGE_FORMAT}"
BUDGETS_FILE = f"budgets.{STORAGE_FORMAT}"

# 카테고리 파일이 비어 있으면 자동 생성되는 기본 카테고리 (요구사항 3 - 안 A)
DEFAULT_CATEGORIES = ("food", "transport", "rent", "shopping", "allowance", "salary", "etc")

TRANSACTION_TYPES = ("income", "expense")
TYPE_LABELS = {"income": "수입", "expense": "지출"}

DEFAULT_LIST_LIMIT = 10
DEFAULT_SUMMARY_TOP = 3

# import/export CSV 스키마 (UTF-8, 헤더 포함)
CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")
CSV_REQUIRED_COLUMNS = ("date", "type", "category", "amount")

MAX_AMOUNT = 1_000_000_000_000
MAX_MEMO_LENGTH = 200
MAX_CATEGORY_LENGTH = 30

# 종료 코드
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_VALIDATION = 2
EXIT_NOT_FOUND = 3
EXIT_CONFLICT = 4
EXIT_STORAGE = 5
EXIT_CANCELLED = 130
