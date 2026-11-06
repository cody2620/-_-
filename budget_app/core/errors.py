"""앱 전용 예외 클래스.

[파일 역할]
- 모든 오류는 '원인(message) + 해결 힌트(hint)'를 가진다.
- 예외 종류마다 종료 코드(exit_code)가 정해져 있어,
  @handle_errors 가 이 값을 그대로 프로그램 종료 코드로 사용한다.
    AppError(1) / ValidationError(2) / NotFoundError(3)
    ConflictError(4) / StorageError(5) / DataFileError(5)
"""

from .. import config


class AppError(Exception):
    """사용자에게 보여줄 수 있는 오류의 기반 클래스.

    [역할] 이 클래스(또는 하위 클래스)로 발생한 오류는 스택트레이스 없이
    '[오류] message / [힌트] hint' 로 출력되고 exit_code 로 종료된다.
    """

    exit_code = config.EXIT_ERROR

    def __init__(self, message: str, hint: str = "") -> None:
        """오류 메시지와 해결 힌트를 저장한다.

        Args:
            message: 무엇이 잘못되었는지 (원인)
            hint: 어떻게 고치면 되는지 (해결 방법). 없으면 빈 문자열.
        """
        super().__init__(message)
        self.message = message
        self.hint = hint


class ValidationError(AppError):
    """입력값 검증 실패. (날짜/금액/타입/카테고리 형식, 옵션 조합 오류 등) 종료 코드 2."""

    exit_code = config.EXIT_VALIDATION


class NotFoundError(AppError):
    """없는 데이터. (없는 id, 등록되지 않은 카테고리, 없는 CSV 파일, 미설정 예산 등) 종료 코드 3."""

    exit_code = config.EXIT_NOT_FOUND


class ConflictError(AppError):
    """상태 충돌. (이미 있는 카테고리 추가, 사용 중인 카테고리 삭제 등) 종료 코드 4."""

    exit_code = config.EXIT_CONFLICT


class StorageError(AppError):
    """저장 파일/폴더 읽기·쓰기 실패. (권한 없음, 경로 오류 등) 종료 코드 5."""

    exit_code = config.EXIT_STORAGE


class DataFileError(StorageError):
    """저장 파일 내용이 손상되어 해석할 수 없음. (잘못된 JSON 줄 등) 종료 코드 5."""
