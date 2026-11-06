"""명령 모듈들이 공유하는 argparse 도우미.

[파일 역할]
- 검증 함수(validators)를 argparse의 type= 으로 쓸 수 있게 변환한다.
- 모든 하위 명령에 붙는 공통 옵션(--data-dir, --verbose) 파서를 만든다.
- 하위 명령 파서 생성 코드(설명/예시/포맷)를 한 함수로 통일한다.
"""

import argparse
from typing import Callable

from .. import config
from ..core.errors import ValidationError


def arg_type(parser: Callable):
    """검증 함수를 argparse의 type= 인자로 쓸 수 있게 감싼다.

    [역할] 검증 함수는 ValidationError를 던지는데, argparse는 ArgumentTypeError만
    메시지를 그대로 보여준다. 그래서 둘을 변환해 '원인 (힌트)' 형태로 출력되게 한다.

    Args:
        parser: 문자열을 받아 검증/변환하는 함수 (예: validators.parse_date)
    Returns:
        argparse의 type= 에 넣을 수 있는 변환 함수
    """

    def _convert(value: str):
        """실제 변환 함수: parser를 호출하고 ValidationError를 ArgumentTypeError로 바꾼다."""
        try:
            return parser(value)
        except ValidationError as exc:
            raise argparse.ArgumentTypeError(f"{exc.message} ({exc.hint})" if exc.hint else exc.message)

    _convert.__name__ = parser.__name__
    return _convert


def build_common_parser() -> argparse.ArgumentParser:
    """모든 하위 명령에 붙일 공통 옵션 파서를 만든다.

    [역할] --data-dir, --verbose 를 `list --data-dir x` 처럼 명령 뒤에 써도 동작하게 한다.
    default=SUPPRESS 로 두어, 명령 뒤에서 지정하지 않으면 최상위 파서의 값(기본값)을
    덮어쓰지 않게 한다.

    Returns:
        add_help=False 인 부모(parents) 파서
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", default=argparse.SUPPRESS, metavar="DIR",
                        help=f"저장 폴더 경로 (기본: {config.DEFAULT_DATA_DIR})")
    common.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS,
                        help="실행 로그(시작/종료/소요 시간)를 표준 오류로 출력")
    return common


def add_command(subparsers, name: str, common, *, help: str, description: str, examples: str):
    """하위 명령 파서를 일정한 형식으로 만든다.

    [역할] 모든 명령이 공통 옵션, 한 줄 도움말, 상세 설명, '예시:' 블록을
    같은 모양으로 갖도록 한다.

    Args:
        subparsers: add_subparsers()로 만든 하위 명령 묶음
        name: 명령 이름 (예: "list")
        common: build_common_parser()의 결과
        help: 상위 --help 목록에 표시될 한 줄 설명
        description: 이 명령 --help 상단 설명
        examples: --help 하단에 표시될 사용 예시
    Returns:
        생성된 하위 명령 ArgumentParser
    """
    return subparsers.add_parser(
        name, parents=[common], help=help, description=description,
        epilog="예시:\n" + examples, formatter_class=argparse.RawDescriptionHelpFormatter)
