"""list 명령: 최신순 거래 목록.

[파일 역할]
- `list [--limit N]` 으로 최신순(날짜 → 입력 시각) 거래를 출력한다. (요구사항 5)
- 파일 전체를 한 번에 로드하지 않고, 제너레이터로 한 줄씩 읽으며
  상위 N건만 메모리에 유지한다. (TransactionService.recent)
- 파일 이름이 list_cmd.py 인 이유: 파이썬 내장 list와 이름이 겹치지 않게 하기 위함.
"""

from .. import config
from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import print_transactions
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """list 하위 명령과 --limit 옵션(기본 10)을 등록한다."""
    parser = add_command(
        subparsers, "list", common,
        help="거래 목록 (최신순)",
        description="저장된 거래를 최신순(날짜 → 입력 시각)으로 출력합니다.\n"
                    "파일을 한 줄씩 읽으며 상위 N건만 메모리에 유지합니다(제너레이터 스트리밍).",
        examples="  python -m budget_app list\n  python -m budget_app list --limit 20")
    parser.add_argument("--limit", type=arg_type(v.parse_positive_int), default=config.DEFAULT_LIST_LIMIT,
                        metavar="N", help=f"출력할 최대 건수 (기본: {config.DEFAULT_LIST_LIMIT})")
    parser.set_defaults(handler=handle)


@log_execution
def handle(args, ctx) -> int:
    """list 명령 실행: 최신 거래 N건을 표로 출력한다.

    [역할] 거래가 없으면 안내 문구와 함께 add 명령을 추천한다.

    Returns:
        종료 코드 0
    """
    items = ctx.transactions.recent(args.limit)
    if not items:
        print("거래 내역이 없습니다.")
        print("  → python -m budget_app add 로 첫 거래를 추가해 보세요.")
        return 0
    print(f"[거래 목록] 최신순, 최대 {args.limit}건")
    count = print_transactions(items)
    print(f"\n{count}건 표시")
    return 0
