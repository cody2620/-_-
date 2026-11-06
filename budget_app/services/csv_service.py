"""CSV 가져오기(import) / 내보내기(export) 서비스.

[파일 역할]
- CSV 스키마(date,type,category,amount,memo,tags / UTF-8 / 헤더 포함)를 검증한다.
- import: 1차로 모든 행을 검증하고, 2차로 유효한 행만 스트리밍으로 저장한다.
- export: 조건에 맞는 거래를 임시 파일에 쓴 뒤 원자적으로 교체해 저장한다.
"""

import csv
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple

from .. import config
from ..core import validators as v
from ..core.errors import NotFoundError, StorageError, ValidationError
from ..models.filters import TransactionFilter
from ..storage.jsonl_file import apply_file_mode
from .category_service import CategoryService
from .transaction_service import TransactionService


@dataclass
class ImportResult:
    """import 결과.

    Attributes:
        total: CSV 데이터 행 수 (헤더 제외)
        imported: 실제로 저장한 건수
        errors: [(CSV 줄 번호, 오류 사유), ...]
        aborted: 오류 때문에 아무것도 반영하지 않았으면 True
    """

    total: int = 0
    imported: int = 0
    errors: List[Tuple[int, str]] = field(default_factory=list)  # (CSV 줄 번호, 사유)
    aborted: bool = False


