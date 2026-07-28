# ruff: noqa: FAST003  # FastAPI path aliases preserve upstream camelCase names.

from collections.abc import Sequence
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.io import (
    OwnerCreate,
    OwnerPage,
    OwnerResponse,
    OwnerUpdate,
    PetCreate,
    PetPage,
    PetResponse,
    PetTypeCreate,
    PetTypeResponse,
    PetTypeUpdate,
    PetUpdate,
    SpecialtyCreate,
    SpecialtyResponse,
    SpecialtyUpdate,
    UserCreate,
    UserResponse,
    VetCreate,
    VetResponse,
    VetUpdate,
    VisitCreate,
    VisitNestedCreate,
    VisitResponse,
    VisitUpdate,
)
from app.model import Owner, Pet, PetType, Specialty, User, Vet, Visit
from app.service import PetClinicService, get_petclinic_service

route = APIRouter(prefix="/api")
Service = Annotated[PetClinicService, Depends(get_petclinic_service)]
OwnerId = Annotated[int, Path(alias="ownerId", ge=0)]
PetId = Annotated[int, Path(alias="petId", ge=0)]
PetTypeId = Annotated[int, Path(alias="petTypeId", ge=0)]
VisitId = Annotated[int, Path(alias="visitId", ge=0)]
SpecialtyId = Annotated[int, Path(alias="specialtyId", ge=0)]
VetId = Annotated[int, Path(alias="vetId", ge=0)]


@route.get("/oops", tags=["errors"], operation_id="failingRequest")
async def failing_request() -> None:
    message = "Expected PetClinic failure"
    raise RuntimeError(message)


@route.get(
    "/owners",
    tags=["owners"],
    response_model=list[OwnerResponse],
    operation_id="listOwners",
)
async def list_owners(
    service: Service,
    last_name: Annotated[str | None, Query(alias="lastName")] = None,
) -> Sequence[Owner]:
    return await service.owners(last_name)


@route.post(
    "/owners",
    tags=["owners"],
    status_code=201,
    response_model=OwnerResponse,
    operation_id="addOwner",
)
async def add_owner(
    data: OwnerCreate,
    response: Response,
    service: Service,
) -> Owner:
    owner = await service.create_owner(data)
    response.headers["Location"] = f"/api/owners/{owner.id}"
    return owner


