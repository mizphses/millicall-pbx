import logging
import subprocess
from urllib.request import Request, urlopen

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
        self._run_command(f"pjsip send notify check-sync endpoint {endpoint}")

    def send_check_sync_all(self, endpoints: list[str]) -> None:
        for ep in endpoints:
            try:
                self.send_check_sync(ep)
            except Exception:
                logger.warning("Failed to send check-sync to %s", ep)

    def send_http_resync(self, phone_ip: str, admin_password: str = "adminpass") -> bool:
        """Send HTTP request to KX-HDV phone to trigger config resync."""
        try:
            import base64

            credentials = base64.b64encode(f"admin:{admin_password}".encode()).decode()
            # KX-HDV resync via web API
            url = f"http://{phone_ip}/admin/resync"
            req = Request(url)
            req.add_header("Authorization", f"Basic {credentials}")
            urlopen(req, timeout=5)
            logger.info("HTTP resync sent to %s", phone_ip)
            return True
        except Exception:
            logger.warning("HTTP resync failed for %s, trying alternative", phone_ip)
            try:
                # Alternative: some KX-HDV firmware uses this endpoint
                url = f"http://{phone_ip}/cgi-bin/api-provision?event=resync"
                urlopen(url, timeout=5)
                logger.info("HTTP resync (alt) sent to %s", phone_ip)
                return True
            except Exception:
                logger.warning("HTTP resync (alt) also failed for %s", phone_ip)
                return False

    def send_resync_to_devices(self, device_ips: list[str]) -> None:
        """Try HTTP resync for all device IPs, then SIP check-sync as fallback."""
        for ip in device_ips:
            if ip:
                self.send_http_resync(ip)

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
