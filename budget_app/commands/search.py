"""search 명령: 조건 검색 (최신순).

[파일 역할]
- --from/--to(기간), --category, --type, --q(메모 키워드), --tag 조건으로
  거래를 검색한다. 여러 조건은 모두 만족(AND)해야 한다. (요구사항 7)
- 저장 파일을 제너레이터로 흘려보내며 조건에 맞는 것만 골라낸다(스트리밍).
- 결과는 최신순으로 출력하고, 건수와 수입/지출 합계를 함께 보여준다.
"""

from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import money, print_transactions
from ..models.filters import TransactionFilter
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """search 하위 명령과 검색 조건 옵션들을 등록한다.

    [역할] --from 은 파이썬 예약어(from)와 겹치므로 dest="date_from" 으로 저장한다.
    --tag 는 여러 번 지정할 수 있다(action="append").
    """
    parser = add_command(
        subparsers, "search", common,
        help="거래 검색 (기간/카테고리/타입/메모/태그)",
        description="조건에 맞는 거래를 최신순으로 출력합니다. 여러 조건은 모두 만족(AND)해야 합니다.",
        examples="  python -m budget_app search --from 2026-11-01 --to 2026-11-30\n"
                 "  python -m budget_app search --category food --type expense\n"
                 "  python -m budget_app search --q 점심 --tag work")
    parser.add_argument("--from", dest="date_from", type=arg_type(v.parse_date), metavar="YYYY-MM-DD",
                        help="시작 날짜 (포함)")
    parser.add_argument("--to", dest="date_to", type=arg_type(v.parse_date), metavar="YYYY-MM-DD",
                        help="종료 날짜 (포함)")
    parser.add_argument("--category", type=arg_type(v.parse_category_name), help="카테고리")
    parser.add_argument("--type", type=arg_type(v.parse_type), choices=None, metavar="income|expense",
                        help="거래 타입")
    parser.add_argument("--q", type=arg_type(v.parse_keyword), metavar="KEYWORD", help="메모 키워드 (부분 일치)")
    parser.add_argument("--tag", type=arg_type(v.parse_tag), action="append", default=[], metavar="TAG",
                        help="태그 (여러 번 지정 시 모두 포함한 거래)")
    parser.add_argument("--limit", type=arg_type(v.parse_positive_int), metavar="N",
                        help="출력할 최대 건수 (기본: 전체)")
    parser.set_defaults(handler=handle)


@log_execution
def handle(args, ctx) -> int:
    """search 명령 실행: 조건으로 필터를 만들어 검색하고 결과를 출력한다.

    [역할] --category 가 등록되지 않은 이름이면 오류(종료 코드 3)로 안내한다.

    Returns:
        종료 코드 0
    """
    if args.category:
        ctx.categories.ensure_exists(args.category)
    flt = TransactionFilter(date_from=args.date_from, date_to=args.date_to, category=args.category,
                            type=args.type, keyword=args.q, tags=args.tag)
    results = ctx.transactions.search(flt, args.limit)
    if not results:
        print("조건에 맞는 거래가 없습니다.")
        return 0
    print("[검색 결과] 최신순")
    count = print_transactions(results)
    income = sum(t.amount for t in results if t.type == "income")
    expense = sum(t.amount for t in results if t.type == "expense")
    print(f"\n{count}건 | 수입 합계 {money(income)} | 지출 합계 {money(expense)}")
    return 0
