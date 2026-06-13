from __future__ import annotations

import threading
import time

from enterprise_agent.memory.locks import SessionLockManager


def test_same_session_is_serialized_and_different_sessions_can_overlap() -> None:
    manager = SessionLockManager()
    active = 0
    same_session_peak = 0
    guard = threading.Lock()

    def same_session_worker() -> None:
        nonlocal active, same_session_peak
        with manager.acquire("user-1", "thread-1", timeout=1):
            with guard:
                active += 1
                same_session_peak = max(same_session_peak, active)
            time.sleep(0.03)
            with guard:
                active -= 1

    threads = [threading.Thread(target=same_session_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert same_session_peak == 1

    barrier = threading.Barrier(2)
    overlap = []

    def different_session_worker(thread_id: str) -> None:
        with manager.acquire("user-1", thread_id, timeout=1):
            barrier.wait(timeout=1)
            overlap.append(thread_id)

    threads = [
        threading.Thread(target=different_session_worker, args=("thread-a",)),
        threading.Thread(target=different_session_worker, args=("thread-b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert set(overlap) == {"thread-a", "thread-b"}
