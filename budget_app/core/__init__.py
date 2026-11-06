"""core 패키지: 여러 계층(commands/services/storage/models)이 함께 쓰는 공통 기능.

[파일 역할] 이 폴더를 파이썬 패키지로 인식시키기 위한 파일이다. (실행 코드 없음)
- errors.py     : 앱 전용 예외 (원인 + 힌트 + 종료 코드)
- decorators.py : @handle_errors, @log_execution
- validators.py : 입력값 검증/변환
- prompts.py    : 대화형 입력 (오류 시 재입력)
- formatting.py : 화면 출력 (표, 금액, 오류 메시지)
"""
