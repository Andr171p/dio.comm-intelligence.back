from enum import StrEnum


class CommunicationType(StrEnum):
    CONFERENCE = "conference"
    CALL = "call"
    CHAT = "chat"


class RepresentationType(StrEnum):
    TRANSCRIPT = "transcript"
    CHAT = "chat"
    TEXT = "text"
