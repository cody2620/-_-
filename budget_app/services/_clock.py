"""시간 관련 공통 함수.

[파일 역할] 생성/수정 시각 문자열을 만드는 함수를 한 곳에 둔다.
(여러 서비스가 같은 형식의 시각을 쓰도록 통일)
"""

from datetime import datetime


def now_iso() -> str:
    """현재 시각을 마이크로초까지 포함한 ISO 문자열로 반환한다.
    예: '2026-11-06T17:46:04.798556'

    [역할] 같은 날짜 거래의 최신순 정렬(created_at)에 사용되므로 마이크로초까지 기록한다.
    """
    return datetime.now().isoformat(timespec="microseconds")
