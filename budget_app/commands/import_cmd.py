"""import 명령: CSV 거래 일괄 등록.

[파일 역할]
- `import --from <csv> [--skip-invalid]` 로 CSV의 거래를 한꺼번에 저장한다. (요구사항 11)
- 기본은 '전부 아니면 전무': 잘못된 행이 하나라도 있으면 아무것도 반영하지 않고
  행 번호별 오류를 보여준 뒤 종료 코드 2로 끝난다.
- --skip-invalid 를 주면 잘못된 행만 건너뛰고 나머지를 반영한다.
- 완료 시 처리 건수를 출력한다.
- 파일 이름이 import_cmd.py 인 이유: 예약어 import 와 겹치지 않게 하기 위함.
"""

import sys
from pathlib import Path

from .. import config
from ..core.decorators import log_execution
from ..core.errors import ValidationError
from ._common import add_command

_MAX_ERRORS_SHOWN = 20


def register(subparsers, common) -> None:
    """import 하위 명령과 --from(필수), --skip-invalid 옵션을 등록한다.

    [역할] --from 은 예약어와 겹치므로 dest="src" 로 저장한다.
    """
    parser = add_command(
        subparsers, "import", common,
        help="CSV에서 거래 일괄 등록",
        description=f"CSV(UTF-8, 헤더 포함)의 거래를 일괄 등록합니다.\n"
                    f"헤더: {','.join(config.CSV_COLUMNS)}  (memo, tags 는 선택)\n"
                    "기본은 모든 행이 올바를 때만 반영합니다. 잘못된 행이 하나라도 있으면 아무것도 반영하지 않습니다.",
        examples="  python -m budget_app import --from samples/sample_import.csv\n"
                 "  python -m budget_app import --from my.csv --skip-invalid")
    parser.add_argument("--from", dest="src", required=True, metavar="CSV", help="가져올 CSV 파일 경로 (필수)")
    parser.add_argument("--skip-invalid", action="store_true", help="잘못된 행은 건너뛰고 올바른 행만 반영")
    parser.set_defaults(handler=handle)


def _print_errors(errors) -> None:
    """잘못된 CSV 행 목록을 stderr로 출력한다. (최대 20건, 나머지는 '... 외 N건')

    Args:
        errors: (CSV 줄 번호, 오류 사유) 목록
    """
    for line, reason in errors[:_MAX_ERRORS_SHOWN]:
        print(f"  - {line}행: {reason}", file=sys.stderr)
    if len(errors) > _MAX_ERRORS_SHOWN:
        print(f"  ... 외 {len(errors) - _MAX_ERRORS_SHOWN}건", file=sys.stderr)


@log_execution
def handle(args, ctx) -> int:
    """import 명령 실행: CSV를 검증/반영하고 결과 건수를 출력한다.

    Returns:
        종료 코드 0 (중단된 경우 ValidationError → 종료 코드 2)
    """
    result = ctx.csv.import_csv(Path(args.src), skip_invalid=args.skip_invalid)
    if result.errors:
        print(f"[잘못된 행 {len(result.errors)}건]", file=sys.stderr)
        _print_errors(result.errors)
    if result.aborted:
        raise ValidationError(
            f"CSV에 잘못된 행이 {len(result.errors)}건 있어 가져오기를 중단했습니다. (반영 0건 / 전체 {result.total}건)",
            "오류 행을 고친 뒤 다시 실행하거나, --skip-invalid 로 올바른 행만 가져오세요.")
    print(f"가져오기 완료: 전체 {result.total}건 중 {result.imported}건 등록"
          + (f", {len(result.errors)}건 건너뜀" if result.errors else ""))
    print("  → python -m budget_app list 로 반영 결과를 확인하세요.")
    return 0
