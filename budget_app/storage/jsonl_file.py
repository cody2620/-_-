"""JSONL 파일 저수준 I/O.

[파일 역할]
- 한 줄에 JSON 객체 하나를 저장하는 파일을 다룬다.
- 스트리밍 읽기: 제너레이터로 한 줄씩 읽어 파일 전체를 메모리에 올리지 않는다.
- 추가(append): 새 레코드를 파일 끝에 붙인다.
- 재작성(rewrite): 임시 파일에 전체를 쓴 뒤 os.replace로 원자적 교체한다.
  (update/delete 도중 실패해도 원본이 깨지지 않음)
- OS 오류는 모두 StorageError(원인 + 힌트)로 바꿔 올려보낸다.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Tuple

from ..core.errors import DataFileError, StorageError


def apply_file_mode(tmp_path: str, target: Path) -> None:
    """임시 파일에 알맞은 파일 권한을 적용한다.

    [역할] tempfile.mkstemp 는 보안상 0600(본인만 읽기/쓰기) 권한으로 파일을 만든다.
    원자적 교체 후에도 권한이 바뀌지 않도록, 원본이 있으면 원본 권한을 복사하고
    없으면 일반 파일처럼 umask 기준 기본 권한(보통 0644)을 준다.

    Args:
        tmp_path: 임시 파일 경로
        target: 최종적으로 교체될 파일 경로
    """
    if target.exists():
        shutil.copymode(str(target), tmp_path)
    else:
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp_path, 0o666 & ~umask)


def _io_error(action: str, path: Path, exc: OSError) -> StorageError:
    """OSError를 사용자용 StorageError로 바꾼다.

    Args:
        action: '읽을', '쓸' 처럼 문장에 들어갈 동작
        path: 문제가 된 파일
        exc: 원래 OSError
    Returns:
        원인 + 힌트가 담긴 StorageError
    """
    return StorageError(f"{path} 파일을 {action} 수 없습니다: {exc.strerror or exc}",
                        "파일/폴더 권한과 경로를 확인하거나 --data-dir 로 다른 저장 폴더를 지정하세요.")


class JsonlFile:
    """한 줄에 JSON 객체 하나를 저장하는 파일.

    [역할] Repository 들이 공통으로 쓰는 파일 읽기/쓰기 기능을 제공한다.
    """

    def __init__(self, path: Path) -> None:
        """다룰 파일 경로를 저장한다. (파일은 아직 만들지 않음)"""
        self.path = path

    def ensure_exists(self) -> bool:
        """파일이 없으면 빈 파일을 만든다. (초기 실행 시 저장 파일 자동 생성)

        Returns:
            새로 만들었으면 True, 이미 있었으면 False
        Raises:
            StorageError: 같은 이름의 폴더가 있거나 파일을 만들 수 없음
        """
        if self.path.exists():
            if not self.path.is_file():
                raise StorageError(f"{self.path} 는 파일이 아닙니다.", "같은 이름의 폴더를 옮기거나 지우세요.")
            return False
        try:
            self.path.touch()
        except OSError as exc:
            raise _io_error("만들", self.path, exc) from None
        return True

    def iter_records(self) -> Iterator[Tuple[int, Dict[str, Any]]]:
        """파일을 한 줄씩 읽어 (줄 번호, 레코드 dict)를 생성하는 제너레이터.

        [역할] 파일 전체를 메모리에 올리지 않는다. 빈 줄은 건너뛴다.
        손상된 줄을 만나면 줄 번호와 함께 DataFileError를 발생시킨다.

        Yields:
            (줄 번호, dict)
        Raises:
            DataFileError: JSON이 아니거나 객체가 아닌 줄, UTF-8이 아닌 파일
            StorageError: 파일을 읽을 수 없음
        """
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                for lineno, line in enumerate(fp, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        raise DataFileError(f"{self.path.name} {lineno}번째 줄이 올바른 JSON이 아닙니다.",
                                            f"{self.path} 파일의 {lineno}번째 줄을 고치거나 삭제하세요.") from None
                    if not isinstance(record, dict):
                        raise DataFileError(f"{self.path.name} {lineno}번째 줄이 JSON 객체가 아닙니다.",
                                            f"{self.path} 파일의 {lineno}번째 줄을 고치거나 삭제하세요.")
                    yield lineno, record
        except UnicodeDecodeError:
            raise DataFileError(f"{self.path.name} 파일이 UTF-8 인코딩이 아닙니다.",
                                "파일을 UTF-8로 저장하거나 백업 후 삭제하세요.") from None
        except OSError as exc:
            raise _io_error("읽을", self.path, exc) from None

    def is_empty(self) -> bool:
        """레코드가 하나도 없는지 확인한다. (첫 레코드만 읽고 바로 멈춤)"""
        for _ in self.iter_records():
            return False
        return True

    def append_many(self, records: Iterable[Dict[str, Any]]) -> int:
        """여러 레코드를 파일 끝에 추가한다.

        [역할] 레코드를 한 건씩 받아 바로 쓰므로 제너레이터를 넘겨도 메모리를 적게 쓴다.
        마지막에 fsync 로 디스크 기록을 보장한다.

        Args:
            records: dict 들의 iterable
        Returns:
            추가한 레코드 수
        """
        count = 0
        try:
            with self.path.open("a", encoding="utf-8") as fp:
                for record in records:
                    fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
                fp.flush()
                os.fsync(fp.fileno())
        except OSError as exc:
            raise _io_error("쓸", self.path, exc) from None
        return count

    def append(self, record: Dict[str, Any]) -> None:
        """레코드 1건을 파일 끝에 추가한다."""
        self.append_many([record])

    def rewrite(self, records: Iterable[Dict[str, Any]]) -> None:
        """파일 내용을 records 로 통째로 바꾼다. (임시 파일 + 원자적 교체)

        [역할]
        1) 같은 폴더에 임시 파일을 만들고 records 를 모두 쓴다.
        2) fsync → 권한 맞춤 → os.replace 로 원본과 한 번에 교체한다.
        3) 도중에 실패하면 임시 파일만 지우고 원본은 그대로 둔다.
        records 가 원본 파일을 스트리밍으로 읽는 제너레이터여도 안전하다
        (원본은 모든 쓰기가 끝난 뒤에만 교체되기 때문).

        Args:
            records: 새 파일 내용이 될 dict 들의 iterable
        Raises:
            StorageError: 쓰기/교체 실패
        """
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), prefix=f".{self.path.name}.", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                for record in records:
                    fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                fp.flush()
                os.fsync(fp.fileno())
            apply_file_mode(tmp_path, self.path)
            os.replace(tmp_path, self.path)
            tmp_path = None
        except OSError as exc:
            raise _io_error("다시 쓸", self.path, exc) from None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
