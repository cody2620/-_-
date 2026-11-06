"""저장소/서비스 조립 및 초기 실행 처리.

[파일 역할]
- 저장 폴더(--data-dir)를 준비하고, 저장 파일 3개(transactions/categories/budgets)가
  없으면 자동 생성한다.
- 카테고리 파일이 비어 있으면 기본 카테고리를 만든다. (요구사항 3 - 안 A)
- Repository(파일 I/O)와 Service(비즈니스 로직) 객체를 만들어 AppContext 하나로 묶어
  명령 handler들에게 전달한다. (의존성 조립 담당)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from . import config
from .core.errors import StorageError
from .services.budget_service import BudgetService
from .services.category_service import CategoryService
from .services.csv_service import CsvService
from .services.summary_service import SummaryService
from .services.transaction_service import TransactionService
from .storage.budget_repository import BudgetRepository
from .storage.category_repository import CategoryRepository
from .storage.transaction_repository import TransactionRepository


@dataclass
class AppContext:
    """명령 실행에 필요한 서비스 객체 묶음.

    [역할] 각 명령 handler(args, ctx)가 ctx.transactions, ctx.categories 처럼
    필요한 서비스를 꺼내 쓸 수 있게 한다.

    Attributes:
        data_dir: 실제 저장 폴더 경로
        transactions: 거래 추가/조회/검색/수정/삭제 서비스
        categories: 카테고리 관리 서비스
        budgets: 월 예산 서비스
        summary: 월별 요약 서비스
        csv: CSV import/export 서비스
    """

    data_dir: Path
    transactions: TransactionService
    categories: CategoryService
    budgets: BudgetService
    summary: SummaryService
    csv: CsvService


def build_context(data_dir: str) -> Tuple[AppContext, List[str]]:
    """저장 폴더를 준비하고 AppContext를 만든다.

    [역할] 프로그램 시작 시 1번 호출된다.
    1) 저장 폴더가 없으면 생성, 경로가 파일이면 오류
    2) 저장 파일 3개가 없으면 빈 파일 생성
    3) 카테고리가 비어 있으면 기본 카테고리 생성
    4) Repository → Service 순서로 객체를 만들어 AppContext로 묶음

    Args:
        data_dir: 저장 폴더 경로 (--data-dir 값)
    Returns:
        (AppContext, 사용자에게 보여줄 [안내] 메시지 목록)
    Raises:
        StorageError: 폴더/파일을 만들 수 없거나 경로가 잘못된 경우
    """
    root = Path(data_dir).expanduser()
    notices: List[str] = []
    if root.exists() and not root.is_dir():
        raise StorageError(f"저장 폴더 경로가 파일입니다: {root}", "--data-dir 로 폴더 경로를 지정하세요.")
    if not root.exists():
        try:
            root.mkdir(parents=True)
        except OSError as exc:
            raise StorageError(f"저장 폴더를 만들 수 없습니다: {root} ({exc.strerror})",
                               "권한을 확인하거나 --data-dir 로 다른 폴더를 지정하세요.") from None
        notices.append(f"저장 폴더를 새로 만들었습니다: {root}")

    tx_repo = TransactionRepository(root / config.TRANSACTIONS_FILE)
    cat_repo = CategoryRepository(root / config.CATEGORIES_FILE)
    budget_repo = BudgetRepository(root / config.BUDGETS_FILE)
    for repo in (tx_repo, cat_repo, budget_repo):
        if repo.ensure_exists():
            notices.append(f"저장 파일을 초기화했습니다: {repo.path}")

    categories = CategoryService(cat_repo, tx_repo)
    seeded = categories.seed_defaults_if_empty()
    if seeded:
        notices.append(f"카테고리가 비어 있어 기본 카테고리를 생성했습니다: {', '.join(seeded)}")

    transactions = TransactionService(tx_repo, categories)
    budgets = BudgetService(budget_repo)
    ctx = AppContext(
        data_dir=root,
        transactions=transactions,
        categories=categories,
        budgets=budgets,
        summary=SummaryService(transactions, budgets),
        csv=CsvService(transactions, categories),
    )
    return ctx, notices
