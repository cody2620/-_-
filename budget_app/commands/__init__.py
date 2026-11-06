"""기능별 CLI 명령 모듈 모음.

[파일 역할]
- 각 명령 모듈을 불러와 COMMAND_MODULES 튜플로 묶는다.
  (cli.build_parser 가 이 순서대로 하위 명령을 등록하며, --help 표시 순서도 같다)
- 모든 명령 모듈은 같은 규칙을 따른다.
    register(subparsers, common): 하위 명령과 옵션을 argparse에 등록
    handle(args, ctx) -> int    : 명령 실행 후 종료 코드 반환
"""

from . import add, budget, category, delete, export_cmd, import_cmd, list_cmd, search, summary, update

# --help 에 표시되는 순서
COMMAND_MODULES = (add, list_cmd, search, update, delete, summary, budget, category, import_cmd, export_cmd)
