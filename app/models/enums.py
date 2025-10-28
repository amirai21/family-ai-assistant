from enum import Enum

class MemberRole(str, Enum):
    parent = "parent"
    child = "child"
    caregiver = "caregiver"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    canceled = "canceled"


class MsgDirection(str, Enum):
    outgoing = "outgoing"
    incoming = "incoming"


class MsgStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class RecurrenceFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"