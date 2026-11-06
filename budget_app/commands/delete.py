"""delete 명령: 거래 삭제.

[파일 역할]
- `delete --id <id>` 로 거래 1건을 삭제하고, 삭제된 거래 내용을 보여준다. (요구사항 6)
- 없는 id는 '없는 데이터' 메시지와 종료 코드 3으로 처리한다.
- 실제 삭제는 임시 파일 재작성 + 원자적 교체로 이루어진다. (storage 계층)
"""

from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import describe
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """delete 하위 명령과 --id(필수) 옵션을 등록한다."""
    parser = add_command(
        subparsers, "delete", common,
        help="거래 삭제",
        description="--id 로 지정한 거래를 삭제합니다. (임시 파일 재작성 후 원자적 교체)",
        examples="  python -m budget_app delete --id 1a2b3c4d")
    parser.add_argument("--id", required=True, type=arg_type(v.parse_id), help="삭제할 거래 id (필수)")
    parser.set_defaults(handler=handle)


@log_execution
def handle(args, ctx) -> int:
    """delete 명령 실행: id로 거래를 삭제하고 삭제된 내용을 출력한다.

    Returns:
        종료 코드 0 (없는 id면 NotFoundError → 종료 코드 3)
    """
    tx = ctx.transactions.delete(args.id)
    print(f"삭제 완료! (id: {tx.id})")
    print(describe(tx))
    return 0
