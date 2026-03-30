"""Lightweight LDAP server for phone directory.

Serves Millicall contacts and extensions via LDAP protocol,
compatible with Panasonic KX-HDV and Yealink phonebook lookup.
"""

import contextlib
import logging
import threading

from ldaptor.inmemory import ReadOnlyInMemoryLDAPEntry
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from ldaptor.protocols.pureldap import (
    LDAPBindResponse,
    LDAPSearchResultDone,
    LDAPSearchResultEntry,
)
from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory

logger = logging.getLogger(__name__)

BASE_DN = "dc=millicall,dc=local"
LDAP_PORT = 10389

# Global tree reference
_directory_root: ReadOnlyInMemoryLDAPEntry | None = None


def _build_tree(contacts: list[dict], extensions: list[dict]) -> ReadOnlyInMemoryLDAPEntry:
    """Build LDAP directory tree from contacts and extensions."""
    root = ReadOnlyInMemoryLDAPEntry(
        dn=BASE_DN,
        attributes={
            "objectClass": ["dcObject", "organization"],
            "dc": ["millicall"],
            "o": ["Millicall PBX"],
        },
    )
    ou = root.addChild(
        rdn="ou=contacts",
        attributes={"objectClass": ["organizationalUnit"], "ou": ["contacts"]},
    )

    seen: set[str] = set()

    for ext in extensions:
        if ext.get("enabled"):
            cn = ext.get("display_name", ext.get("number", ""))
            number = ext.get("number", "")
            if cn and number and cn not in seen:
                seen.add(cn)
                with contextlib.suppress(Exception):
                    ou.addChild(
                        rdn=f"cn={cn}",
                        attributes={
                            "objectClass": ["inetOrgPerson"],
                            "cn": [cn],
                            "sn": [cn],
                            "telephoneNumber": [number],
                        },
                    )

    for c in contacts:
        cn = c.get("name", "")
        number = c.get("phone_number", "")
        if cn and number and cn not in seen:
            seen.add(cn)
            attrs: dict[str, list[str]] = {
                "objectClass": ["inetOrgPerson"],
                "cn": [cn],
                "sn": [cn],
                "telephoneNumber": [number],
            }
            if c.get("company"):
                attrs["o"] = [c["company"]]
            with contextlib.suppress(Exception):
                ou.addChild(rdn=f"cn={cn}", attributes=attrs)

    return root


def _match_filter(entry_attrs: dict, ldap_filter) -> bool:
    """Simple LDAP filter matching against entry attributes."""
    from ldaptor.protocols import pureldap

    if ldap_filter is None:
        return True

    if isinstance(ldap_filter, pureldap.LDAPFilter_present):
        attr_name = ldap_filter.value.decode() if isinstance(ldap_filter.value, bytes) else str(ldap_filter.value)
        return attr_name.lower() in {k.lower() for k in entry_attrs}

    if isinstance(ldap_filter, pureldap.LDAPFilter_equalityMatch):
        attr = ldap_filter.attributeDesc.value.decode() if hasattr(ldap_filter.attributeDesc, 'value') else str(ldap_filter.attributeDesc)
        val = ldap_filter.assertionValue.value.decode() if hasattr(ldap_filter.assertionValue, 'value') else str(ldap_filter.assertionValue)
        for k, vs in entry_attrs.items():
            if k.lower() == attr.lower():
                for v in vs:
                    if v.lower() == val.lower():
                        return True
        return False

    if isinstance(ldap_filter, pureldap.LDAPFilter_substrings):
        attr = ldap_filter.type.decode() if isinstance(ldap_filter.type, bytes) else str(ldap_filter.type)
        for k, vs in entry_attrs.items():
            if k.lower() == attr.lower():
                for v in vs:
                    # Simple substring match - just check if any substring is in value
                    for sub in ldap_filter.substrings:
                        sub_val = sub.value.decode() if isinstance(sub.value, bytes) else str(sub.value)
                        if sub_val.lower() in v.lower():
                            return True
        return False

    if isinstance(ldap_filter, pureldap.LDAPFilter_or):
        return any(_match_filter(entry_attrs, f) for f in ldap_filter)

    if isinstance(ldap_filter, pureldap.LDAPFilter_and):
        return all(_match_filter(entry_attrs, f) for f in ldap_filter)

    if isinstance(ldap_filter, pureldap.LDAPFilter_not):
        return not _match_filter(entry_attrs, ldap_filter.value)

    # Unknown filter type — match everything
    return True


