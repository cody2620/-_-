"""CLI 진입점: 인자 파싱 → 저장소 준비 → 명령 실행 → 종료 코드 반환.

[파일 역할]
- argparse로 최상위 파서를 만들고, commands 패키지의 각 명령 모듈을 하위 명령으로 등록한다.
- --verbose 여부에 따라 로깅을 설정한다.
- 선택된 명령의 handler를 @handle_errors 로 감싼 run()에서 실행해,
  어떤 오류가 나도 스택트레이스 없이 '원인 + 힌트'와 종료 코드로 끝나게 한다.
"""

import argparse
import logging
import sys
from typing import List, Optional

from . import __version__, config
from .app_context import build_context
from .commands import COMMAND_MODULES
from .commands._common import build_common_parser
from .core.decorators import handle_errors


def build_parser() -> argparse.ArgumentParser:
    """최상위 argparse 파서를 만든다.

    [역할]
    - 전역 옵션(--data-dir, --verbose, --version)을 정의한다.
    - COMMAND_MODULES의 각 모듈에 register()를 호출해 add/list/... 하위 명령을 붙인다.

    Returns:
        완성된 ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="나만의 용돈 기입장 - 수입/지출 기록, 검색, 월별 요약, 예산 관리 (JSONL 파일 저장)",
        epilog="각 명령의 자세한 사용법: python -m budget_app <command> --help\n"
               "예시:\n"
               "  python -m budget_app add\n"
               "  python -m budget_app list --limit 5\n"
               "  python -m budget_app summary --month 2026-11 --top 3",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default=config.DEFAULT_DATA_DIR, metavar="DIR",
                        help=f"저장 폴더 경로 (기본: {config.DEFAULT_DATA_DIR})")
    parser.add_argument("--verbose", action="store_true", help="실행 로그(시작/종료/소요 시간)를 표준 오류로 출력")
    parser.add_argument("--version", action="version", version=f"budget_app {__version__}")

    common = build_common_parser()
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", title="명령")
    for module in COMMAND_MODULES:
        module.register(subparsers, common)
    return parser


def _configure_logging(verbose: bool) -> None:
    """"budget_app" 로거의 출력 방식을 설정한다.

    [역할] @log_execution 데코레이터가 남기는 로그를
    --verbose 이면 stderr로 출력하고, 아니면 아무 데도 출력하지 않는다(NullHandler).

    Args:
        verbose: --verbose 옵션 지정 여부
    """
    logger = logging.getLogger("budget_app")
    logger.handlers.clear()
    logger.propagate = False
    if verbose:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("[log] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    else:
        logger.addHandler(logging.NullHandler())


@handle_errors
def run(args: argparse.Namespace) -> int:
    """저장소를 준비하고 선택된 명령의 handler를 실행한다.

    [역할] @handle_errors 가 적용되어 있어, 이 함수 안에서 발생한 모든 예외가
    '[오류] 원인 / [힌트] 해결법' 출력 + 종료 코드로 변환된다.

    Args:
        args: 파싱된 명령줄 인자 (args.handler 에 실행할 함수가 들어 있음)
    Returns:
        종료 코드 (0 = 정상)
    """
    ctx, notices = build_context(args.data_dir)
    for notice in notices:
        print(f"[안내] {notice}")
    return args.handler(args, ctx)


def main(argv: Optional[List[str]] = None) -> int:
    """프로그램 메인 함수.

    [역할]
    1) 명령줄 인자를 파싱한다. (잘못된 옵션은 argparse가 사용법 출력 후 종료 코드 2)
    2) 로깅을 설정한다.
    3) 명령이 지정되지 않았으면 도움말을 보여주고 종료 코드 2를 반환한다.
    4) run()으로 명령을 실행하고 종료 코드를 반환한다.

    Args:
        argv: 테스트용 인자 목록. None이면 sys.argv를 사용한다.
    Returns:
        종료 코드
    """
    parser = build_parser()
    args = parser.parse_args(argv)  # 잘못된 옵션은 argparse가 사용법을 보여주고 종료 코드 2로 종료
    _configure_logging(args.verbose)
    if getattr(args, "handler", None) is None:
        parser.print_help()
        print("\n[오류] 실행할 명령을 지정하세요. 예: python -m budget_app list", file=sys.stderr)
        return config.EXIT_VALIDATION
    return run(args)
