"""백그라운드 선생성 단일성 락 — (book_id, idx) 단위 중복 생성 방지(학생/06 정본).

04(Bible·1장)·06(다음 장)·15(전결)·13(학습) 선생성이 한 책에서 동시에 돌 수 있어,
같은 `(book_id, idx)` 를 두 번 만들지 않도록 인메모리 가드를 공유한다. 단일 프로세스
uvicorn 전제(현 운영). 멀티워커 격상 시 advisory lock/DB 락으로 교체.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_inflight: set[tuple[str, str]] = set()


def acquire_prefetch(book_id: str, idx: int | str) -> bool:
    """선생성 시작 권한을 얻으면 True. 이미 진행 중이면 False(skip)."""
    key = (book_id, str(idx))
    with _lock:
        if key in _inflight:
            return False
        _inflight.add(key)
        return True


def release_prefetch(book_id: str, idx: int | str) -> None:
    key = (book_id, str(idx))
    with _lock:
        _inflight.discard(key)


def is_inflight(book_id: str, idx: int | str) -> bool:
    with _lock:
        return (book_id, str(idx)) in _inflight
