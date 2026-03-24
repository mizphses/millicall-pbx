"""Audit logging for security-sensitive operations.

All administrative actions (user management, config changes, etc.)
are logged here for security audit trail.
"""

import logging

logger = logging.getLogger("millicall.audit")

# Ensure audit logger always outputs even if root logger is configured differently
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s AUDIT %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def audit_log(
    action: str,
    actor: str,
    target: str = "",
    detail: str = "",
    client_ip: str = "",
) -> None:
    """Write an audit log entry.

    Args:
        action: The action performed (e.g. "user.create", "user.delete", "password.reset")
        actor: Username of the user who performed the action
        target: The target of the action (e.g. username, resource id)
        detail: Additional detail about the action
        client_ip: Client IP address
    """
    parts = [
        f"action={action}",
        f"actor={actor}",
    ]
    if target:
        parts.append(f"target={target}")
    if detail:
        parts.append(f"detail={detail}")
    if client_ip:
        parts.append(f"ip={client_ip}")

    logger.info(" ".join(parts))
