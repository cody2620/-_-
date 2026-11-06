"""카테고리 관리 서비스 (add / list / remove).

[파일 역할]
- 카테고리가 비어 있을 때 기본 카테고리 생성 (요구사항 3 - 안 A)
- 카테고리 존재 확인 (add/update/search/import 에서 사용)
- 중복 추가 방지
- 사용 중인 카테고리 삭제 시 삭제를 막거나, 대체 카테고리로 거래를 옮긴 뒤 삭제 (요구사항 10)
"""

from typing import Dict, List, Optional, Tuple

from .. import config
from ..core.errors import ConflictError, NotFoundError, ValidationError
from ..models.category import Category
from ..storage.category_repository import CategoryRepository
from ..storage.transaction_repository import TransactionRepository
from ._clock import now_iso


class CategoryService:
    """카테고리 비즈니스 로직.

    [역할] 카테고리 저장소뿐 아니라 거래 저장소도 사용한다.
    (사용 중인지 확인하고, 대체 카테고리로 거래를 옮기기 위해)
    """

    def __init__(self, categories: CategoryRepository, transactions: TransactionRepository) -> None:
        """카테고리 저장소와 거래 저장소를 주입받는다."""
        self._categories = categories
        self._transactions = transactions

    def seed_defaults_if_empty(self) -> Optional[List[str]]:
        """카테고리 파일이 비어 있으면 기본 카테고리를 생성한다. (요구사항 3 - 안 A)

        Returns:
            생성한 카테고리 이름 목록. 이미 카테고리가 있으면 None.
        """
        if not self._categories.is_empty():
            return None
        created = now_iso()
        self._categories.add_many(Category(name, created) for name in config.DEFAULT_CATEGORIES)
        return list(config.DEFAULT_CATEGORIES)

    def names(self) -> List[str]:
        """등록된 카테고리 이름 목록을 반환한다."""
        return self._categories.names()

    def list_with_usage(self) -> List[Tuple[str, int]]:
        """카테고리별 사용 거래 건수를 함께 반환한다. (category list 출력용)

        Returns:
            [(카테고리 이름, 사용 건수), ...]
        """
        usage: Dict[str, int] = self._transactions.count_by_category()
        return [(name, usage.get(name, 0)) for name in self.names()]

    def ensure_exists(self, name: str) -> None:
        """카테고리가 등록되어 있는지 확인한다.

        Raises:
            NotFoundError: 등록되지 않은 카테고리
                (등록된 목록과 category add 명령을 힌트로 안내)
        """
        names = self.names()
        if name not in names:
            raise NotFoundError(f"등록되지 않은 카테고리입니다: '{name}'",
                                f"등록된 카테고리: {', '.join(names) or '(없음)'}"
                                f" / 새로 등록하려면: python -m budget_app category add --name {name}")

    def add(self, name: str) -> Category:
        """카테고리를 추가한다.

        Returns:
            추가된 Category
        Raises:
            ConflictError: 이미 등록된 이름
        """
        if self._categories.exists(name):
            raise ConflictError(f"이미 등록된 카테고리입니다: '{name}'", "category list 로 목록을 확인하세요.")
        category = Category(name=name, created_at=now_iso())
        self._categories.add(category)
        return category

    def remove(self, name: str, replacement: Optional[str] = None) -> int:
        """카테고리를 삭제한다.

        [역할]
        - 사용 중이 아니면 바로 삭제한다.
        - 사용 중인데 replacement 가 없으면 삭제를 막는다.
        - replacement 가 있으면 해당 거래들의 카테고리를 replacement 로 옮긴 뒤 삭제한다.

        Args:
            name: 삭제할 카테고리
            replacement: 대체 카테고리 (--replace)
        Returns:
            대체 카테고리로 옮긴 거래 건수
        Raises:
            NotFoundError: 없는 카테고리 / 없는 대체 카테고리
            ConflictError: 사용 중인데 대체 카테고리가 없음
            ValidationError: 대체 카테고리가 삭제할 카테고리와 같음
        """
        self.ensure_exists(name)
        in_use = self._transactions.count_by_category().get(name, 0)
        moved = 0
        if in_use:
            if replacement is None:
                raise ConflictError(
                    f"'{name}' 카테고리를 사용하는 거래가 {in_use}건 있어 삭제할 수 없습니다.",
                    f"대체 카테고리를 지정하세요: python -m budget_app category remove --name {name} --replace <다른카테고리>")
            if replacement == name:
                raise ValidationError("대체 카테고리가 삭제할 카테고리와 같습니다.", "다른 카테고리를 --replace 로 지정하세요.")
            self.ensure_exists(replacement)
            moved = self._transactions.reassign_category(name, replacement)
        elif replacement is not None and replacement != name:
            self.ensure_exists(replacement)
        self._categories.remove(name)
        return moved
