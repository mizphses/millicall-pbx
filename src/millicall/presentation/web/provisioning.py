"""Provisioning endpoints for Panasonic KX-HDV and Yealink phones."""

import logging
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.provisioning_service import ProvisioningService
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.contact_repo import ContactRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/provisioning", tags=["provisioning"])

# ── Panasonic KX-HDV ─────────────────────────────────────────────


@router.get("/Panasonic/ConfigCommon.cfg")
@router.get("/ConfigCommon.cfg")
async def common_config(session: AsyncSession = Depends(get_session)):
    service = ProvisioningService(session)
    content = service.generate_common_config()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Panasonic/Config{mac_address}.cfg")
@router.get("/Config{mac_address}.cfg")
async def device_config(mac_address: str, session: AsyncSession = Depends(get_session)):
    service = ProvisioningService(session)
    content = await service.generate_device_config(mac_address)
    if content is None:
        return PlainTextResponse(
            "# Panasonic SIP Phone Standard Format File #\n# No configuration assigned\n",
            media_type="text/plain",
        )
    return PlainTextResponse(content, media_type="text/plain")


# ── Remote Phonebook (XML) ─────────────────────────────────────


@router.get("/phonebook/panasonic.xml")
async def panasonic_phonebook(session: AsyncSession = Depends(get_session)):
    """Panasonic XML phonebook — used by XMLAPP_LDAP_URL."""
    contact_repo = ContactRepository(session)
    ext_repo = ExtensionRepository(session)

    contacts = await contact_repo.get_all()
    extensions = await ext_repo.get_all()

    # Panasonic XML format
    root = Element("PhoneDirectory")

    # Add internal extensions
    for ext in extensions:
        if ext.enabled:
            entry = SubElement(root, "DirectoryEntry")
            SubElement(entry, "Name").text = ext.display_name
            SubElement(entry, "Telephone").text = ext.number

    # Add contacts
    for c in contacts:
        entry = SubElement(root, "DirectoryEntry")
        SubElement(entry, "Name").text = c.name
        SubElement(entry, "Telephone").text = c.phone_number

    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode").encode("utf-8")
    return Response(content=xml_bytes, media_type="text/xml")


@router.get("/phonebook/yealink.xml")
async def yealink_phonebook(session: AsyncSession = Depends(get_session)):
    """Yealink XML phonebook — used by remote_phonebook.data.N.url."""
    contact_repo = ContactRepository(session)
    ext_repo = ExtensionRepository(session)

    contacts = await contact_repo.get_all()
    extensions = await ext_repo.get_all()

    # Yealink XML format
    root = Element("YealinkIPPhoneDirectory")

    # Add internal extensions
    for ext in extensions:
        if ext.enabled:
            entry = SubElement(root, "DirectoryEntry")
            SubElement(entry, "Name").text = ext.display_name
            tel = SubElement(entry, "Telephone")
            tel.text = ext.number

    # Add contacts
    for c in contacts:
        entry = SubElement(root, "DirectoryEntry")
        SubElement(entry, "Name").text = c.name
        tel = SubElement(entry, "Telephone")
        tel.text = c.phone_number

    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode").encode("utf-8")
    return Response(content=xml_bytes, media_type="text/xml")


# ── Yealink ──────────────────────────────────────────────────────
# Routes under /Yealink/ and also at root level so that DHCP option 66
# pointing to /provisioning/ works for both Panasonic and Yealink.


@router.get("/Yealink/y000000000000.boot")
@router.get("/y000000000000.boot")
async def yealink_boot(session: AsyncSession = Depends(get_session)):
    """Boot file — all Yealink models request this on startup."""
    service = ProvisioningService(session)
    content = service.generate_yealink_boot()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Yealink/{boot_file}.boot")
@router.get("/{boot_file}.boot")
async def yealink_model_boot(boot_file: str, session: AsyncSession = Depends(get_session)):
    """Model-specific boot file (e.g. y000000000042 for T43U) — same content."""
    service = ProvisioningService(session)
    content = service.generate_yealink_boot()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Yealink/common.cfg")
async def yealink_common_config(session: AsyncSession = Depends(get_session)):
    """Common configuration shared by all Yealink phones."""
    service = ProvisioningService(session)
    content = service.generate_yealink_common_config()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Yealink/{mac_address}.cfg")
async def yealink_device_config(mac_address: str, session: AsyncSession = Depends(get_session)):
    """Per-device config — MAC address without separators (e.g. 805ec0a1b2c3.cfg)."""
    logger.info("Yealink provisioning request for MAC: %s", mac_address)
    service = ProvisioningService(session)
    content = await service.generate_yealink_device_config(mac_address)
    if content is None:
        return PlainTextResponse(
            "#!version:1.0.0.1\n## No configuration assigned\n",
            media_type="text/plain",
        )
    return PlainTextResponse(content, media_type="text/plain")
