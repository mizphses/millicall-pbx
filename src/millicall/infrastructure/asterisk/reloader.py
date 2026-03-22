import logging
import subprocess

from millicall.domain.exceptions import AsteriskReloadError

logger = logging.getLogger(__name__)


class AsteriskReloader:
    def reload_pjsip(self) -> None:
        self._run_command("pjsip reload")

    def reload_dialplan(self) -> None:
        self._run_command("dialplan reload")

    def reload_all(self) -> None:
        self.reload_pjsip()
        self.reload_dialplan()

    def send_check_sync(self, endpoint: str) -> None:
        """Send SIP NOTIFY with check-sync event to trigger phone reprovisioning."""
        self._run_command(
            f'pjsip send notify check-sync endpoint {endpoint}'
        )

    def send_check_sync_all(self, endpoints: list[str]) -> None:
        for ep in endpoints:
            try:
                self.send_check_sync(ep)
            except Exception:
                logger.warning("Failed to send check-sync to %s", ep)

    def _run_command(self, command: str) -> None:
        try:
            result = subprocess.run(
                ["asterisk", "-rx", command],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error("Asterisk command failed: %s -> %s", command, result.stderr)
                raise AsteriskReloadError(result.stderr)
            logger.info("Asterisk command OK: %s", command)
        except FileNotFoundError:
            logger.warning("Asterisk binary not found, skipping reload")
        except subprocess.TimeoutExpired:
            raise AsteriskReloadError(f"Timeout running: {command}")
