"""거래 내역(Transaction) 데이터 모델.

[파일 역할]
- 거래 1건의 필드를 dataclass로 정의한다. (요구사항 2)
  id(유일), type(income/expense), date(YYYY-MM-DD), amount(양수),
  category, memo(선택), tags(선택), created_at(정렬용 생성 시각)
- 저장 파일의 JSON 객체 ↔ Transaction 변환을 담당한다.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class Transaction:
    """거래 내역 1건.

    [역할] frozen=True 로 불변 객체이다. 값을 바꿀 때는 dataclasses.replace()로
    새 객체를 만든다. (실수로 원본이 바뀌는 것을 방지)
    """

    id: str
    type: str          # income / expense
    date: str          # YYYY-MM-DD
    amount: int        # 양수
    category: str
    memo: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""   # 같은 날짜끼리 최신순 정렬을 위한 생성 시각(ISO)

    def to_dict(self) -> Dict[str, Any]:
        """저장용 dict로 변환한다. (JSONL 한 줄로 쓰기 위해 사용)"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """저장 파일에서 읽은 dict를 Transaction으로 변환한다.

        [역할] 필수 필드 누락, 양수가 아닌 금액, 잘못된 type, 리스트가 아닌 tags 를
        검사해 손상된 데이터가 프로그램 안으로 들어오지 않게 막는다.

        Args:
            data: JSON 객체(dict)
        Returns:
            Transaction
        Raises:
            ValueError: 필드 누락 또는 형식 오류 (Repository가 줄 번호와 함께 DataFileError로 바꿈)
        """
        try:
            amount = data["amount"]
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                raise ValueError(f"amount가 양의 정수가 아님({amount!r})")
            if data["type"] not in ("income", "expense"):
                raise ValueError(f"type이 올바르지 않음({data['type']!r})")
            tags = data.get("tags") or []
            if not isinstance(tags, list):
                raise ValueError("tags가 리스트가 아님")
            return cls(
                id=str(data["id"]),
                type=data["type"],
                date=str(data["date"]),
                amount=amount,
                category=str(data["category"]),
                memo=str(data.get("memo") or ""),
                tags=[str(t) for t in tags],
                created_at=str(data.get("created_at") or ""),
            )
        except KeyError as exc:
            raise ValueError(f"필수 필드 누락: {exc.args[0]}") from None

    def sort_key(self) -> Tuple[str, str, str]:
        """최신순 정렬 기준값을 반환한다.

        [역할] 날짜가 같으면 먼저 입력한 거래보다 나중에 입력한 거래가 최신이 되도록
        (date, created_at, id) 순으로 비교한다.
        """
        return (self.date, self.created_at, self.id)
