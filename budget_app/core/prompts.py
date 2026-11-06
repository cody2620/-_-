"""대화형 입력 도우미.

[파일 역할]
- input()으로 값을 받고, 검증 함수로 확인한 뒤
  잘못된 값이면 이유와 힌트를 보여주고 다시 입력받는다. (요구사항 2 - 재입력 요구)
- y/n 확인 질문을 처리한다.
"""

from typing import Any, Callable

from .errors import ValidationError

_MISSING = object()


def ask(prompt: str, parser: Callable[[str], Any], default: Any = _MISSING) -> Any:
    """값을 입력받아 검증/변환한다. 올바른 값이 들어올 때까지 반복한다.

    [역할]
    - 빈 입력(엔터): default 가 있으면 default 반환, 없으면 '값을 입력해 주세요' 후 재입력
    - 검증 실패: '! 원인' 과 '→ 힌트' 를 보여주고 재입력

    Args:
        prompt: 화면에 보여줄 질문
        parser: 검증/변환 함수 (예: validators.parse_date)
        default: 빈 입력 시 사용할 기본값 (생략하면 필수 입력)
    Returns:
        parser 가 반환한 값 또는 default
    """
    while True:
        raw = input(prompt).strip()
        if not raw:
            if default is not _MISSING:
                return default
            print("  ! 값을 입력해 주세요.")
            continue
        try:
            return parser(raw)
        except ValidationError as exc:
            print(f"  ! {exc.message}")
            if exc.hint:
                print(f"    → {exc.hint}")


def confirm(prompt: str, default: bool = False) -> bool:
    """예/아니오 질문을 한다.

    [역할] y/yes/예/ㅇ → True, n/no/아니오/ㄴ → False,
    빈 입력 → default, 그 외 입력은 다시 묻는다.

    Args:
        prompt: 질문 문구
        default: 엔터만 쳤을 때의 답
    Returns:
        True(예) / False(아니오)
    """
    while True:
        raw = input(prompt).strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes", "예", "ㅇ"):
            return True
        if raw in ("n", "no", "아니오", "ㄴ"):
            return False
        print("  ! y 또는 n 으로 답해 주세요.")
