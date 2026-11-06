"""입력값 검증/변환 함수 모음.

[파일 역할]
- 대화형 입력(add), 옵션 인자(argparse), CSV import 에서 같은 검증 규칙을 쓰도록
  검증 로직을 한 곳에 모은다.
- 모든 함수는 문자열을 받아 정규화된 값을 반환하고,
  실패 시 ValidationError(원인 + 힌트)를 발생시킨다.
"""

import re
from datetime import datetime
from typing import List

from .. import config
from .errors import ValidationError

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_INT_RE = re.compile(r"^\+?\d+$")

_TYPE_ALIASES = {"i": "income", "e": "expense", "수입": "income", "지출": "expense"}


def parse_date(value: str) -> str:
    """날짜 문자열을 검증한다.

    [역할] YYYY-MM-DD 형식인지, 실제로 존재하는 날짜인지(예: 2026-02-30 불가) 확인한다.

    Args:
        value: 입력 문자열
    Returns:
        앞뒤 공백을 제거한 'YYYY-MM-DD' 문자열
    Raises:
        ValidationError: 형식이 틀리거나 존재하지 않는 날짜
    """
    text = (value or "").strip()
    if not _DATE_RE.match(text):
        raise ValidationError(f"날짜 형식이 올바르지 않습니다: '{value}'",
                              "YYYY-MM-DD 형식으로 입력하세요. 예: 2026-11-06")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"존재하지 않는 날짜입니다: '{value}'",
                              "월(01~12)과 일(해당 월의 마지막 날 이하)을 확인하세요.") from None
    return text


def parse_month(value: str) -> str:
    """월 문자열을 검증한다.

    [역할] YYYY-MM 형식이고 월이 01~12 인지 확인한다. (summary/budget/export 에서 사용)

    Returns:
        'YYYY-MM' 문자열
    Raises:
        ValidationError: 형식이 틀리거나 존재하지 않는 월
    """
    text = (value or "").strip()
    if not _MONTH_RE.match(text):
        raise ValidationError(f"월 형식이 올바르지 않습니다: '{value}'",
                              "YYYY-MM 형식으로 입력하세요. 예: 2026-11")
    try:
        datetime.strptime(text, "%Y-%m")
    except ValueError:
        raise ValidationError(f"존재하지 않는 월입니다: '{value}'", "월은 01~12 사이여야 합니다.") from None
    return text


def parse_type(value: str, allow_alias: bool = False) -> str:
    """거래 타입을 검증한다.

    [역할] 대소문자 구분 없이 income/expense 만 허용한다.
    allow_alias=True(대화형 입력)이면 i/e/수입/지출 단축 입력도 허용한다.

    Args:
        value: 입력 문자열
        allow_alias: 단축 입력 허용 여부
    Returns:
        'income' 또는 'expense'
    Raises:
        ValidationError: 허용되지 않은 타입
    """
    text = (value or "").strip().lower()
    if allow_alias:
        text = _TYPE_ALIASES.get(text, text)
    if text not in config.TRANSACTION_TYPES:
        hint = "income 또는 expense 중 하나를 입력하세요."
        if allow_alias:
            hint += " (단축 입력: i / e / 수입 / 지출)"
        raise ValidationError(f"허용되지 않은 거래 타입입니다: '{value}'", hint)
    return text


def parse_amount(value: str) -> int:
    """금액을 검증한다.

    [역할] 쉼표와 끝의 '원'을 제거한 뒤 양의 정수인지 확인한다.
    0, 음수, 소수, 문자, 너무 큰 값(MAX_AMOUNT 이상)은 거부한다.

    Returns:
        금액(int)
    Raises:
        ValidationError: 양의 정수가 아니거나 범위를 벗어남
    """
    text = str(value or "").strip().replace(",", "")
    if text.endswith("원"):
        text = text[:-1].strip()
    if not _INT_RE.match(text):
        raise ValidationError(f"금액은 양의 정수여야 합니다: '{value}'",
                              "숫자만 입력하세요(쉼표 허용). 음수/소수/문자는 사용할 수 없습니다. 예: 12000")
    amount = int(text)
    if amount <= 0:
        raise ValidationError(f"금액은 0보다 커야 합니다: '{value}'", "1 이상의 금액을 입력하세요.")
    if amount >= config.MAX_AMOUNT:
        raise ValidationError(f"금액이 너무 큽니다: '{value}'", f"{config.MAX_AMOUNT:,} 미만으로 입력하세요.")
    return amount


