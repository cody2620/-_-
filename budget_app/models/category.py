"""카테고리(Category) 데이터 모델.

[파일 역할] 카테고리 1개를 dataclass로 정의하고,
저장 파일의 JSON 객체 ↔ Category 변환을 담당한다.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Category:
    """카테고리 1개. (name: 소문자 이름, created_at: 생성 시각) 불변 객체."""

    name: str
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """저장용 dict로 변환한다."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        """저장 파일에서 읽은 dict를 Category로 변환한다. (이름은 소문자로 정규화)

        Raises:
            ValueError: name 누락 또는 빈 이름
        """
        try:
            name = str(data["name"]).strip().lower()
        except KeyError:
            raise ValueError("필수 필드 누락: name") from None
        if not name:
            raise ValueError("name이 비어 있음")
        return cls(name=name, created_at=str(data.get("created_at") or ""))