class MillicallLDAPServer(LDAPServer):
    """LDAP server that serves phone directory via LDAP."""

    def handle_LDAPBindRequest(self, request, controls, reply):  # noqa: N802
        """Allow anonymous bind."""
        return reply(LDAPBindResponse(resultCode=0))

    def handle_LDAPSearchRequest(self, request, controls, reply):  # noqa: N802
        """Handle search requests using in-memory directory."""
        global _directory_root  # noqa: PLW0602

        if _directory_root is None:
            return reply(LDAPSearchResultDone(resultCode=53))  # unwillingToPerform

        # Get all entries under ou=contacts
        entries = []
        for _child_dn, child in _directory_root._children.items():
            for _entry_dn, entry in child._children.items():
                # Build attributes dict
                attrs = {}
                for attr_key, attr_vals in entry._attributes.items():
                    key = attr_key.decode() if isinstance(attr_key, bytes) else str(attr_key)
                    vals = []
                    for v in attr_vals:
                        vals.append(v.decode() if isinstance(v, bytes) else str(v))
                    attrs[key] = vals

                # Apply filter
                if _match_filter(attrs, request.filter):
                    dn = entry.dn.getText() if hasattr(entry.dn, 'getText') else str(entry.dn)
                    # Build attribute list for response
                    attr_list = []
                    for k, vs in attrs.items():
                        attr_list.append((k, [v.encode() if isinstance(v, str) else v for v in vs]))
                    entries.append((dn, attr_list))

        # Send results
        for dn, attr_list in entries:
            reply(LDAPSearchResultEntry(
                objectName=dn,
                attributes=attr_list,
            ))

        return reply(LDAPSearchResultDone(resultCode=0))


class LDAPServerFactory(ServerFactory):
    protocol = MillicallLDAPServer


_ldap_thread: threading.Thread | None = None
_running = False


def _fetch_data() -> tuple[list[dict], list[dict]]:
    """Synchronously fetch contacts and extensions from DB."""
    import asyncio as _asyncio

    async def _get():
        from millicall.infrastructure.database import async_session
        from millicall.infrastructure.repositories.contact_repo import ContactRepository
        from millicall.infrastructure.repositories.extension_repo import ExtensionRepository

        async with async_session() as session:
            contact_repo = ContactRepository(session)
            ext_repo = ExtensionRepository(session)
            contacts_list = await contact_repo.get_all()
            extensions_list = await ext_repo.get_all()

        return (
            [{"name": c.name, "phone_number": c.phone_number, "company": c.company, "department": c.department} for c in contacts_list],
            [{"number": e.number, "display_name": e.display_name, "enabled": e.enabled} for e in extensions_list],
        )

    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_get())
    finally:
        loop.close()


def _run_ldap_server(port: int) -> None:
    """Run LDAP server in Twisted reactor."""
    global _running, _directory_root  # noqa: PLW0603
    _running = True

    try:
        contacts, extensions = _fetch_data()
        _directory_root = _build_tree(contacts, extensions)
        factory = LDAPServerFactory()
        reactor.listenTCP(port, factory)  # type: ignore[attr-defined]
        logger.info("LDAP server listening on port %d (%d entries)", port, len(contacts) + len(extensions))
        reactor.run(installSignalHandlers=False)  # type: ignore[attr-defined]
    except Exception:
        logger.exception("LDAP server failed")
    finally:
        _running = False


def start_ldap_server(port: int = 10389) -> None:
    """Start LDAP server in a background thread."""
    global _ldap_thread  # noqa: PLW0603
    if _ldap_thread and _ldap_thread.is_alive():
        return

    _ldap_thread = threading.Thread(target=_run_ldap_server, args=(port,), daemon=True)
    _ldap_thread.start()
    logger.info("LDAP server thread started on port %d", port)