def _iter_csv_rows(path: Path) -> Iterator[Tuple[int, Dict[str, str]]]:
    """CSV 파일을 한 행씩 읽는 제너레이터.

    [역할]
    - BOM 이 있는 UTF-8(엑셀 저장 형식)도 읽을 수 있게 utf-8-sig 로 연다.
    - 헤더 이름의 공백/대소문자를 정규화하고, 필수 컬럼이 모두 있는지 확인한다.
    - 파일 없음/폴더/권한/인코딩/CSV 형식 오류를 원인 + 힌트가 있는 예외로 바꾼다.

    Yields:
        (CSV 줄 번호, {컬럼명: 값})
    Raises:
        NotFoundError, ValidationError, StorageError
    """
    try:
        fp = path.open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError:
        raise NotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}", "경로와 파일 이름을 확인하세요.") from None
    except IsADirectoryError:
        raise ValidationError(f"CSV 경로가 폴더입니다: {path}", "CSV 파일 경로를 지정하세요.") from None
    except OSError as exc:
        raise StorageError(f"CSV 파일을 열 수 없습니다: {path} ({exc.strerror})", "파일 권한을 확인하세요.") from None
    with fp:
        try:
            reader = csv.DictReader(fp)
            if not reader.fieldnames:
                raise ValidationError("CSV 파일이 비어 있거나 헤더가 없습니다.",
                                      f"첫 줄에 헤더를 넣으세요: {','.join(config.CSV_COLUMNS)}")
            reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]
            missing = [c for c in config.CSV_REQUIRED_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise ValidationError(f"CSV 필수 컬럼이 없습니다: {', '.join(missing)}",
                                      f"헤더는 {','.join(config.CSV_COLUMNS)} 형식이어야 합니다. (memo, tags는 선택)")
            for row in reader:
                yield reader.line_num, row
        except UnicodeDecodeError:
            raise ValidationError(f"CSV 파일이 UTF-8 인코딩이 아닙니다: {path}",
                                  "엑셀에서는 'CSV UTF-8' 형식으로 다시 저장하세요.") from None
        except csv.Error as exc:
            raise ValidationError(f"CSV 형식 오류 (줄 {reader.line_num}): {exc}", "따옴표/쉼표가 올바른지 확인하세요.") from None


def _row_to_fields(row: Dict[str, str], categories: Set[str]) -> Dict[str, Any]:
    """CSV 한 행을 검증해 거래 필드 dict 로 바꾼다.

    [역할] 필수 값 존재 → 카테고리 등록 여부 → 날짜/타입/금액/메모/태그 형식 순으로
    검사한다. (대화형 입력과 같은 validators 규칙 사용)

    Args:
        row: {컬럼명: 값}
        categories: 등록된 카테고리 이름 집합
    Returns:
        {date, type, category, amount, memo, tags}
    Raises:
        ValidationError: 첫 번째로 발견된 문제
    """
    def cell(name: str) -> str:
        """컬럼 값을 가져온다. 컬럼이 없거나 None 이면 빈 문자열, 앞뒤 공백은 제거한다."""
        return (row.get(name) or "").strip()

    for name in config.CSV_REQUIRED_COLUMNS:
        if not cell(name):
            raise ValidationError(f"필수 값 '{name}' 이(가) 비어 있습니다.")
    category = v.parse_category_name(cell("category"))
    if category not in categories:
        raise ValidationError(f"등록되지 않은 카테고리 '{category}' (category add 로 먼저 등록하세요)")
    return {
        "date": v.parse_date(cell("date")),
        "type": v.parse_type(cell("type")),
        "category": category,
        "amount": v.parse_amount(cell("amount")),
        "memo": v.parse_memo(cell("memo")),
        "tags": v.parse_tags(cell("tags")),
    }


class CsvService:
    """CSV import/export 비즈니스 로직."""

    def __init__(self, transactions: TransactionService, categories: CategoryService) -> None:
        """거래 서비스(저장/조회용)와 카테고리 서비스(존재 확인용)를 주입받는다."""
        self._transactions = transactions
        self._categories = categories

    def import_csv(self, path: Path, skip_invalid: bool = False) -> ImportResult:
        """CSV 의 거래를 일괄 등록한다.

        [역할]
        - 1차: 모든 행을 검증해 오류 목록을 만든다.
        - 오류가 있고 skip_invalid=False 면 아무것도 저장하지 않는다. ('전부 아니면 전무')
        - 2차: CSV 를 다시 읽으며 유효한 행만 스트리밍으로 저장한다.
          (두 번 읽기 때문에 CSV 전체를 메모리에 올리지 않는다)

        Args:
            path: CSV 파일 경로
            skip_invalid: True 면 잘못된 행만 건너뛰고 나머지 저장
        Returns:
            ImportResult
        """
        categories = set(self._categories.names())
        result = ImportResult()
        for line, row in _iter_csv_rows(path):
            result.total += 1
            try:
                _row_to_fields(row, categories)
            except ValidationError as exc:
                result.errors.append((line, exc.message))

        if result.errors and not skip_invalid:
            result.aborted = True
            return result

        def valid_rows() -> Iterator[Dict[str, Any]]:
            """CSV 를 다시 읽으며 검증을 통과한 행의 필드 dict 만 내보내는 제너레이터."""
            for _, row in _iter_csv_rows(path):
                try:
                    yield _row_to_fields(row, categories)
                except ValidationError:
                    continue

        result.imported = self._transactions.create_many(valid_rows())
        return result

    def export_csv(self, path: Path, flt: TransactionFilter) -> int:
        """조건에 맞는 거래를 CSV 로 저장한다.

        [역할]
        - 출력 폴더가 없으면 만든다. 같은 파일이 있으면 덮어쓴다.
        - 헤더를 먼저 쓰고, 거래를 스트리밍으로 한 줄씩 쓴다. (tags 는 'a,b' 문자열)
        - 임시 파일에 다 쓴 뒤 원자적으로 교체해, 실패해도 기존 파일이 깨지지 않는다.

        Args:
            path: 저장할 CSV 경로
            flt: 내보낼 거래 조건
        Returns:
            저장한 거래 건수
        Raises:
            ValidationError: 경로가 폴더
            StorageError: 쓰기 실패
        """
        if path.exists() and path.is_dir():
            raise ValidationError(f"출력 경로가 폴더입니다: {path}", "파일 이름까지 지정하세요. 예: --out out/2026-11.csv")
        tmp_path = None
        count = 0
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fp:
                writer = csv.writer(fp)
                writer.writerow(config.CSV_COLUMNS)
                for tx in self._transactions.iter_matching(flt):
                    writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, ",".join(tx.tags)])
                    count += 1
            apply_file_mode(tmp_path, path)
            os.replace(tmp_path, path)
            tmp_path = None
        except OSError as exc:
            raise StorageError(f"CSV 파일을 쓸 수 없습니다: {path} ({exc.strerror or exc})",
                               "출력 폴더의 권한과 경로를 확인하세요.") from None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return count