@route.get(
    "/v2/owners",
    tags=["owners"],
    operation_id="listOwnersPage",
)
async def list_owners_page(
    service: Service,
    last_name: Annotated[str | None, Query(alias="lastName")] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OwnerPage:
    content, total = await service.owner_page(last_name, page, size)
    return OwnerPage(
        content=list(content),
        page=page,
        size=size,
        total_elements=total,
        total_pages=ceil(total / size),
    )


@route.get(
    "/owners/{ownerId}",
    tags=["owners"],
    response_model=OwnerResponse,
    operation_id="getOwner",
)
async def get_owner(owner_id: OwnerId, service: Service) -> Owner:
    return await service.owner(owner_id)


@route.put(
    "/owners/{ownerId}",
    tags=["owners"],
    status_code=204,
    operation_id="updateOwner",
)
async def update_owner(
    owner_id: OwnerId,
    data: OwnerUpdate,
    service: Service,
) -> None:
    await service.update_owner(owner_id, data)


@route.delete(
    "/owners/{ownerId}",
    tags=["owners"],
    status_code=204,
    operation_id="deleteOwner",
)
async def delete_owner(owner_id: OwnerId, service: Service) -> None:
    await service.delete_owner(owner_id)


@route.post(
    "/owners/{ownerId}/pets",
    tags=["owners", "pets"],
    status_code=201,
    response_model=PetResponse,
    operation_id="addPetToOwner",
)
async def add_pet_to_owner(
    owner_id: OwnerId,
    data: PetCreate,
    response: Response,
    service: Service,
) -> Pet:
    pet = await service.create_pet(owner_id, data)
    response.headers["Location"] = f"/api/pets/{pet.id}"
    return pet


@route.get(
    "/owners/{ownerId}/pets/{petId}",
    tags=["owners", "pets"],
    response_model=PetResponse,
    operation_id="getOwnersPet",
)
async def get_owners_pet(
    owner_id: OwnerId,
    pet_id: PetId,
    service: Service,
) -> Pet:
    return await service.owners_pet(owner_id, pet_id)


@route.put(
    "/owners/{ownerId}/pets/{petId}",
    tags=["owners", "pets"],
    status_code=204,
    operation_id="updateOwnersPet",
)
async def update_owners_pet(
    owner_id: OwnerId,
    pet_id: PetId,
    data: PetUpdate,
    service: Service,
) -> None:
    await service.update_owners_pet(owner_id, pet_id, data)


@route.post(
    "/owners/{ownerId}/pets/{petId}/visits",
    tags=["owners", "visits"],
    status_code=201,
    response_model=VisitResponse,
    operation_id="addVisitToOwner",
)
async def add_visit_to_owner(
    owner_id: OwnerId,
    pet_id: PetId,
    data: VisitNestedCreate,
    response: Response,
    service: Service,
) -> Visit:
    visit = await service.create_nested_visit(owner_id, pet_id, data)
    response.headers["Location"] = f"/api/visits/{visit.id}"
    return visit


@route.get(
    "/pets",
    tags=["pets"],
    response_model=list[PetResponse],
    operation_id="listPets",
)
async def list_pets(service: Service) -> Sequence[Pet]:
    return await service.pets()


@route.get(
    "/v2/pets",
    tags=["pets"],
    operation_id="listPetsPage",
)
async def list_pets_page(
    service: Service,
    page: Annotated[int, Query(ge=0)] = 0,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PetPage:
    content, total = await service.pet_page(page, size)
    return PetPage(
        content=list(content),
        page=page,
        size=size,
        total_elements=total,
        total_pages=ceil(total / size),
    )


@route.get(
    "/pets/{petId}",
    tags=["pets"],
    response_model=PetResponse,
    operation_id="getPet",
)
async def get_pet(pet_id: PetId, service: Service) -> Pet:
    return await service.pet(pet_id)


@route.put(
    "/pets/{petId}",
    tags=["pets"],
    status_code=204,
    operation_id="updatePet",
)
async def update_pet(pet_id: PetId, data: PetUpdate, service: Service) -> None:
    await service.update_pet(pet_id, data)


@route.delete(
    "/pets/{petId}",
    tags=["pets"],
    status_code=204,
    operation_id="deletePet",
)
async def delete_pet(pet_id: PetId, service: Service) -> None:
    await service.delete_pet(pet_id)


@route.get(
    "/pettypes",
    tags=["pettypes"],
    response_model=list[PetTypeResponse],
    operation_id="listPetTypes",
)
async def list_pet_types(service: Service) -> Sequence[PetType]:
    return await service.pet_types()


@route.post(
    "/pettypes",
    tags=["pettypes"],
    status_code=201,
    response_model=PetTypeResponse,
    operation_id="addPetType",
)
async def add_pet_type(
    data: PetTypeCreate,
    response: Response,
    service: Service,
) -> PetType:
    pet_type = await service.create_pet_type(data)
    response.headers["Location"] = f"/api/pettypes/{pet_type.id}"
    return pet_type


@route.get(
    "/pettypes/{petTypeId}",
    tags=["pettypes"],
    response_model=PetTypeResponse,
    operation_id="getPetType",
)
async def get_pet_type(pet_type_id: PetTypeId, service: Service) -> PetType:
    return await service.pet_type(pet_type_id)


@route.put(
    "/pettypes/{petTypeId}",
    tags=["pettypes"],
    status_code=204,
    operation_id="updatePetType",
)
async def update_pet_type(
    pet_type_id: PetTypeId,
    data: PetTypeUpdate,
    service: Service,
) -> None:
    await service.update_pet_type(pet_type_id, data)


@route.delete(
    "/pettypes/{petTypeId}",
    tags=["pettypes"],
    status_code=204,
    operation_id="deletePetType",
)
async def delete_pet_type(pet_type_id: PetTypeId, service: Service) -> None:
    await service.delete_pet_type(pet_type_id)


@route.get(
    "/visits",
    tags=["visits"],
    response_model=list[VisitResponse],
    operation_id="listVisits",
)
async def list_visits(service: Service) -> Sequence[Visit]:
    return await service.visits()


@route.post(
    "/visits",
    tags=["visits"],
    status_code=201,
    response_model=VisitResponse,
    operation_id="addVisit",
)
async def add_visit(
    data: VisitCreate,
    response: Response,
    service: Service,
) -> Visit:
    visit = await service.create_visit(data)
    response.headers["Location"] = f"/api/visits/{visit.id}"
    return visit


@route.get(
    "/visits/{visitId}",
    tags=["visits"],
    response_model=VisitResponse,
    operation_id="getVisit",
)
async def get_visit(visit_id: VisitId, service: Service) -> Visit:
    return await service.visit(visit_id)


@route.put(
    "/visits/{visitId}",
    tags=["visits"],
    status_code=204,
    operation_id="updateVisit",
)
async def update_visit(
    visit_id: VisitId,
    data: VisitUpdate,
    service: Service,
) -> None:
    await service.update_visit(visit_id, data)


@route.delete(
    "/visits/{visitId}",
    tags=["visits"],
    status_code=204,
    operation_id="deleteVisit",
)
async def delete_visit(visit_id: VisitId, service: Service) -> None:
    await service.delete_visit(visit_id)


@route.get(
    "/specialties",
    tags=["specialties"],
    response_model=list[SpecialtyResponse],
    operation_id="listSpecialties",
)
async def list_specialties(service: Service) -> Sequence[Specialty]:
    return await service.specialties()


@route.post(
    "/specialties",
    tags=["specialties"],
    status_code=201,
    response_model=SpecialtyResponse,
    operation_id="addSpecialty",
)
async def add_specialty(
    data: SpecialtyCreate,
    response: Response,
    service: Service,
) -> Specialty:
    specialty = await service.create_specialty(data)
    response.headers["Location"] = f"/api/specialties/{specialty.id}"
    return specialty


@route.get(
    "/specialties/{specialtyId}",
    tags=["specialties"],
    response_model=SpecialtyResponse,
    operation_id="getSpecialty",
)
async def get_specialty(
    specialty_id: SpecialtyId,
    service: Service,
) -> Specialty:
    return await service.specialty(specialty_id)


@route.put(
    "/specialties/{specialtyId}",
    tags=["specialties"],
    status_code=204,
    operation_id="updateSpecialty",
)
async def update_specialty(
    specialty_id: SpecialtyId,
    data: SpecialtyUpdate,
    service: Service,
) -> None:
    await service.update_specialty(specialty_id, data)


@route.delete(
    "/specialties/{specialtyId}",
    tags=["specialties"],
    status_code=204,
    operation_id="deleteSpecialty",
)
async def delete_specialty(specialty_id: SpecialtyId, service: Service) -> None:
    await service.delete_specialty(specialty_id)


@route.get(
    "/vets",
    tags=["vets"],
    response_model=list[VetResponse],
    operation_id="listVets",
)
async def list_vets(service: Service) -> Sequence[Vet]:
    return await service.vets()


@route.post(
    "/vets",
    tags=["vets"],
    status_code=201,
    response_model=VetResponse,
    operation_id="addVet",
)
async def add_vet(
    data: VetCreate,
    response: Response,
    service: Service,
) -> Vet:
    vet = await service.create_vet(data)
    response.headers["Location"] = f"/api/vets/{vet.id}"
    return vet


@route.get(
    "/vets/{vetId}",
    tags=["vets"],
    response_model=VetResponse,
    operation_id="getVet",
)
async def get_vet(vet_id: VetId, service: Service) -> Vet:
    return await service.vet(vet_id)


@route.put(
    "/vets/{vetId}",
    tags=["vets"],
    status_code=204,
    operation_id="updateVet",
)
async def update_vet(vet_id: VetId, data: VetUpdate, service: Service) -> None:
    await service.update_vet(vet_id, data)


@route.delete(
    "/vets/{vetId}",
    tags=["vets"],
    status_code=204,
    operation_id="deleteVet",
)
async def delete_vet(vet_id: VetId, service: Service) -> None:
    await service.delete_vet(vet_id)


@route.post(
    "/users",
    tags=["users"],
    status_code=201,
    response_model=UserResponse,
    operation_id="addUser",
)
async def add_user(
    data: UserCreate,
    response: Response,
    service: Service,
) -> User:
    user = await service.create_user(data)
    response.headers["Location"] = f"/api/users/{user.username}"
    return user
