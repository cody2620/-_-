"""카테고리 저장소: categories.jsonl 읽기/쓰기.

[파일 역할]
- 카테고리 목록 조회/추가/삭제를 제공한다.
- 카테고리는 개수가 적으므로 목록 전체를 읽어 처리한다.
- 같은 이름이 중복 저장되어 있어도 한 번만 보이게 한다.
"""

from pathlib import Path
from typing import Iterable, List

from ..core.errors import DataFileError
from ..models.category import Category
from .jsonl_file import JsonlFile


class CategoryRepository:
    """카테고리 파일 저장소."""

    def __init__(self, path: Path) -> None:
        """categories.jsonl 경로로 JsonlFile 을 준비한다."""
        self._file = JsonlFile(path)

    @property
    def path(self) -> Path:
        """저장 파일 경로. (안내/오류 메시지에 사용)"""
        return self._file.path

    def ensure_exists(self) -> bool:
        """저장 파일이 없으면 만든다. 새로 만들었으면 True."""
        return self._file.ensure_exists()

    def is_empty(self) -> bool:
        """등록된 카테고리가 하나도 없는지 확인한다. (기본 카테고리 생성 판단용)"""
        return self._file.is_empty()

    def list(self) -> List[Category]:
        """카테고리 목록을 파일 순서대로 반환한다. (중복 이름은 첫 번째만)

        Raises:
            DataFileError: 해석할 수 없는 줄이 있으면 줄 번호와 함께 발생
        """
        categories: List[Category] = []
        seen = set()
        for lineno, record in self._file.iter_records():
            try:
                category = Category.from_dict(record)
            except ValueError as exc:
                raise DataFileError(f"{self.path.name} {lineno}번째 줄의 카테고리를 해석할 수 없습니다: {exc}",
                                    f"{self.path} 파일의 {lineno}번째 줄을 고치거나 삭제하세요.") from None
            if category.name not in seen:
                seen.add(category.name)
                categories.append(category)
        return categories

    def names(self) -> List[str]:
        """카테고리 이름 목록만 반환한다."""
        return [c.name for c in self.list()]

    def exists(self, name: str) -> bool:
        """해당 이름의 카테고리가 등록되어 있는지 확인한다."""
        return name in self.names()

    def add(self, category: Category) -> None:
        """카테고리 1개를 파일 끝에 추가한다. (중복 검사는 Service 가 담당)"""
        self._file.append(category.to_dict())

    def add_many(self, categories: Iterable[Category]) -> int:
        """여러 카테고리를 한 번에 추가한다. (기본 카테고리 생성용)

        Returns:
            추가한 개수
        """
        return self._file.append_many(c.to_dict() for c in categories)

    def remove(self, name: str) -> None:
        """해당 이름의 카테고리를 빼고 파일을 재작성한다. (원자적 교체)"""
        remaining = [c for c in self.list() if c.name != name]
        self._file.rewrite(c.to_dict() for c in remaining)
