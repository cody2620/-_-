"""`python -m budget_app` 실행 진입점.

[파일 역할]
- `python -m budget_app ...` 으로 실행하면 파이썬이 이 파일을 실행한다.
- cli.main()을 호출하고, 그 반환값(종료 코드)으로 프로세스를 종료한다.
  (정상 0, 오류 0이 아닌 값)
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
