"""예산 저장소: budgets.jsonl 읽기/쓰기.

[파일 역할]
- 월별 예산(한 달에 1건)을 조회/저장한다.
- 저장 시 같은 월이 있으면 교체하고, 월 순서로 정렬해 원자적으로 재작성한다.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..core.errors import DataFileError
from ..models.budget import Budget
from .jsonl_file import JsonlFile


class BudgetRepository:
    """월 예산 파일 저장소."""

    def __init__(self, path: Path) -> None:
        """budgets.jsonl 경로로 JsonlFile 을 준비한다."""
        self._file = JsonlFile(path)

    @property
    def path(self) -> Path:
        """저장 파일 경로. (안내/오류 메시지에 사용)"""
        return self._file.path

    def ensure_exists(self) -> bool:
        """저장 파일이 없으면 만든다. 새로 만들었으면 True."""
        return self._file.ensure_exists()

    def _load(self) -> Dict[str, Budget]:
        """모든 예산을 {월: Budget} 형태로 읽는다.

        [역할] 같은 월이 여러 줄이면 마지막 값을 사용한다.

        Raises:
            DataFileError: 해석할 수 없는 줄이 있으면 줄 번호와 함께 발생
        """
        budgets: Dict[str, Budget] = {}
        for lineno, record in self._file.iter_records():
            try:
                budget = Budget.from_dict(record)
            except ValueError as exc:
                raise DataFileError(f"{self.path.name} {lineno}번째 줄의 예산을 해석할 수 없습니다: {exc}",
                                    f"{self.path} 파일의 {lineno}번째 줄을 고치거나 삭제하세요.") from None
            budgets[budget.month] = budget  # 같은 월이 여러 번이면 마지막 값 우선
        return budgets

    def list_all(self) -> List[Budget]:
        """모든 예산을 월 순서로 반환한다."""
        return sorted(self._load().values(), key=lambda b: b.month)

    def get(self, month: str) -> Optional[Budget]:
        """해당 월의 예산을 반환한다. 없으면 None."""
        return self._load().get(month)

    def upsert(self, budget: Budget) -> Optional[Budget]:
        """월 예산을 저장한다. 같은 월이 있으면 교체한다. (원자적 재작성)

        Args:
            budget: 저장할 예산
        Returns:
            이전 예산 (없었으면 None)
        """
        budgets = self._load()
        previous = budgets.get(budget.month)
        budgets[budget.month] = budget
        self._file.rewrite(b.to_dict() for b in sorted(budgets.values(), key=lambda b: b.month))
        return previous
