import hashlib
import uuid


def offline_uuid(player_name) -> str:
    """
    生成一个离线 UUID
    Args:
        player_name (str): 玩家名

    Returns:
        str: UUID v3
    """
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{player_name}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0f) | 0x30  # 版本号设为 3
    digest[8] = (digest[8] & 0x3f) | 0x80  # 变体位设为 RFC 4122
    return str(uuid.UUID(bytes=bytes(digest)))
