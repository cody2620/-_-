"""summary 명령: 월별 요약 (+ 예산 사용률/초과 경고).

[파일 역할]
- `summary --month YYYY-MM [--top N]` 으로 해당 월의
  총수입/총지출/잔액과 카테고리별 지출 TOP N을 출력한다. (요구사항 8)
- 거래가 없는 달은 '데이터 없음'을 출력한다.
- 예산이 설정되어 있으면 사용률(%)과 초과 경고를 함께 출력한다. (요구사항 9)
- 예산 영역 출력 함수(print_budget_section)는 `budget show` 에서도 재사용한다.
"""

from .. import config
from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import fit, money
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """summary 하위 명령과 --month(필수), --top(기본 3) 옵션을 등록한다."""
    parser = add_command(
        subparsers, "summary", common,
        help="월별 요약 (수입/지출/잔액, 지출 TOP N, 예산)",
        description="해당 월의 총수입, 총지출, 잔액과 카테고리별 지출 TOP N을 출력합니다.\n"
                    "예산이 설정되어 있으면 사용률(%)과 초과 경고도 함께 출력합니다.",
        examples="  python -m budget_app summary --month 2026-11\n"
                 "  python -m budget_app summary --month 2026-11 --top 5")
    parser.add_argument("--month", required=True, type=arg_type(v.parse_month), metavar="YYYY-MM",
                        help="요약할 월 (필수)")
    parser.add_argument("--top", type=arg_type(v.parse_positive_int), default=config.DEFAULT_SUMMARY_TOP,
                        metavar="N", help=f"카테고리별 지출 상위 N개 (기본: {config.DEFAULT_SUMMARY_TOP})")
    parser.set_defaults(handler=handle)


def print_budget_section(summary) -> None:
    """요약 결과 중 [예산] 영역을 출력한다.

    [역할]
    - 예산이 없으면 설정 방법을 안내한다.
    - 예산이 있으면 월 예산/사용액/사용률을 보여주고,
      초과 시 '⚠ 경고', 80% 이상이면 '※ 주의' 문구를 출력한다.

    Args:
        summary: SummaryService.summarize() 의 결과(MonthlySummary)
    """
    budget = summary.budget
    print("\n[예산]")
    if budget is None:
        print(f"  설정된 예산 없음 → python -m budget_app budget set --month {summary.month} --amount <금액>")
        return
    rate = summary.usage_rate
    print(f"  월 예산   : {fit(money(budget.amount), 16, 'right')}")
    print(f"  사용액    : {fit(money(summary.expense), 16, 'right')}")
    print(f"  사용률    : {fit(f'{rate:.1f}%', 16, 'right')}")
    if summary.over_budget:
        print(f"  ⚠ 경고: 예산을 {money(summary.expense - budget.amount)} 초과했습니다! (사용률 {rate:.1f}%)")
    else:
        print(f"  남은 예산 : {fit(money(budget.amount - summary.expense), 16, 'right')}")
        if rate >= 80:
            print("  ※ 주의: 예산의 80% 이상을 사용했습니다.")


@log_execution
def handle(args, ctx) -> int:
    """summary 명령 실행: 월별 집계를 받아 화면에 출력한다.

    [역할] 데이터가 없는 달은 '데이터 없음'을 출력하고,
    예산이 있으면 예산 영역만 추가로 보여준다.

    Returns:
        종료 코드 0
    """
    s = ctx.summary.summarize(args.month, args.top)
    print(f"=== {s.month} 월별 요약 ===")
    if not s.has_data:
        print("데이터 없음 (해당 월에 등록된 거래가 없습니다)")
        if s.budget is not None:
            print_budget_section(s)
        return 0
    print(f"  총 수입   : {fit(money(s.income), 16, 'right')}  ({s.income_count}건)")
    print(f"  총 지출   : {fit(money(s.expense), 16, 'right')}  ({s.expense_count}건)")
    print(f"  잔액      : {fit(money(s.balance), 16, 'right')}")

    print(f"\n[카테고리별 지출 TOP {args.top}]")
    if not s.top_categories:
        print("  지출 내역 없음")
    for rank, (category, amount) in enumerate(s.top_categories, start=1):
        share = amount / s.expense * 100
        print(f"  {rank}. {fit(category, 12)} {fit(money(amount), 14, 'right')}  ({share:.1f}%)")

    print_budget_section(s)
    return 0
