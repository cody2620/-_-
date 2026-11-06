"""월 예산(Budget) 데이터 모델.

[파일 역할] 월별 예산 1건을 dataclass로 정의하고,
저장 파일의 JSON 객체 ↔ Budget 변환을 담당한다.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Budget:
    """월 예산 1건. (month: YYYY-MM, amount: 양수, updated_at: 마지막 저장 시각) 불변 객체."""

    month: str       # YYYY-MM
    amount: int      # 양수
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """저장용 dict로 변환한다."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        """저장 파일에서 읽은 dict를 Budget으로 변환한다.

        Raises:
            ValueError: 필드 누락 또는 금액이 양의 정수가 아님
        """
        try:
            amount = data["amount"]
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                raise ValueError(f"amount가 양의 정수가 아님({amount!r})")
            return cls(month=str(data["month"]), amount=amount, updated_at=str(data.get("updated_at") or ""))
        except KeyError as exc:
            raise ValueError(f"필수 필드 누락: {exc.args[0]}") from None
