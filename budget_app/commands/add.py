"""add 명령: 거래 추가 (대화형 입력).

[파일 역할]
- `python -m budget_app add` 실행 시 날짜/타입/카테고리/금액/메모/태그를
  input()으로 차례로 입력받는다. (요구사항 4)
- 잘못된 값은 이유를 보여주고 다시 입력받는다.
- 등록되지 않은 카테고리는 안내 후 등록을 유도한다.
- 저장이 끝나면 생성된 거래 id를 출력한다.
"""

from datetime import date

from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import describe
from ..core.prompts import ask, confirm
from ._common import add_command


def register(subparsers, common) -> None:
    """add 하위 명령을 등록한다. (옵션 없음, 대화형으로만 입력)

    Args:
        subparsers: 최상위 파서의 하위 명령 묶음
        common: 공통 옵션 파서
    """
    parser = add_command(
        subparsers, "add", common,
        help="거래 추가 (대화형 입력)",
        description="날짜/타입/카테고리/금액/메모/태그를 차례로 입력받아 거래를 저장합니다.\n"
                    "잘못된 값을 입력하면 이유를 보여주고 다시 입력받습니다.",
        examples="  python -m budget_app add")
    parser.set_defaults(handler=handle)


def _ask_category(categories) -> str:
    """카테고리를 대화형으로 입력받는다.

    [역할]
    - 매번 등록된 카테고리 목록을 보여준다.
    - 목록에 없는 이름이면 "새로 등록할까요? [y/N]"를 물어
      y → 즉시 등록 후 사용, n → 다시 입력받는다.

    Args:
        categories: CategoryService
    Returns:
        등록된(또는 방금 등록한) 카테고리 이름
    """
    while True:
        names = categories.names()
        print(f"  (등록된 카테고리: {', '.join(names)})")
        name = ask("카테고리: ", v.parse_category_name)
        if name in names:
            return name
        print(f"  ! '{name}' 은(는) 등록되지 않은 카테고리입니다.")
        if confirm(f"  '{name}' 카테고리를 새로 등록할까요? [y/N]: "):
            categories.add(name)
            print(f"  카테고리 '{name}' 을(를) 등록했습니다.")
            return name
        print("  → 목록에 있는 카테고리를 다시 입력하세요.")


@log_execution
def handle(args, ctx) -> int:
    """add 명령 실행: 거래 필드를 순서대로 입력받아 저장하고 id를 출력한다.

    [역할]
    - 날짜: 엔터만 치면 오늘 날짜
    - 타입: income/expense (단축 i/e, 수입/지출 허용)
    - 금액: 양의 정수 (쉼표 허용)
    - 메모/태그: 선택 (엔터로 건너뛰기)

    Args:
        args: 파싱된 인자
        ctx: AppContext
    Returns:
        종료 코드 0
    """
    print("새 거래를 입력합니다. (취소: Ctrl+C)")
    today = date.today().isoformat()
    tx_date = ask(f"날짜 (YYYY-MM-DD, 엔터={today}): ", v.parse_date, default=today)
    tx_type = ask("타입 (income/expense, 단축 i/e): ", lambda s: v.parse_type(s, allow_alias=True))
    category = _ask_category(ctx.categories)
    amount = ask("금액 (양의 정수): ", v.parse_amount)
    memo = ask("메모 (선택, 엔터=건너뛰기): ", v.parse_memo, default="")
    tags = ask("태그 (선택, 쉼표로 구분): ", v.parse_tags, default=[])

    tx = ctx.transactions.create(date=tx_date, type=tx_type, category=category,
                                 amount=amount, memo=memo, tags=tags)
    print()
    print(f"저장 완료! 생성된 거래 id: {tx.id}")
    print(describe(tx))
    return 0
