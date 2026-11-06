"""거래 저장소: transactions.jsonl 읽기/쓰기.

[파일 역할]
- JsonlFile 위에서 Transaction 객체 단위로 저장/조회/수정/삭제를 제공한다.
- 조회는 모두 제너레이터 기반 스트리밍이다. (파일 전체를 한 번에 로드하지 않음)
- 수정/삭제/카테고리 일괄 변경은 '전체 재작성 + 원자적 교체'로 처리한다.
- 검증 규칙(카테고리 존재 등)은 여기서 하지 않고 Service 계층이 담당한다.
"""

from collections import Counter
from dataclasses import replace as dc_replace
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

from ..core.errors import DataFileError
from ..models.transaction import Transaction
from .jsonl_file import JsonlFile


class TransactionRepository:
    """거래 내역 파일 저장소."""

    def __init__(self, path: Path) -> None:
        """transactions.jsonl 경로로 JsonlFile 을 준비한다."""
        self._file = JsonlFile(path)

    @property
    def path(self) -> Path:
        """저장 파일 경로. (안내/오류 메시지에 사용)"""
        return self._file.path

    def ensure_exists(self) -> bool:
        """저장 파일이 없으면 만든다. 새로 만들었으면 True."""
        return self._file.ensure_exists()

    def iter_all(self) -> Iterator[Transaction]:
        """저장된 거래를 한 건씩 생성하는 제너레이터. (list/search/summary/export 의 기반)

        Yields:
            Transaction
        Raises:
            DataFileError: 해석할 수 없는 줄이 있으면 줄 번호와 함께 발생
        """
        for lineno, record in self._file.iter_records():
            try:
                yield Transaction.from_dict(record)
            except ValueError as exc:
                raise DataFileError(f"{self.path.name} {lineno}번째 줄의 거래를 해석할 수 없습니다: {exc}",
                                    f"{self.path} 파일의 {lineno}번째 줄을 고치거나 삭제하세요.") from None

    def iter_ids(self) -> Iterator[str]:
        """저장된 거래 id 만 한 건씩 생성한다. (새 id 중복 확인용)"""
        return (tx.id for tx in self.iter_all())

    def find(self, tx_id: str) -> Optional[Transaction]:
        """id로 거래를 찾는다. 찾는 즉시 읽기를 멈춘다.

        Returns:
            Transaction, 없으면 None
        """
        return next((tx for tx in self.iter_all() if tx.id == tx_id), None)

    def add(self, tx: Transaction) -> None:
        """거래 1건을 파일 끝에 추가한다."""
        self._file.append(tx.to_dict())

    def add_many(self, txs: Iterable[Transaction]) -> int:
        """여러 거래를 파일 끝에 추가한다. (CSV import 용, 제너레이터 입력 가능)

        Returns:
            추가한 건수
        """
        return self._file.append_many(tx.to_dict() for tx in txs)

    def _rewrite(self, transform: Callable[[Transaction], Optional[Transaction]]) -> int:
        """모든 거래에 transform 을 적용해 파일을 재작성한다. (수정/삭제 공통 로직)

        [역할] 원본을 한 줄씩 읽으며 transform 결과를 임시 파일에 쓰고 원자적으로 교체한다.
        - transform 이 같은 객체를 반환 → 그대로 유지
        - 다른 객체를 반환 → 변경
        - None 을 반환 → 삭제

        Args:
            transform: Transaction → Transaction 또는 None
        Returns:
            변경/삭제된 건수
        """
        changed = 0

        def records():
            """원본 거래를 스트리밍으로 읽어 transform 을 적용한 dict 를 내보내는 제너레이터.
            (변경 건수는 바깥 변수 changed 에 기록한다)
            """
            nonlocal changed
            for tx in self.iter_all():
                new_tx = transform(tx)
                if new_tx is not tx:
                    changed += 1
                if new_tx is not None:
                    yield new_tx.to_dict()

        self._file.rewrite(records())
        return changed

    def replace(self, updated: Transaction) -> bool:
        """같은 id의 거래를 updated 로 교체한다. (update 명령)

        Returns:
            교체했으면 True
        """
        return self._rewrite(lambda tx: updated if tx.id == updated.id else tx) > 0

    def delete(self, tx_id: str) -> bool:
        """id에 해당하는 거래를 삭제한다. (delete 명령)

        Returns:
            삭제했으면 True
        """
        return self._rewrite(lambda tx: None if tx.id == tx_id else tx) > 0

    def reassign_category(self, old: str, new: str) -> int:
        """old 카테고리를 쓰는 모든 거래의 카테고리를 new 로 바꾼다.
        (category remove --replace 에서 사용)

        Returns:
            변경된 거래 건수
        """
        return self._rewrite(lambda tx: dc_replace(tx, category=new) if tx.category == old else tx)

    def count_by_category(self) -> Counter:
        """카테고리별 거래 건수를 센다. (category list 표시, 사용 중 카테고리 판단)

        Returns:
            Counter({카테고리: 건수})
        """
        return Counter(tx.category for tx in self.iter_all())
