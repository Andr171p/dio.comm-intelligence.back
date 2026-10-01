from typing import Annotated

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from typing_extensions import Doc

type Silence = tuple[int, int]
"""Интервал тишины (начало, конец) в миллисекундах."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AudioChunk:
    """Фрагмент записи для распознавания.

    Фрагмент нарезается с перекрытием ``[start_ms, end_ms)``, но владеет только своим
    интервалом ``[own_from_ms, own_to_ms)`` - границы проходят по тишине,
    перекрытие нужно для контекста модели и сопоставления спикеров соседних фрагментов.
    """

    index: int
    start_ms: Annotated[int, Doc("Начало нарезки (с учётом перекрытия)")]
    end_ms: Annotated[int, Doc("Конец нарезки (с учётом перекрытия)")]
    own_from_ms: Annotated[int, Doc("Начало собственного интервала")]
    own_to_ms: Annotated[int, Doc("Конец собственного интервала")]


def _find_cut(silences: Sequence[Silence], target_ms: int, search_ms: int) -> int:
    """Возвращает точку разреза: середину самой длинной паузы рядом с целевой точкой."""

    candidates = [
        (start, end)
        for start, end in silences
        if abs((start + end) // 2 - target_ms) <= search_ms
    ]
    if not candidates:
        return target_ms

    start, end = max(candidates, key=lambda silence: silence[1] - silence[0])
    return (start + end) // 2


def plan_chunks(
    duration_ms: int,
    silences: Sequence[Silence],
    *,
    target_ms: int,
    overlap_ms: int,
    search_ms: int,
) -> tuple[AudioChunk, ...]:
    """Разбивает запись на фрагменты ~target_ms, разрезая по паузам.

    Запись не длиннее ``target_ms + search_ms`` не разбивается.
    Если рядом с целевой точкой паузы нет, режем по целевой точке (спасает перекрытие).
    """

    cuts: list[int] = []
    position = 0

    while duration_ms - position > target_ms + search_ms:
        position = _find_cut(silences, position + target_ms, search_ms)
        cuts.append(position)

    return tuple(
        AudioChunk(
            index=index,
            start_ms=max(0, own_from - overlap_ms),
            end_ms=min(duration_ms, own_to + overlap_ms),
            own_from_ms=own_from,
            own_to_ms=own_to,
        )
        for index, (own_from, own_to) in enumerate(pairwise((0, *cuts, duration_ms)))
    )


__all__ = ["AudioChunk", "Silence", "plan_chunks"]
