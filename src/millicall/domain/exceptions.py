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


class TrunkNotFoundError(MillicallError):
    def __init__(self, trunk_id: int):
        super().__init__(f"Trunk {trunk_id} not found")


class DuplicateTrunkError(MillicallError):
    def __init__(self, name: str):
        super().__init__(f"Trunk name {name} already exists")


class AsteriskReloadError(MillicallError):
    def __init__(self, detail: str):
        super().__init__(f"Asterisk reload failed: {detail}")


class WorkflowNotFoundError(MillicallError):
    def __init__(self, workflow_id: int):
        super().__init__(f"Workflow {workflow_id} not found")


class ContactNotFoundError(MillicallError):
    def __init__(self, contact_id: int):
        super().__init__(f"Contact {contact_id} not found")
