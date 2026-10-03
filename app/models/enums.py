from enum import StrEnum


class ActionStatus(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class DecisionStatus(StrEnum):
    candidate = "candidate"
    rejected = "rejected"
    changed = "changed"
    draft = "draft"
    confirmed = "confirmed"


class AnalysisStatus(StrEnum):
    draft = "draft"
    confirmed = "confirmed"


class NotionSyncStatus(StrEnum):
    not_connected = "NOT_CONNECTED"
    not_synced = "NOT_SYNCED"
    synced = "SYNCED"
    outdated = "OUTDATED"
    error = "ERROR"

