"""분석 작업 세대(generation) 관리 — 취소와 중복 실행 방지.

작업을 시작할 때 세대 번호를 받고, 확인 지점마다 아직 최신 세대인지 확인한다.
취소하면 세대가 올라가서 진행 중이던 작업은 다음 확인 지점에서 스스로 멈춘다.
진행 중인 OpenAI 요청 자체는 끊지 못하므로, 그 결과는 받은 뒤 버린다.
(uvicorn worker 1개 전제 — 10장)
"""

import threading
import uuid

_lock = threading.Lock()
_stt: dict[uuid.UUID, int] = {}
_ai: dict[uuid.UUID, int] = {}


class Cancelled(Exception):
    pass


def _bump(table: dict[uuid.UUID, int], episode_id: uuid.UUID) -> int:
    with _lock:
        table[episode_id] = table.get(episode_id, 0) + 1
        return table[episode_id]


def _current(table: dict[uuid.UUID, int], episode_id: uuid.UUID) -> int:
    with _lock:
        return table.get(episode_id, 0)


def start_stt(episode_id: uuid.UUID) -> int:
    return _bump(_stt, episode_id)


def cancel_stt(episode_id: uuid.UUID) -> None:
    _bump(_stt, episode_id)


def stt_alive(episode_id: uuid.UUID, gen: int) -> bool:
    return _current(_stt, episode_id) == gen


def start_ai(episode_id: uuid.UUID) -> int:
    return _bump(_ai, episode_id)


def cancel_ai(episode_id: uuid.UUID) -> None:
    _bump(_ai, episode_id)


def ai_alive(episode_id: uuid.UUID, gen: int) -> bool:
    return _current(_ai, episode_id) == gen
