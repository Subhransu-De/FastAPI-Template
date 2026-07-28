import hashlib
import secrets
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.exceptions import PetClinicConflictError, PetClinicNotFoundError
from app.io.petclinic import (
    OwnerCreate,
    OwnerUpdate,
    PetCreate,
    PetTypeCreate,
    PetTypeUpdate,
    PetUpdate,
    SpecialtyCreate,
    SpecialtyUpdate,
    UserCreate,
    VetCreate,
    VetUpdate,
    VisitCreate,
    VisitNestedCreate,
    VisitUpdate,
)
from app.model import Owner, Pet, PetType, Role, Specialty, User, Vet, Visit
from app.repository import PetClinicRepository


class PetClinicService:
    def __init__(self, repo: PetClinicRepository) -> None:
        self.repo = repo

    async def owners(self, last_name: str | None = None) -> Sequence[Owner]:
        return _require_collection(await self.repo.owners(last_name), "Owners")

    async def owner_page(
        self,
        last_name: str | None,
        page: int,
        size: int,
    ) -> tuple[Sequence[Owner], int]:
        return await self.repo.owner_page(last_name=last_name, page=page, size=size)

    async def owner(self, owner_id: int) -> Owner:
        return _require(await self.repo.owner(owner_id), "Owner", owner_id)

    async def create_owner(self, data: OwnerCreate) -> Owner:
        return await self._save(Owner(**data.model_dump(by_alias=False)))

    async def update_owner(self, owner_id: int, data: OwnerUpdate) -> Owner:
        owner = await self.owner(owner_id)
        for key, value in data.model_dump(by_alias=False).items():
            setattr(owner, key, value)
        return await self._save(owner)

    async def delete_owner(self, owner_id: int) -> None:
        await self.repo.remove(await self.owner(owner_id))

    async def pets(self) -> Sequence[Pet]:
        return _require_collection(await self.repo.pets(), "Pets")

    async def pet_page(self, page: int, size: int) -> tuple[Sequence[Pet], int]:
        return await self.repo.pet_page(page, size)

    async def pet(self, pet_id: int) -> Pet:
        return _require(await self.repo.pet(pet_id), "Pet", pet_id)

    async def owners_pet(self, owner_id: int, pet_id: int) -> Pet:
        await self.owner(owner_id)
        pet = await self.pet(pet_id)
        if pet.owner_id != owner_id:
            resource = "Pet"
            raise PetClinicNotFoundError(resource, pet_id)
        return pet

    async def create_pet(self, owner_id: int, data: PetCreate) -> Pet:
        owner = await self.owner(owner_id)
        pet_type = await self.pet_type(data.type.id)
        pet = Pet(
            name=data.name,
            birth_date=data.birth_date,
            type=pet_type,
            owner=owner,
        )
        return await self._save(pet)

    async def update_pet(self, pet_id: int, data: PetUpdate) -> Pet:
        pet = await self.pet(pet_id)
        pet.name = data.name
        pet.birth_date = data.birth_date
        pet.type = await self.pet_type(data.type.id)
        return await self._save(pet)

    async def update_owners_pet(
        self,
        owner_id: int,
        pet_id: int,
        data: PetUpdate,
    ) -> Pet:
        await self.owners_pet(owner_id, pet_id)
        return await self.update_pet(pet_id, data)

    async def delete_pet(self, pet_id: int) -> None:
        await self.repo.remove(await self.pet(pet_id))

    async def pet_types(self) -> Sequence[PetType]:
        return _require_collection(await self.repo.pet_types(), "Pet types")

    async def pet_type(self, pet_type_id: int) -> PetType:
        return _require(
            await self.repo.pet_type(pet_type_id),
            "Pet type",
            pet_type_id,
        )

    async def create_pet_type(self, data: PetTypeCreate) -> PetType:
        return await self._save(PetType(name=data.name))

    async def update_pet_type(
        self,
        pet_type_id: int,
        data: PetTypeUpdate,
    ) -> PetType:
        pet_type = await self.pet_type(pet_type_id)
        pet_type.name = data.name
        return await self._save(pet_type)

    async def delete_pet_type(self, pet_type_id: int) -> None:
        await self._remove(await self.pet_type(pet_type_id))

    async def visits(self) -> Sequence[Visit]:
        return _require_collection(await self.repo.visits(), "Visits")

    async def visit(self, visit_id: int) -> Visit:
        return _require(await self.repo.visit(visit_id), "Visit", visit_id)

    async def create_visit(self, data: VisitCreate) -> Visit:
        await self.pet(data.pet_id)
        return await self._save(Visit(**data.model_dump(by_alias=False)))

    async def create_nested_visit(
        self,
        owner_id: int,
        pet_id: int,
        data: VisitNestedCreate,
    ) -> Visit:
        await self.owners_pet(owner_id, pet_id)
        return await self._save(Visit(pet_id=pet_id, **data.model_dump(by_alias=False)))

    async def update_visit(self, visit_id: int, data: VisitUpdate) -> Visit:
        visit = await self.visit(visit_id)
        visit.date = data.date
        visit.description = data.description
        return await self._save(visit)

    async def delete_visit(self, visit_id: int) -> None:
        await self.repo.remove(await self.visit(visit_id))

    async def specialties(self) -> Sequence[Specialty]:
        return _require_collection(await self.repo.specialties(), "Specialties")

    async def specialty(self, specialty_id: int) -> Specialty:
        return _require(
            await self.repo.specialty(specialty_id),
            "Specialty",
            specialty_id,
        )

    async def create_specialty(self, data: SpecialtyCreate) -> Specialty:
        return await self._save(Specialty(name=data.name))

    async def update_specialty(
        self,
        specialty_id: int,
        data: SpecialtyUpdate,
    ) -> Specialty:
        specialty = await self.specialty(specialty_id)
        specialty.name = data.name
        return await self._save(specialty)

    async def delete_specialty(self, specialty_id: int) -> None:
        await self._remove(await self.specialty(specialty_id))

    async def vets(self) -> Sequence[Vet]:
        return _require_collection(await self.repo.vets(), "Veterinarians")

    async def vet(self, vet_id: int) -> Vet:
        return _require(await self.repo.vet(vet_id), "Veterinarian", vet_id)

    async def create_vet(self, data: VetCreate) -> Vet:
        specialties = await self._resolve_specialties(data)
        return await self._save(
            Vet(
                first_name=data.first_name,
                last_name=data.last_name,
                specialties=list(specialties),
            )
        )

    async def update_vet(self, vet_id: int, data: VetUpdate) -> Vet:
        vet = await self.vet(vet_id)
        vet.first_name = data.first_name
        vet.last_name = data.last_name
        vet.specialties = list(await self._resolve_specialties(data))
        return await self._save(vet)

    async def delete_vet(self, vet_id: int) -> None:
        await self.repo.remove(await self.vet(vet_id))

    async def create_user(self, data: UserCreate) -> User:
        if await self.repo.user(data.username) is not None:
            message = f"User '{data.username}' already exists"
            raise PetClinicConflictError(message)
        user = User(
            username=data.username,
            password=_hash_password(data.password),
            enabled=data.enabled,
            roles=[Role(name=_normalize_role(role.name)) for role in data.roles],
        )
        return await self._save(user)

    async def _resolve_specialties(
        self,
        data: VetCreate | VetUpdate,
    ) -> Sequence[Specialty]:
        names = {item.name for item in data.specialties}
        specialties = await self.repo.specialties_by_names(names)
        found = {item.name for item in specialties}
        missing = names - found
        if missing:
            resource = f"Specialties ({', '.join(sorted(missing))})"
            raise PetClinicNotFoundError(resource)
        return specialties

    async def _save[Model](self, model: Model) -> Model:
        try:
            return await self.repo.save(model)
        except IntegrityError as exc:
            message = "The resource conflicts with existing PetClinic data"
            raise PetClinicConflictError(message) from exc

    async def _remove(self, model: object) -> None:
        try:
            await self.repo.remove(model)
        except IntegrityError as exc:
            message = "The resource is still referenced and cannot be deleted"
            raise PetClinicConflictError(message) from exc


def _require[Model](
    value: Model | None,
    resource: str,
    resource_id: int,
) -> Model:
    if value is None:
        raise PetClinicNotFoundError(resource, resource_id)
    return value


def _require_collection[Model](
    values: Sequence[Model],
    resource: str,
) -> Sequence[Model]:
    if not values:
        raise PetClinicNotFoundError(resource)
    return values


def _normalize_role(role: str) -> str:
    normalized = role.upper()
    return normalized if normalized.startswith("ROLE_") else f"ROLE_{normalized}"


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"
