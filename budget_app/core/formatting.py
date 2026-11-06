"""화면 출력 도우미.

[파일 역할]
- 한글(2칸)과 영문(1칸)의 화면 폭 차이를 고려해 표의 열을 정렬한다.
- 금액을 '12,000원' 형태로 표기한다.
- 거래 목록 표, 거래 상세, 오류 메시지 출력 형식을 한 곳에서 관리한다.
"""

import sys
import unicodedata
from typing import Iterable

from .. import config


def display_width(text: str) -> int:
    """문자열이 터미널에서 차지하는 칸 수를 계산한다.

    [역할] 한글·한자 등 전각 문자(W, F)는 2칸, 나머지는 1칸으로 센다.

    Returns:
        화면 폭(칸 수)
    """
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def fit(text: str, width: int, align: str = "left") -> str:
    """문자열을 정해진 화면 폭에 맞춘다.

    [역할] 폭보다 길면 잘라서 끝에 '…'를 붙이고, 짧으면 공백으로 채운다.

    Args:
        text: 출력할 값
        width: 맞출 화면 폭(칸 수)
        align: "left" 또는 "right"
    Returns:
        정확히 width 칸을 차지하는 문자열
    """
    text = str(text)
    if display_width(text) > width:
        out, used = "", 0
        for ch in text:
            w = display_width(ch)
            if used + w > width - 1:
                break
            out += ch
            used += w
        text = out + "…"
    pad = " " * max(0, width - display_width(text))
    return pad + text if align == "right" else text + pad


def money(amount: int) -> str:
    """금액을 천 단위 쉼표와 '원'을 붙인 문자열로 바꾼다. 예: 12000 → '12,000원'"""
    return f"{amount:,}원"


def signed_money(tx) -> str:
    """거래 금액에 부호를 붙여 표시한다. (수입 '+12,000원', 지출 '-12,000원')

    Args:
        tx: Transaction
    """
    sign = "+" if tx.type == "income" else "-"
    return f"{sign}{money(tx.amount)}"


def type_label(tx_type: str) -> str:
    """거래 타입을 한글 이름으로 바꾼다. (income → 수입, expense → 지출)"""
    return f"{config.TYPE_LABELS.get(tx_type, tx_type)}"


# (헤더, 폭, 정렬)
_COLUMNS = (("ID", 8, "left"), ("날짜", 10, "left"), ("구분", 4, "left"), ("카테고리", 10, "left"),
            ("금액", 14, "right"), ("메모", 20, "left"), ("태그", 16, "left"))


def _row(values) -> str:
    """값 목록을 _COLUMNS 의 폭/정렬에 맞춰 표의 한 줄로 만든다."""
    return "  ".join(fit(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)).rstrip()


def print_transactions(transactions: Iterable) -> int:
    """거래 목록을 표 형태로 출력한다.

    [역할] 거래를 한 건씩 받아 바로 출력한다(스트리밍). 첫 거래가 나올 때
    헤더와 구분선을 출력하므로, 거래가 없으면 아무것도 출력하지 않는다.

    Args:
        transactions: Transaction 들의 iterable (리스트나 제너레이터)
    Returns:
        출력한 거래 건수
    """
    count = 0
    for tx in transactions:
        if count == 0:
            print(_row([c[0] for c in _COLUMNS]))
            print("-" * (sum(c[1] for c in _COLUMNS) + 2 * (len(_COLUMNS) - 1)))
        print(_row([tx.id, tx.date, type_label(tx.type), tx.category, signed_money(tx),
                    tx.memo or "-", ", ".join(tx.tags) or "-"]))
        count += 1
    return count


def describe(tx) -> str:
    """거래 1건을 여러 줄의 상세 형태로 만든다. (add/delete 결과 출력에 사용)

    Args:
        tx: Transaction
    Returns:
        'id/날짜/구분/카테고리/금액/메모/태그' 상세 문자열
    """
    lines = [
        f"  id       : {tx.id}",
        f"  날짜     : {tx.date}",
        f"  구분     : {type_label(tx.type)}({tx.type})",
        f"  카테고리 : {tx.category}",
        f"  금액     : {money(tx.amount)}",
        f"  메모     : {tx.memo or '-'}",
        f"  태그     : {', '.join(tx.tags) or '-'}",
    ]
    return "\n".join(lines)


def print_error(message: str, hint: str = "") -> None:
    """오류를 '[오류] 원인' + '[힌트] 해결법' 형식으로 stderr에 출력한다.

    Args:
        message: 오류 원인
        hint: 해결 방법 (없으면 힌트 줄을 생략)
    """
    print(f"[오류] {message}", file=sys.stderr)
    if hint:
        print(f"[힌트] {hint}", file=sys.stderr)
