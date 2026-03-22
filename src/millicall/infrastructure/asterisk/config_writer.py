import fcntl
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from millicall.config import settings
from millicall.domain.models import AIAgent, Extension, Peer


@dataclass
class TrunkConfig:
    enabled: bool = False
    host: str = ""
    username: str = ""
    password: str = ""
    did_number: str = ""
    caller_id: str = ""
    incoming_dest: str = ""  # Extension to ring on incoming PSTN calls


class AsteriskConfigWriter:
    def __init__(
        self,
        templates_dir: Path | None = None,
        output_dir: Path | None = None,
    ):
        self.templates_dir = templates_dir or settings.asterisk_templates_dir
        self.output_dir = output_dir or settings.asterisk_config_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            keep_trailing_newline=True,
        )

    def write_pjsip_config(
        self,
        peers: list[Peer],
        bind_address: str | None = None,
        trunk: TrunkConfig | None = None,
    ) -> Path:
        template = self.env.get_template("pjsip.conf.j2")
        content = template.render(
            peers=peers,
            bind_address=bind_address or settings.pbx_bind_address,
            trunk=trunk or TrunkConfig(),
        )
        output_path = self.output_dir / "pjsip.conf"
        self._write_locked(output_path, content)
        return output_path

    def write_extensions_config(
        self,
        extensions: list[Extension],
        peer_map: dict[int, Peer],
        ai_agents: list[AIAgent] | None = None,
        trunk: TrunkConfig | None = None,
    ) -> Path:
        template = self.env.get_template("extensions.conf.j2")

        ext_with_peers = []
        for ext in extensions:
            peer = peer_map.get(ext.peer_id) if ext.peer_id else None
            ext_with_peers.append({"ext": ext, "peer": peer})

        content = template.render(
            extensions=ext_with_peers,
            ai_agents=ai_agents or [],
            trunk=trunk or TrunkConfig(),
        )
        output_path = self.output_dir / "extensions.conf"
        self._write_locked(output_path, content)
        return output_path

    def _write_locked(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(content)
            f.flush()
