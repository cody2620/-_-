"""월 예산 서비스.

[파일 역할]
- 월 예산 저장(budget set), 조회(budget show, summary), 목록(budget list)을 처리한다.
- 저장 시각(updated_at)을 기록하고, 예산이 없을 때의 오류 메시지를 만든다.
"""

from typing import List, Optional, Tuple

from ..core.errors import NotFoundError
from ..models.budget import Budget
from ..storage.budget_repository import BudgetRepository
from ._clock import now_iso


class BudgetService:
    """월 예산 비즈니스 로직."""

    def __init__(self, repository: BudgetRepository) -> None:
        """예산 저장소를 주입받는다."""
        self._repo = repository

    def set(self, month: str, amount: int) -> Tuple[Budget, Optional[Budget]]:
        """월 예산을 저장한다. (있으면 덮어쓰기)

        Args:
            month: YYYY-MM
            amount: 양의 정수 금액
        Returns:
            (저장된 예산, 이전 예산 또는 None)
        """
        budget = Budget(month=month, amount=amount, updated_at=now_iso())
        previous = self._repo.upsert(budget)
        return budget, previous

    def find(self, month: str) -> Optional[Budget]:
        """해당 월 예산을 반환한다. 없으면 None. (summary 처럼 '없어도 되는' 곳에서 사용)"""
        return self._repo.get(month)

    def get(self, month: str) -> Budget:
        """해당 월 예산을 반환한다. 없으면 오류. (budget show 처럼 '반드시 있어야 하는' 곳에서 사용)

        Raises:
            NotFoundError: 예산이 설정되지 않은 달 (설정 방법을 힌트로 안내)
        """
        budget = self._repo.get(month)
        if budget is None:
            raise NotFoundError(f"{month} 예산이 설정되어 있지 않습니다.",
                                f"python -m budget_app budget set --month {month} --amount <금액> 으로 설정하세요.")
        return budget

    def list_all(self) -> List[Budget]:
        """설정된 모든 월 예산을 월 순서로 반환한다."""
        return self._repo.list_all()
