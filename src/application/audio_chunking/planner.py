from .dtos import AudioChunk, AudioChunkingOptions


def plan_audio_chunks(
    *,
    duration_ms: int,
    boundaries: tuple[int, ...],
    options: AudioChunkingOptions,
) -> tuple[AudioChunk, ...]:
    """Строит план разбиения аудио на чанки.

    Планировщик работает только с временными диапазонами и не выполняет
    физическое разбиение аудиофайла.

    Границы чанков по возможности выбираются около ``target_duration_ms``
    из переданного набора безопасных точек ``boundaries``. Если подходящей
    границы нет, используется принудительное разбиение не позднее
    ``max_duration_ms``.

    Для каждого чанка формируются две временные области:

    - ``start_ms`` / ``end_ms`` — фактический диапазон аудио, который
      необходимо передать распознавателю. Он расширяется на ``overlap_ms``;
    - ``accepted_start_ms`` / ``accepted_end_ms`` — диапазон результата,
      который должен быть принят при последующем объединении транскрипций.

    Благодаря этому соседние чанки получают небольшой общий контекст,
    но их результаты можно объединить без дублирования текста.

    Последний короткий остаток по возможности не создаётся отдельно:
    планировщик сдвигает предыдущую принудительную границу так, чтобы
    остаток был не короче ``min_duration_ms``.

    Args:
        duration_ms: Полная длительность аудио в миллисекундах.
        boundaries: Безопасные точки разбиения в абсолютных миллисекундах
            от начала аудио, например найденные VAD или silence detector.
        options: Настройки планирования чанков.

    Returns:
        Последовательность чанков в хронологическом порядке.

    Raises:
        ValueError: Если длительность или настройки chunking некорректны.
    """

    _validate_options(duration_ms=duration_ms, options=options)

    if duration_ms == 0:
        return ()

    normalized_boundaries = tuple(sorted({boundary for boundary in boundaries if 0 < boundary < duration_ms}))

    chunks: list[AudioChunk] = []
    accepted_start_ms = 0

    while accepted_start_ms < duration_ms:

        accepted_end_ms = _select_boundary(
            start_ms=accepted_start_ms,
            duration_ms=duration_ms,
            boundaries=normalized_boundaries,
            options=options,
        )

        if accepted_end_ms <= accepted_start_ms:
            raise RuntimeError(
                f"Chunk boundary must be greater than its start: {accepted_start_ms=} {accepted_end_ms=}",
            )

        start_ms = max(0, accepted_start_ms - options.overlap_ms)
        end_ms = min(duration_ms, accepted_end_ms + options.overlap_ms)

        chunks.append(
            AudioChunk(
                index=len(chunks),
                start_ms=start_ms,
                end_ms=end_ms,
                accepted_start_ms=accepted_start_ms,
                accepted_end_ms=accepted_end_ms,
            )
        )

        accepted_start_ms = accepted_end_ms

    return tuple(chunks)


def _select_boundary(
    *,
    start_ms: int,
    duration_ms: int,
    boundaries: tuple[int, ...],
    options: AudioChunkingOptions,
) -> int:
    """Выбирает конец следующего логического чанка.

    В первую очередь функция ищет безопасную границу около целевой
    длительности чанка. Поиск ограничивается:

    - минимальной длительностью чанка;
    - окном ``boundary_search_ms`` вокруг целевой точки;
    - максимальной длительностью чанка;
    - полной длительностью аудио.

    Из подходящих границ выбирается ближайшая к целевой точке.

    Граница, после которой остаётся ненулевой фрагмент короче
    ``min_duration_ms``, игнорируется, чтобы не создавать слишком
    маленький последний чанк.

    Если безопасной границы нет, выполняется принудительное разбиение.
    При этом конечная точка по возможности сдвигается назад так, чтобы
    оставшийся последний фрагмент имел хотя бы ``min_duration_ms``.

    Args:
        start_ms: Начало логического чанка в абсолютных миллисекундах.
        duration_ms: Полная длительность аудио.
        boundaries: Доступные безопасные точки разбиения.
        options: Настройки chunking.

    Returns:
        Абсолютную позицию конца чанка в миллисекундах.
    """

    remaining_ms = duration_ms - start_ms

    if remaining_ms <= options.max_duration_ms:
        return duration_ms

    target = start_ms + options.target_duration_ms

    search_start = max(start_ms + options.min_duration_ms, target - options.boundary_search_ms)
    search_end = min(duration_ms, target + options.boundary_search_ms, start_ms + options.max_duration_ms)

    candidates = [
        boundary
        for boundary in boundaries
        if (
            search_start <= boundary <= search_end
            and _has_valid_tail(
                boundary_ms=boundary,
                duration_ms=duration_ms,
                min_duration_ms=options.min_duration_ms,
            )
        )
    ]

    if candidates:
        return min(candidates, key=lambda boundary: (abs(boundary - target), boundary))

    hard_boundary = min(start_ms + options.max_duration_ms, duration_ms)
    tail_duration = duration_ms - hard_boundary

    if 0 < tail_duration < options.min_duration_ms:
        adjusted_boundary = duration_ms - options.min_duration_ms

        if adjusted_boundary - start_ms >= options.min_duration_ms:
            return adjusted_boundary

    return hard_boundary


def _has_valid_tail(*, boundary_ms: int, duration_ms: int, min_duration_ms: int) -> bool:
    """Проверяет, что после границы не останется слишком короткий хвост."""
    tail_duration = duration_ms - boundary_ms
    return tail_duration == 0 or tail_duration >= min_duration_ms


def _validate_options(*, duration_ms: int, options: AudioChunkingOptions,) -> None:
    """Проверяет базовые инварианты параметров планирования."""

    if duration_ms < 0:
        raise ValueError("duration_ms must be >= 0")

    if options.min_duration_ms <= 0:
        raise ValueError("min_duration_ms must be > 0")

    if options.target_duration_ms < options.min_duration_ms:
        raise ValueError("target_duration_ms must be >= min_duration_ms")

    if options.max_duration_ms < options.target_duration_ms:
        raise ValueError("max_duration_ms must be >= target_duration_ms")

    if options.boundary_search_ms < 0:
        raise ValueError("boundary_search_ms must be >= 0")

    if options.overlap_ms < 0:
        raise ValueError("overlap_ms must be >= 0")
