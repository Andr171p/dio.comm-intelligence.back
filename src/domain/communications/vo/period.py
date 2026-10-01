from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class Period:
    started_at: datetime
    ended_at: datetime

    def __post_init__(self) -> None:
        if self.ended_at < self.started_at:
            raise ValueError("The end time cannot be earlier than the start time.")

    @property
    def duration(self) -> timedelta:
        return self.ended_at - self.started_at
