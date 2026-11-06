"""update 명령: 거래 수정 (옵션 기반 - 안 A로 고정).

[파일 역할]
- `update --id <id> [--date] [--type] [--category] [--amount] [--memo] [--tags]`
  형태로, 지정한 필드만 수정한다. (요구사항 6)
- 없는 id는 '없는 데이터' 메시지와 종료 코드 3으로 처리한다.
- 수정 결과를 '필드: 이전 값 → 새 값' 형태로 보여준다.
- 실제 파일 수정은 임시 파일 재작성 + 원자적 교체로 이루어진다. (storage 계층)
"""

from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import money
from ._common import add_command, arg_type

_FIELDS = (("date", "날짜"), ("type", "타입"), ("category", "카테고리"), ("amount", "금액"),
           ("memo", "메모"), ("tags", "태그"))


def register(subparsers, common) -> None:
    """update 하위 명령과 --id(필수), 수정 가능한 필드 옵션들을 등록한다."""
    parser = add_command(
        subparsers, "update", common,
        help="거래 수정 (옵션 방식)",
        description="--id 로 지정한 거래에서, 옵션으로 넘긴 필드만 수정합니다. (옵션 기반 방식으로 고정)\n"
                    "--memo \"\" / --tags \"\" 처럼 빈 값을 주면 메모/태그를 비웁니다.",
        examples="  python -m budget_app update --id 1a2b3c4d --amount 15000\n"
                 "  python -m budget_app update --id 1a2b3c4d --category transport --memo \"버스\" --tags \"commute,work\"")
    parser.add_argument("--id", required=True, type=arg_type(v.parse_id), help="수정할 거래 id (필수)")
    parser.add_argument("--date", type=arg_type(v.parse_date), metavar="YYYY-MM-DD", help="새 날짜")
    parser.add_argument("--type", type=arg_type(v.parse_type), metavar="income|expense", help="새 타입")
    parser.add_argument("--category", type=arg_type(v.parse_category_name), help="새 카테고리 (등록된 것만)")
    parser.add_argument("--amount", type=arg_type(v.parse_amount), help="새 금액 (양의 정수)")
    parser.add_argument("--memo", type=arg_type(v.parse_memo), help="새 메모")
    parser.add_argument("--tags", type=arg_type(v.parse_tags), help="새 태그 (쉼표 구분, 기존 태그를 대체)")
    parser.set_defaults(handler=handle)


def _show(value) -> str:
    """수정 전/후 값을 화면용 문자열로 바꾼다.

    [역할] 금액(int)은 '9,000원', 태그(list)는 'a, b', 빈 값은 '-' 로 표시한다.

    Args:
        value: 필드 값
    Returns:
        출력용 문자열
    """
    if isinstance(value, int):
        return money(value)
    if isinstance(value, list):
        return ", ".join(value) or "-"
    return str(value) if value != "" else "-"


@log_execution
def handle(args, ctx) -> int:
    """update 명령 실행: 옵션으로 받은 필드만 바꿔 저장하고 변경 내역을 출력한다.

    [역할]
    - 수정할 필드가 하나도 없으면 오류(종료 코드 2)
    - 새 값이 기존 값과 모두 같으면 '수정 사항 없음'을 알리고 파일은 건드리지 않는다.

    Returns:
        종료 코드 0
    """
    changes = {name: getattr(args, name) for name, _ in _FIELDS}
    old, new = ctx.transactions.update(args.id, changes)
    if old == new:
        print(f"수정 사항이 없습니다. (id: {new.id} - 입력한 값이 기존 값과 같습니다)")
        return 0
    print(f"수정 완료! (id: {new.id})")
    for name, label in _FIELDS:
        before, after = getattr(old, name), getattr(new, name)
        if before != after:
            print(f"  {label}: {_show(before)} → {_show(after)}")
    return 0