def parse_positive_int(value: str) -> int:
    """1 이상의 정수를 검증한다. (--limit, --top 옵션에서 사용)

    Returns:
        정수 값
    Raises:
        ValidationError: 숫자가 아니거나 1 미만
    """
    text = (value or "").strip()
    if not _INT_RE.match(text) or int(text) <= 0:
        raise ValidationError(f"1 이상의 정수가 필요합니다: '{value}'", "예: 5")
    return int(text)


def parse_category_name(value: str) -> str:
    """카테고리 이름을 검증하고 정규화한다.

    [역할] 앞뒤 공백 제거 + 소문자 변환(Food → food)으로 같은 카테고리가
    다르게 저장되는 것을 막는다. 빈 값, 쉼표 포함, 30자 초과는 거부한다.

    Returns:
        정규화된 카테고리 이름
    Raises:
        ValidationError: 규칙 위반
    """
    text = (value or "").strip().lower()
    if not text:
        raise ValidationError("카테고리 이름이 비어 있습니다.", "예: food, transport")
    if "," in text:
        raise ValidationError(f"카테고리 이름에 쉼표(,)를 쓸 수 없습니다: '{value}'", "쉼표 없이 입력하세요.")
    if len(text) > config.MAX_CATEGORY_LENGTH:
        raise ValidationError("카테고리 이름이 너무 깁니다.", f"{config.MAX_CATEGORY_LENGTH}자 이하로 입력하세요.")
    return text


def parse_memo(value: str) -> str:
    """메모를 검증한다. (앞뒤 공백 제거, 200자 이하)

    Returns:
        메모 문자열 (빈 문자열 가능)
    Raises:
        ValidationError: 너무 긴 메모
    """
    text = (value or "").strip()
    if len(text) > config.MAX_MEMO_LENGTH:
        raise ValidationError("메모가 너무 깁니다.", f"{config.MAX_MEMO_LENGTH}자 이하로 입력하세요.")
    return text


def parse_tags(value: str) -> List[str]:
    """쉼표(,) 구분 문자열을 태그 리스트로 바꾼다.

    [역할] 각 태그의 공백 제거 + 소문자 변환, 빈 값과 중복은 제거한다. (순서 유지)
    예: " Lunch, school,,lunch " → ["lunch", "school"]

    Returns:
        태그 리스트 (빈 문자열이면 빈 리스트)
    """
    tags: List[str] = []
    for raw in (value or "").split(","):
        tag = raw.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def parse_tag(value: str) -> str:
    """검색용 태그 1개를 검증한다. (search --tag 에서 사용)

    [역할] 한 옵션에 쉼표로 여러 태그를 넣으면 거부하고,
    --tag a --tag b 처럼 반복 지정하도록 안내한다.

    Returns:
        정규화된 태그 1개
    Raises:
        ValidationError: 비어 있거나 여러 개인 경우
    """
    tags = parse_tags(value)
    if len(tags) != 1:
        raise ValidationError(f"태그는 하나씩 지정해야 합니다: '{value}'",
                              "여러 태그는 --tag a --tag b 처럼 옵션을 반복하세요.")
    return tags[0]


def parse_id(value: str) -> str:
    """거래 id를 검증한다. (공백 제거, 소문자 변환, 빈 값 거부)

    Returns:
        정규화된 id 문자열
    Raises:
        ValidationError: 빈 id
    """
    text = (value or "").strip().lower()
    if not text:
        raise ValidationError("id가 비어 있습니다.", "list 또는 search 명령으로 거래 id를 확인하세요.")
    return text


def parse_keyword(value: str) -> str:
    """메모 검색 키워드를 검증한다. (search --q 에서 사용, 빈 값 거부)

    Returns:
        공백을 제거한 키워드
    Raises:
        ValidationError: 빈 키워드
    """
    text = (value or "").strip()
    if not text:
        raise ValidationError("검색 키워드가 비어 있습니다.", "예: --q 점심")
    return text
