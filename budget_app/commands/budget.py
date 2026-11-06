"""budget 명령: 월 예산 설정/조회 (set / show / list).

[파일 역할]
- budget set  --month YYYY-MM --amount 금액 : 월 예산 저장(있으면 덮어쓰기) (요구사항 9)
- budget show --month YYYY-MM              : 예산, 사용액, 사용률 조회
- budget list                              : 설정된 모든 월 예산 목록
- 예산은 budgets.jsonl 에 영구 저장된다.
"""

import argparse

from .. import config
from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import fit, money
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """budget 명령과 하위 명령(set/show/list)을 등록한다.

    [역할] 하위 명령 없이 `budget` 만 실행하면 도움말 + 오류를 보여주도록
    기본 handler를 _missing_action 으로 지정한다.
    """
    parser = add_command(
        subparsers, "budget", common,
        help="월 예산 설정/조회 (set/show/list)",
        description="월 예산을 저장하고 조회합니다. 예산은 budgets.jsonl 에 영구 저장됩니다.",
        examples="  python -m budget_app budget set --month 2026-11 --amount 300000\n"
                 "  python -m budget_app budget show --month 2026-11\n"
                 "  python -m budget_app budget list")
    actions = parser.add_subparsers(dest="budget_action", metavar="<action>", title="하위 명령")

    p_set = add_command(actions, "set", common, help="월 예산 저장(덮어쓰기)",
                        description="해당 월의 예산을 저장합니다. 이미 있으면 새 금액으로 바꿉니다.",
                        examples="  python -m budget_app budget set --month 2026-11 --amount 300000")
    p_set.add_argument("--month", required=True, type=arg_type(v.parse_month), metavar="YYYY-MM", help="월 (필수)")
    p_set.add_argument("--amount", required=True, type=arg_type(v.parse_amount), help="예산 금액 (양의 정수, 필수)")
    p_set.set_defaults(handler=handle_set)

    p_show = add_command(actions, "show", common, help="월 예산과 사용률 조회",
                         description="해당 월의 예산, 사용액, 사용률을 출력합니다.",
                         examples="  python -m budget_app budget show --month 2026-11")
    p_show.add_argument("--month", required=True, type=arg_type(v.parse_month), metavar="YYYY-MM", help="월 (필수)")
    p_show.set_defaults(handler=handle_show)

    p_list = add_command(actions, "list", common, help="설정된 모든 월 예산 목록",
                         description="설정된 월 예산을 월 순서로 출력합니다.",
                         examples="  python -m budget_app budget list")
    p_list.set_defaults(handler=handle_list)

    parser.set_defaults(handler=_missing_action(parser))


def _missing_action(parser: argparse.ArgumentParser):
    """하위 명령이 빠졌을 때 실행할 handler를 만든다.

    Args:
        parser: budget 명령 파서 (도움말 출력용)
    Returns:
        도움말을 출력하고 종료 코드 2를 반환하는 handler 함수
    """
    def handler(args, ctx) -> int:
        """budget 도움말과 '하위 명령을 지정하세요' 오류를 출력하고 종료 코드 2를 반환한다."""
        parser.print_help()
        print("\n[오류] 하위 명령(set/show/list)을 지정하세요.")
        return config.EXIT_VALIDATION
    return handler


@log_execution
def handle_set(args, ctx) -> int:
    """budget set 실행: 월 예산을 저장하고, 이전 예산이 있었다면 변경 전 금액도 알려준다.

    Returns:
        종료 코드 0
    """
    budget, previous = ctx.budgets.set(args.month, args.amount)
    print(f"저장 완료! {budget.month} 예산: {money(budget.amount)}")
    if previous is not None:
        print(f"  (이전 예산 {money(previous.amount)} 에서 변경)")
    return 0


@log_execution
def handle_show(args, ctx) -> int:
    """budget show 실행: 해당 월의 예산, 사용액, 사용률(초과 경고 포함)을 출력한다.

    [역할] 예산이 설정되지 않은 달이면 NotFoundError(종료 코드 3)로 설정 방법을 안내한다.

    Returns:
        종료 코드 0
    """
    from .summary import print_budget_section
    ctx.budgets.get(args.month)  # 없으면 NotFoundError
    s = ctx.summary.summarize(args.month, top=0)
    print(f"=== {args.month} 예산 ===", end="")
    print_budget_section(s)
    return 0


@log_execution
def handle_list(args, ctx) -> int:
    """budget list 실행: 설정된 모든 월 예산을 월 순서로 출력한다.

    Returns:
        종료 코드 0
    """
    budgets = ctx.budgets.list_all()
    if not budgets:
        print("설정된 예산이 없습니다.  → python -m budget_app budget set --month YYYY-MM --amount <금액>")
        return 0
    print("[월 예산 목록]")
    for b in budgets:
        print(f"  {b.month}  {fit(money(b.amount), 16, 'right')}")
    return 0
