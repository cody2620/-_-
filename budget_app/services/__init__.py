"""services 패키지: 비즈니스 로직 계층.

[파일 역할] 이 폴더를 파이썬 패키지로 인식시키기 위한 파일이다. (실행 코드 없음)
- transaction_service.py : 거래 생성/조회/검색/수정/삭제
- category_service.py    : 카테고리 관리, 사용 중 카테고리 처리
- budget_service.py      : 월 예산
- summary_service.py     : 월별 집계, 예산 사용률
- csv_service.py         : CSV import/export
- _clock.py              : 현재 시각
Service 는 규칙(검증, 존재 확인 등)을 지키고, 실제 파일 작업은 Repository 에 맡긴다.
"""
