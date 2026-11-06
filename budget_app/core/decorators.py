"""공통 관심사 데코레이터.

[파일 역할]
- handle_errors : 예외 처리 공통화. 스택트레이스 대신 '원인 + 힌트'를 출력하고
                  알맞은 종료 코드를 반환한다. (cli.run 에 적용)
- log_execution : 명령 시작/종료/성공 여부/소요 시간을 로그로 남긴다.
                  (모든 명령 handler 에 적용, --verbose 로 확인)
"""

import functools
import logging
import sys
import time

from .. import config
from .errors import AppError
from .formatting import print_error

logger = logging.getLogger("budget_app")


def handle_errors(func):
    """함수 실행 중 발생한 예외를 잡아 사용자 친화적인 메시지와 종료 코드로 바꾼다.

    [역할]
    - AppError 계열   → '[오류] 원인 / [힌트] 해결법', 해당 exit_code
    - Ctrl+C          → 취소 안내, 130
    - 입력 끝(EOF)     → 대화형 실행 안내, 130
    - 그 외 모든 예외  → 일반 오류 안내, 1 (스택트레이스 출력 금지)
    - 정상 종료 시 함수가 None을 반환하면 0으로 바꿔준다.

    Args:
        func: 감쌀 함수
    Returns:
        종료 코드(int)를 반환하는 함수
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> int:
        """실제로 func를 실행하고, 결과나 예외를 종료 코드로 변환한다."""
        try:
            result = func(*args, **kwargs)
            return config.EXIT_OK if result is None else int(result)
        except AppError as exc:
            print_error(exc.message, exc.hint)
            return exc.exit_code
        except KeyboardInterrupt:
            print(file=sys.stderr)
            print_error("사용자가 입력을 취소했습니다.", "변경 사항은 저장되지 않았습니다. 다시 실행해 주세요.")
            return config.EXIT_CANCELLED
        except EOFError:
            print(file=sys.stderr)
            print_error("입력이 끝나(EOF) 더 이상 값을 읽을 수 없습니다.",
                        "대화형 명령은 터미널에서 직접 실행하거나, 필요한 값을 모두 입력으로 넘겨 주세요.")
            return config.EXIT_CANCELLED
        except Exception as exc:  # noqa: BLE001 - 마지막 안전망 (스택트레이스 출력 금지)
            logger.debug("예기치 못한 오류: %r", exc)
            print_error(f"예기치 못한 오류가 발생했습니다: {type(exc).__name__}: {exc}",
                        "입력값과 저장 폴더(--data-dir)의 파일 상태를 확인한 뒤 다시 시도하세요.")
            return config.EXIT_ERROR

    return wrapper


def log_execution(func):
    """함수의 시작/종료와 소요 시간을 "budget_app" 로거로 기록한다.

    [역할] 실패(예외)해도 finally 에서 '종료 [실패]' 로그가 남는다.
    로그 출력 여부는 cli._configure_logging(--verbose)이 결정한다.

    Args:
        func: 감쌀 함수 (주로 명령 handler)
    Returns:
        로그 기능이 추가된 함수 (반환값/예외는 그대로 전달)
    """

    name = f"{func.__module__.rsplit('.', 1)[-1]}.{func.__name__}"

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """시작 로그 → func 실행 → 종료 로그(성공/실패, ms 단위 소요 시간) 순으로 처리한다."""
        logger.info("시작: %s", name)
        started = time.perf_counter()
        status = "실패"
        try:
            result = func(*args, **kwargs)
            status = "성공"
            return result
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info("종료: %s [%s] (%.1fms)", name, status, elapsed_ms)

    return wrapper
