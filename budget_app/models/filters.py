"""거래 검색 조건(TransactionFilter).

[파일 역할]
- search/summary/export 가 공통으로 쓰는 '거래 조건'을 하나의 객체로 표현한다.
- 조건이 None/빈 값이면 그 조건은 검사하지 않는다. 지정된 조건은 모두 만족(AND)해야 한다.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ..core.errors import ValidationError
from .transaction import Transaction


@dataclass
class TransactionFilter:
    """거래 검색 조건 묶음.

    Attributes:
        date_from / date_to: 기간 (양 끝 포함)
        month: YYYY-MM (summary, export --month)
        category / type: 정확히 일치
        keyword: 메모 부분 일치 (대소문자 무시)
        tags: 모두 포함해야 일치
    """

    date_from: Optional[str] = None   # YYYY-MM-DD (포함)
    date_to: Optional[str] = None     # YYYY-MM-DD (포함)
    month: Optional[str] = None       # YYYY-MM
    category: Optional[str] = None
    type: Optional[str] = None
    keyword: Optional[str] = None     # 메모 부분 일치 (대소문자 무시)
    tags: List[str] = field(default_factory=list)  # 모두 포함해야 일치

    def __post_init__(self) -> None:
        """객체 생성 직후 조건을 검사한다. (--from 이 --to 보다 늦으면 ValidationError)"""
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(f"기간이 올바르지 않습니다: --from {self.date_from} > --to {self.date_to}",
                                  "--from 날짜가 --to 날짜보다 앞서거나 같아야 합니다.")

    def matches(self, tx: Transaction) -> bool:
        """거래 1건이 모든 조건을 만족하는지 검사한다.

        Args:
            tx: 검사할 Transaction
        Returns:
            모두 만족하면 True
        """
        if self.month and not tx.date.startswith(self.month + "-"):
            return False
        if self.date_from and tx.date < self.date_from:
            return False
        if self.date_to and tx.date > self.date_to:
            return False
        if self.category and tx.category != self.category:
            return False
        if self.type and tx.type != self.type:
            return False
        if self.keyword and self.keyword.lower() not in tx.memo.lower():
            return False
        if self.tags and not all(tag in tx.tags for tag in self.tags):
            return False
        return True
