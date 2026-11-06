"""거래 서비스: 추가/조회/검색/수정/삭제.

[파일 역할]
- 새 거래 id 생성(8자리, 중복 없음)과 생성 시각 기록
- 카테고리 존재 확인 후 저장
- 최신순 조회/검색 (제너레이터 스트리밍 + heapq 로 필요한 만큼만 메모리 유지)
- 없는 id 처리('없는 데이터' 오류)
- 지정한 필드만 수정하는 update, delete
"""

import heapq
import uuid
from dataclasses import replace
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from ..core.errors import NotFoundError, ValidationError
from ..models.filters import TransactionFilter
from ..models.transaction import Transaction
from ..storage.transaction_repository import TransactionRepository
from ._clock import now_iso
from .category_service import CategoryService

UPDATABLE_FIELDS = ("date", "type", "category", "amount", "memo", "tags")


def _new_id(taken: Set[str]) -> str:
    """기존 id와 겹치지 않는 8자리 16진수 id를 만든다.

    [역할] 만든 id는 taken 에 바로 추가해, 한 번에 여러 건을 만들 때(import)도
    서로 겹치지 않게 한다.

    Args:
        taken: 이미 사용 중인 id 집합 (함수 안에서 갱신됨)
    Returns:
        새 id (예: '85df636e')
    """
    while True:
        candidate = uuid.uuid4().hex[:8]
        if candidate not in taken:
            taken.add(candidate)
            return candidate


class TransactionService:
    """거래 비즈니스 로직."""

    def __init__(self, repository: TransactionRepository, categories: CategoryService) -> None:
        """거래 저장소와 카테고리 서비스(카테고리 존재 확인용)를 주입받는다."""
        self._repo = repository
        self._categories = categories

    # ---- 생성 -------------------------------------------------------------
    def create(self, *, date: str, type: str, category: str, amount: int,
               memo: str = "", tags: Optional[List[str]] = None) -> Transaction:
        """거래 1건을 만들어 저장한다. (add 명령)

        [역할] 카테고리 존재 확인 → 중복 없는 id 생성 → 생성 시각 기록 → 파일에 추가.
        (날짜/금액/타입 형식 검증은 입력 단계(validators)에서 이미 끝난 상태)

        Returns:
            저장된 Transaction (id 포함)
        Raises:
            NotFoundError: 등록되지 않은 카테고리
        """
        self._categories.ensure_exists(category)
        taken = set(self._repo.iter_ids())
        tx = Transaction(id=_new_id(taken), type=type, date=date, amount=amount, category=category,
                         memo=memo, tags=list(tags or []), created_at=now_iso())
        self._repo.add(tx)
        return tx

    def create_many(self, rows: Iterable[Dict[str, Any]]) -> int:
        """검증이 끝난 필드 dict 들을 스트리밍으로 일괄 저장한다. (import 용)

        Args:
            rows: {date, type, category, amount, memo, tags} dict 들의 iterable
        Returns:
            저장한 건수
        """
        taken = set(self._repo.iter_ids())

        def build() -> Iterator[Transaction]:
            """필드 dict 마다 새 id 와 생성 시각을 붙여 Transaction 을 하나씩 내보내는 제너레이터."""
            for row in rows:
                yield Transaction(id=_new_id(taken), created_at=now_iso(), **row)

        return self._repo.add_many(build())

    # ---- 조회/검색 ----------------------------------------------------------
    def iter_matching(self, flt: TransactionFilter) -> Iterator[Transaction]:
        """조건에 맞는 거래를 파일 순서대로 하나씩 내보내는 제너레이터.

        [역할] summary 집계와 export 에서 전체를 메모리에 올리지 않고 처리할 때 사용한다.

        Args:
            flt: 검색 조건
        """
        return (tx for tx in self._repo.iter_all() if flt.matches(tx))

    def recent(self, limit: int) -> List[Transaction]:
        """최신순 상위 limit 건을 반환한다. (list 명령)

        [역할] heapq.nlargest 가 제너레이터를 한 건씩 소비하며 상위 limit 건만
        메모리에 유지하므로, 파일이 커도 메모리 사용량이 limit 에 비례한다.

        Returns:
            최신순 정렬된 Transaction 리스트
        """
        return heapq.nlargest(limit, self._repo.iter_all(), key=Transaction.sort_key)

    def search(self, flt: TransactionFilter, limit: Optional[int] = None) -> List[Transaction]:
        """조건에 맞는 거래를 최신순으로 반환한다. (search 명령)

        [역할] 파일은 스트리밍으로 필터링하고, 조건에 맞는 거래만 정렬한다.
        limit 이 있으면 heapq 로 상위 limit 건만 유지한다.

        Args:
            flt: 검색 조건
            limit: 최대 건수 (None 이면 전체)
        Returns:
            최신순 정렬된 Transaction 리스트
        """
        matches = self.iter_matching(flt)
        if limit is not None:
            return heapq.nlargest(limit, matches, key=Transaction.sort_key)
        return sorted(matches, key=Transaction.sort_key, reverse=True)

    def get(self, tx_id: str) -> Transaction:
        """id로 거래를 가져온다.

        Raises:
            NotFoundError: 없는 id ('없는 데이터', 종료 코드 3)
        """
        tx = self._repo.find(tx_id)
        if tx is None:
            raise NotFoundError(f"id '{tx_id}' 거래를 찾을 수 없습니다. (없는 데이터)",
                                "python -m budget_app list 또는 search 로 올바른 id를 확인하세요.")
        return tx

    # ---- 수정/삭제 ----------------------------------------------------------
    def update(self, tx_id: str, changes: Dict[str, Any]) -> Tuple[Transaction, Transaction]:
        """거래에서 지정한 필드만 수정한다. (update 명령)

        [역할]
        - 값이 None 인 항목(옵션 미지정)은 무시한다.
        - 바꿀 카테고리가 등록되어 있는지 확인한다.
        - 새 값이 기존과 같으면 파일을 다시 쓰지 않는다.

        Args:
            tx_id: 수정할 거래 id
            changes: {필드명: 새 값}
        Returns:
            (수정 전 Transaction, 수정 후 Transaction)
        Raises:
            ValidationError: 수정할 항목이 없음
            NotFoundError: 없는 id 또는 없는 카테고리
        """
        changes = {k: v for k, v in changes.items() if k in UPDATABLE_FIELDS and v is not None}
        if not changes:
            raise ValidationError("수정할 항목이 지정되지 않았습니다.",
                                  "--date / --type / --category / --amount / --memo / --tags 중 하나 이상 지정하세요.")
        old = self.get(tx_id)
        if "category" in changes:
            self._categories.ensure_exists(changes["category"])
        new = replace(old, **changes)
        if new != old:
            self._repo.replace(new)
        return old, new

    def delete(self, tx_id: str) -> Transaction:
        """거래를 삭제한다. (delete 명령)

        Returns:
            삭제된 Transaction (화면에 보여주기 위해)
        Raises:
            NotFoundError: 없는 id
        """
        tx = self.get(tx_id)
        self._repo.delete(tx_id)
        return tx
