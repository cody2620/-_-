"""월별 요약 서비스.

[파일 역할]
- 해당 월 거래를 스트리밍으로 읽으며 총수입/총지출/건수, 카테고리별 지출을 집계한다.
- 카테고리별 지출 TOP N 을 계산한다. (요구사항 8)
- 예산이 있으면 사용률(%)과 초과 여부를 계산한다. (요구사항 9)
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..models.budget import Budget
from ..models.filters import TransactionFilter
from .budget_service import BudgetService
from .transaction_service import TransactionService


@dataclass
class MonthlySummary:
    """월별 요약 결과.

    Attributes:
        month: YYYY-MM
        income / expense: 총수입 / 총지출
        income_count / expense_count: 수입 / 지출 건수
        top_categories: [(카테고리, 지출 합계), ...] 지출 많은 순
        budget: 해당 월 예산 (없으면 None)
    """

    month: str
    income: int = 0
    expense: int = 0
    income_count: int = 0
    expense_count: int = 0
    top_categories: List[Tuple[str, int]] = field(default_factory=list)
    budget: Optional[Budget] = None

    @property
    def balance(self) -> int:
        """잔액 = 총수입 - 총지출"""
        return self.income - self.expense

    @property
    def has_data(self) -> bool:
        """해당 월에 거래가 1건 이상 있는지. (False 면 '데이터 없음' 출력)"""
        return (self.income_count + self.expense_count) > 0

    @property
    def usage_rate(self) -> Optional[float]:
        """예산 대비 사용률(%) = 총지출 / 예산 × 100. 예산이 없으면 None."""
        if self.budget is None:
            return None
        return self.expense / self.budget.amount * 100

    @property
    def over_budget(self) -> bool:
        """예산 초과 여부. (예산이 있고 총지출이 예산보다 크면 True)"""
        return self.budget is not None and self.expense > self.budget.amount


class SummaryService:
    """월별 요약 비즈니스 로직."""

    def __init__(self, transactions: TransactionService, budgets: BudgetService) -> None:
        """거래 서비스와 예산 서비스를 주입받는다."""
        self._transactions = transactions
        self._budgets = budgets

    def summarize(self, month: str, top: int) -> MonthlySummary:
        """해당 월의 요약을 계산한다.

        [역할] 해당 월 거래만 스트리밍으로 읽어 합계를 낸다(파일 전체를 메모리에 올리지 않음).
        TOP N 은 지출 금액 내림차순, 같으면 카테고리 이름순이다.

        Args:
            month: YYYY-MM
            top: 카테고리별 지출 상위 개수
        Returns:
            MonthlySummary
        """
        summary = MonthlySummary(month=month, budget=self._budgets.find(month))
        expense_by_category: Counter = Counter()
        # 해당 월 거래만 스트리밍으로 집계 (파일 전체를 메모리에 올리지 않음)
        for tx in self._transactions.iter_matching(TransactionFilter(month=month)):
            if tx.type == "income":
                summary.income += tx.amount
                summary.income_count += 1
            else:
                summary.expense += tx.amount
                summary.expense_count += 1
                expense_by_category[tx.category] += tx.amount
        summary.top_categories = sorted(expense_by_category.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
        return summary
