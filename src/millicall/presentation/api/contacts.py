from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Contact, User
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.contact_repo import ContactRepository
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import ContactCreate, ContactResponse, ContactUpdate

router = APIRouter(
    prefix="/api/contacts",
    tags=["contacts"],
    dependencies=[Depends(get_current_user)],
)


def _to_response(c: Contact) -> ContactResponse:
    return ContactResponse(
        id=c.id,
        name=c.name,
        phone_number=c.phone_number,
        company=c.company,
        department=c.department,
        notes=c.notes,
    )


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    q: str = Query(default="", description="Search query for name, phone number, or company"),
    session: AsyncSession = Depends(get_session),
):
    repo = ContactRepository(session)
    if q.strip():
        contacts = await repo.search(q.strip())
    else:
        contacts = await repo.get_all()
    return [_to_response(c) for c in contacts]


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: int, session: AsyncSession = Depends(get_session)):
    repo = ContactRepository(session)
    c = await repo.get_by_id(contact_id)
    return _to_response(c)


@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = ContactRepository(session)
    c = await repo.create(
        Contact(
            name=data.name,
            phone_number=data.phone_number,
            company=data.company,
            department=data.department,
            notes=data.notes,
        )
    )
    return _to_response(c)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = ContactRepository(session)
    c = await repo.update(
        Contact(
            id=contact_id,
            name=data.name,
            phone_number=data.phone_number,
            company=data.company,
            department=data.department,
            notes=data.notes,
        )
    )
    return _to_response(c)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = ContactRepository(session)
    await repo.delete(contact_id)
