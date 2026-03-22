class MillicallError(Exception):
    pass


class ExtensionNotFoundError(MillicallError):
    def __init__(self, extension_id: int):
        super().__init__(f"Extension {extension_id} not found")


class PeerNotFoundError(MillicallError):
    def __init__(self, peer_id: int):
        super().__init__(f"Peer {peer_id} not found")


class DuplicateExtensionError(MillicallError):
    def __init__(self, number: str):
        super().__init__(f"Extension number {number} already exists")


class DuplicatePeerError(MillicallError):
    def __init__(self, username: str):
        super().__init__(f"Peer username {username} already exists")


class AsteriskReloadError(MillicallError):
    def __init__(self, detail: str):
        super().__init__(f"Asterisk reload failed: {detail}")
