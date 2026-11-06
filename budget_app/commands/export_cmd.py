"""export 명령: 조건에 맞는 거래를 CSV로 저장.

[파일 역할]
- `export --out <csv> (--month YYYY-MM | --from YYYY-MM-DD --to YYYY-MM-DD)`
  기간 조건 중 하나가 반드시 필요하다. (요구사항 11)
- 선택 조건으로 --category, --type 도 지원한다.
- CSV는 UTF-8, 헤더(date,type,category,amount,memo,tags) 포함으로 저장한다.
"""

from pathlib import Path

from .. import config
from ..core import validators as v
from ..core.decorators import log_execution
from ..core.errors import ValidationError
from ..models.filters import TransactionFilter
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """export 하위 명령과 --out(필수), 기간/선택 조건 옵션들을 등록한다."""
    parser = add_command(
        subparsers, "export", common,
        help="조건에 맞는 거래를 CSV로 내보내기",
        description=f"거래를 CSV(UTF-8, 헤더 포함)로 저장합니다. 헤더: {','.join(config.CSV_COLUMNS)}\n"
                    "--month 또는 --from/--to(둘 다) 중 하나의 기간 조건이 반드시 필요합니다.",
        examples="  python -m budget_app export --out out/2026-11.csv --month 2026-11\n"
                 "  python -m budget_app export --out out/q4.csv --from 2026-10-01 --to 2026-12-31 --type expense")
    parser.add_argument("--out", required=True, metavar="CSV", help="저장할 CSV 경로 (필수, 있으면 덮어씀)")
    parser.add_argument("--month", type=arg_type(v.parse_month), metavar="YYYY-MM", help="대상 월")
    parser.add_argument("--from", dest="date_from", type=arg_type(v.parse_date), metavar="YYYY-MM-DD",
                        help="시작 날짜 (포함)")
    parser.add_argument("--to", dest="date_to", type=arg_type(v.parse_date), metavar="YYYY-MM-DD",
                        help="종료 날짜 (포함)")
    parser.add_argument("--category", type=arg_type(v.parse_category_name), help="(선택) 카테고리")
    parser.add_argument("--type", type=arg_type(v.parse_type), metavar="income|expense", help="(선택) 거래 타입")
    parser.set_defaults(handler=handle)


def _validate_period(args) -> None:
    """export 의 기간 조건 규칙을 검사한다.

    [역할]
    - 기간 조건이 하나도 없으면 오류
    - --month 와 --from/--to 를 함께 쓰면 오류
    - --from, --to 중 하나만 쓰면 오류

    Raises:
        ValidationError: 규칙 위반 시 (종료 코드 2)
    """
    has_range = args.date_from is not None or args.date_to is not None
    if args.month is None and not has_range:
        raise ValidationError("내보낼 기간 조건이 없습니다.",
                              "--month YYYY-MM 또는 --from YYYY-MM-DD --to YYYY-MM-DD 를 지정하세요.")
    if args.month is not None and has_range:
        raise ValidationError("--month 와 --from/--to 는 함께 쓸 수 없습니다.", "둘 중 하나만 지정하세요.")
    if has_range and (args.date_from is None or args.date_to is None):
        raise ValidationError("--from 과 --to 는 함께 지정해야 합니다.",
                              "예: --from 2026-11-01 --to 2026-11-30")


@log_execution
def handle(args, ctx) -> int:
    """export 명령 실행: 기간 규칙을 검사하고 조건에 맞는 거래를 CSV로 저장한다.

    [역할] 저장 건수를 출력하며, 0건이면 헤더만 저장했다고 알려준다.

    Returns:
        종료 코드 0
    """
    _validate_period(args)
    if args.category:
        ctx.categories.ensure_exists(args.category)
    flt = TransactionFilter(month=args.month, date_from=args.date_from, date_to=args.date_to,
                            category=args.category, type=args.type)
    out = Path(args.out)
    count = ctx.csv.export_csv(out, flt)
    print(f"내보내기 완료: {count}건 → {out}")
    if count == 0:
        print("  (조건에 맞는 거래가 없어 헤더만 저장했습니다)")
    return 0
