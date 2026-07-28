from collections.abc import Sequence

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model import Owner, Pet, PetType, Role, Specialty, User, Vet, Visit


class PetClinicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save[Model](self, model: Model) -> Model:
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def remove(self, model: object) -> None:
        await self.session.delete(model)
        await self.session.flush()

    async def owner(self, owner_id: int) -> Owner | None:
        return await self.session.get(Owner, owner_id)

    async def owners(self, last_name: str | None = None) -> Sequence[Owner]:
        statement = select(Owner).order_by(Owner.id)
        if last_name is not None:
            statement = statement.where(
                Owner.last_name.ilike(f"{_escape_like(last_name)}%", escape="\\")
            )
        return (await self.session.scalars(statement)).all()

    async def owner_page(
        self,
        *,
        last_name: str | None,
        page: int,
        size: int,
    ) -> tuple[Sequence[Owner], int]:
        query: Select[tuple[Owner]] = select(Owner)
        count_query = select(func.count()).select_from(Owner)
        if last_name is not None:
            criterion = Owner.last_name.ilike(
                f"{_escape_like(last_name)}%",
                escape="\\",
            )
            query = query.where(criterion)
            count_query = count_query.where(criterion)
        total = await self.session.scalar(count_query)
        rows = await self.session.scalars(
            query.order_by(Owner.id).offset(page * size).limit(size)
        )
        return rows.all(), int(total or 0)

    async def pet(self, pet_id: int) -> Pet | None:
        return await self.session.get(Pet, pet_id)

    async def pets(self) -> Sequence[Pet]:
        return (await self.session.scalars(select(Pet).order_by(Pet.id))).all()

    async def pet_page(self, page: int, size: int) -> tuple[Sequence[Pet], int]:
        total = await self.session.scalar(select(func.count()).select_from(Pet))
        rows = await self.session.scalars(
            select(Pet).order_by(Pet.id).offset(page * size).limit(size)
        )
        return rows.all(), int(total or 0)

    async def pet_type(self, pet_type_id: int) -> PetType | None:
        return await self.session.get(PetType, pet_type_id)

    async def pet_types(self) -> Sequence[PetType]:
        return (
            await self.session.scalars(
                select(PetType).order_by(func.lower(PetType.name), PetType.id)
            )
        ).all()

    async def visit(self, visit_id: int) -> Visit | None:
        return await self.session.get(Visit, visit_id)

    async def visits(self) -> Sequence[Visit]:
        return (await self.session.scalars(select(Visit).order_by(Visit.id))).all()

    async def specialty(self, specialty_id: int) -> Specialty | None:
        return await self.session.get(Specialty, specialty_id)

    async def specialties(self) -> Sequence[Specialty]:
        return (
            await self.session.scalars(
                select(Specialty).order_by(
                    func.lower(Specialty.name),
                    Specialty.id,
                )
            )
        ).all()

    async def specialties_by_ids(
        self,
        specialty_ids: set[int],
    ) -> Sequence[Specialty]:
        if not specialty_ids:
            return []
        return (
            await self.session.scalars(
                select(Specialty).where(Specialty.id.in_(specialty_ids))
            )
        ).all()

    async def specialties_by_names(
        self,
        specialty_names: set[str],
    ) -> Sequence[Specialty]:
        if not specialty_names:
            return []
        return (
            await self.session.scalars(
                select(Specialty).where(Specialty.name.in_(specialty_names))
            )
        ).all()

    async def vet(self, vet_id: int) -> Vet | None:
        return await self.session.get(Vet, vet_id)

    async def vets(self) -> Sequence[Vet]:
        return (await self.session.scalars(select(Vet).order_by(Vet.id))).all()

    async def user(self, username: str) -> User | None:
        return await self.session.get(User, username)

    async def clear_roles(self, username: str) -> None:
        await self.session.execute(delete(Role).where(Role.username == username))
        await self.session.flush()


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
