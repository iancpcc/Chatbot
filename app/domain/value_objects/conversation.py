from enum import StrEnum


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ConversationType(StrEnum):
    CHAT = "chat"
    VOICE = "voice"
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    AUDIO = "audio"
    VIDEO_MESSAGE = "video_message"
