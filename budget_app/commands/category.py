"""category 명령: 카테고리 관리 (add / list / remove).

[파일 역할]
- category add    [--name 이름]               : 추가 (--name 생략 시 대화형 입력)
- category list                               : 목록 + 카테고리별 사용 거래 건수
- category remove --name 이름 [--replace 대체] : 삭제 (요구사항 10)
  사용 중인 카테고리는 삭제를 막고, --replace 를 주면 거래를 옮긴 뒤 삭제한다.
"""

import argparse

from .. import config
from ..core import validators as v
from ..core.decorators import log_execution
from ..core.formatting import fit
from ..core.prompts import ask
from ._common import add_command, arg_type


def register(subparsers, common) -> None:
    """category 명령과 하위 명령(add/list/remove)을 등록한다.

    [역할] 하위 명령 없이 `category` 만 실행하면 도움말 + 오류를 보여주도록
    기본 handler를 _missing_action 으로 지정한다.
    """
    parser = add_command(
        subparsers, "category", common,
        help="카테고리 관리 (add/list/remove)",
        description="거래에 사용할 카테고리를 관리합니다.\n"
                    "사용 중인 카테고리는 --replace 로 대체 카테고리를 지정해야만 삭제할 수 있습니다.",
        examples="  python -m budget_app category list\n"
                 "  python -m budget_app category add --name hobby\n"
                 "  python -m budget_app category remove --name hobby\n"
                 "  python -m budget_app category remove --name hobby --replace etc")
    actions = parser.add_subparsers(dest="category_action", metavar="<action>", title="하위 명령")

    p_add = add_command(actions, "add", common, help="카테고리 추가",
                        description="카테고리를 추가합니다. --name 을 생략하면 대화형으로 입력받습니다.",
                        examples="  python -m budget_app category add --name hobby\n  python -m budget_app category add")
    p_add.add_argument("--name", type=arg_type(v.parse_category_name), help="추가할 카테고리 이름")
    p_add.set_defaults(handler=handle_add)

    p_list = add_command(actions, "list", common, help="카테고리 목록 (사용 건수 포함)",
                         description="등록된 카테고리와 각 카테고리를 사용하는 거래 건수를 출력합니다.",
                         examples="  python -m budget_app category list")
    p_list.set_defaults(handler=handle_list)

    p_remove = add_command(actions, "remove", common, help="카테고리 삭제",
                           description="카테고리를 삭제합니다. 해당 카테고리를 쓰는 거래가 있으면 삭제를 막고,\n"
                                       "--replace 로 대체 카테고리를 지정하면 거래를 옮긴 뒤 삭제합니다.",
                           examples="  python -m budget_app category remove --name hobby --replace etc")
    p_remove.add_argument("--name", required=True, type=arg_type(v.parse_category_name), help="삭제할 카테고리 (필수)")
    p_remove.add_argument("--replace", type=arg_type(v.parse_category_name), metavar="CATEGORY",
                          help="사용 중인 거래를 옮길 대체 카테고리")
    p_remove.set_defaults(handler=handle_remove)

    parser.set_defaults(handler=_missing_action(parser))


def _missing_action(parser: argparse.ArgumentParser):
    """하위 명령이 빠졌을 때 실행할 handler를 만든다.

    Args:
        parser: category 명령 파서 (도움말 출력용)
    Returns:
        도움말을 출력하고 종료 코드 2를 반환하는 handler 함수
    """
    def handler(args, ctx) -> int:
        """category 도움말과 '하위 명령을 지정하세요' 오류를 출력하고 종료 코드 2를 반환한다."""
        parser.print_help()
        print("\n[오류] 하위 명령(add/list/remove)을 지정하세요.")
        return config.EXIT_VALIDATION
    return handler


@log_execution
def handle_add(args, ctx) -> int:
    """category add 실행: 카테고리를 추가한다.

    [역할] --name 이 없으면 대화형으로 이름을 입력받는다.
    이미 있는 이름이면 ConflictError(종료 코드 4).

    Returns:
        종료 코드 0
    """
    name = args.name or ask("추가할 카테고리 이름: ", v.parse_category_name)
    ctx.categories.add(name)
    print(f"카테고리 추가 완료: {name}")
    return 0


@log_execution
def handle_list(args, ctx) -> int:
    """category list 실행: 등록된 카테고리와 각각을 사용하는 거래 건수를 출력한다.

    Returns:
        종료 코드 0
    """
    rows = ctx.categories.list_with_usage()
    print(f"[카테고리 목록] 총 {len(rows)}개")
    for name, used in rows:
        print(f"  - {fit(name, 14)} 사용 거래 {used}건")
    return 0


@log_execution
def handle_remove(args, ctx) -> int:
    """category remove 실행: 카테고리를 삭제한다.

    [역할]
    - 사용 중이고 --replace 가 없으면 ConflictError(종료 코드 4)로 삭제를 막는다.
    - --replace 가 있으면 옮긴 거래 건수를 출력한 뒤 삭제한다.
    - 카테고리가 모두 사라지면 다음 실행 때 기본 카테고리가 생성된다고 안내한다.

    Returns:
        종료 코드 0
    """
    moved = ctx.categories.remove(args.name, args.replace)
    if moved:
        print(f"거래 {moved}건의 카테고리를 '{args.name}' → '{args.replace}' 로 변경했습니다.")
    print(f"카테고리 삭제 완료: {args.name}")
    if not ctx.categories.names():
        print("  ※ 카테고리가 모두 삭제되었습니다. 다음 실행 시 기본 카테고리가 자동 생성됩니다.")
    return 0
