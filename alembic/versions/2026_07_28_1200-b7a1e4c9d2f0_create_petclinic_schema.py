"""Create and seed the PetClinic schema.

Revision ID: b7a1e4c9d2f0
Revises: 97f7686bdccd
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7a1e4c9d2f0"
down_revision: str | Sequence[str] | None = "97f7686bdccd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vets",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("first_name", sa.String(30), nullable=False),
        sa.Column("last_name", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vets")),
    )
    op.create_index(op.f("ix_vets_last_name"), "vets", ["last_name"])
    op.create_table(
        "specialties",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_specialties")),
    )
    op.create_index(
        "uq_specialties_name_ci",
        "specialties",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "vet_specialties",
        sa.Column("vet_id", sa.Integer(), nullable=False),
        sa.Column("specialty_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["specialty_id"],
            ["specialties.id"],
            name=op.f("fk_vet_specialties_specialty_id_specialties"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vet_id"],
            ["vets.id"],
            name=op.f("fk_vet_specialties_vet_id_vets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "vet_id",
            "specialty_id",
            name=op.f("pk_vet_specialties"),
        ),
        sa.UniqueConstraint(
            "vet_id",
            "specialty_id",
            name="uq_vet_specialties_vet_specialty",
        ),
    )
    op.create_table(
        "types",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_types")),
    )
    op.create_index(
        "uq_types_name_ci",
        "types",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "owners",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("first_name", sa.String(30), nullable=False),
        sa.Column("last_name", sa.String(30), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("telephone", sa.String(10), nullable=False),
        sa.CheckConstraint(
            "telephone ~ '^[0-9]{10}$'",
            name=op.f("ck_owners_telephone_10_digits"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_owners")),
    )
    op.create_index(op.f("ix_owners_last_name"), "owners", ["last_name"])
    op.create_table(
        "pets",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["owners.id"],
            name=op.f("fk_pets_owner_id_owners"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["type_id"],
            ["types.id"],
            name=op.f("fk_pets_type_id_types"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pets")),
    )
    op.create_index(op.f("ix_pets_name"), "pets", ["name"])
    op.create_index(op.f("ix_pets_owner_id"), "pets", ["owner_id"])
    op.create_index(op.f("ix_pets_type_id"), "pets", ["type_id"])
    op.create_index(
        "uq_pets_owner_name_ci",
        "pets",
        ["owner_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("pet_id", sa.Integer(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["pet_id"],
            ["pets.id"],
            name=op.f("fk_visits_pet_id_pets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visits")),
    )
    op.create_index(op.f("ix_visits_pet_id"), "visits", ["pet_id"])
    op.create_table(
        "users",
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("username", name=op.f("pk_users")),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("role", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["username"],
            ["users.username"],
            name=op.f("fk_roles_username_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("username", "role", name="uq_roles_username_role"),
    )
    _seed()


def _seed() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO vets (id, first_name, last_name) VALUES
              (1, 'James', 'Carter'), (2, 'Helen', 'Leary'),
              (3, 'Linda', 'Douglas'), (4, 'Rafael', 'Ortega'),
              (5, 'Henry', 'Stevens'), (6, 'Sharon', 'Jenkins');
            INSERT INTO specialties (id, name) VALUES
              (1, 'radiology'), (2, 'surgery'), (3, 'dentistry');
            INSERT INTO vet_specialties (vet_id, specialty_id) VALUES
              (2, 1), (3, 2), (3, 3), (4, 2), (5, 1);
            INSERT INTO types (id, name) VALUES
              (1, 'cat'), (2, 'dog'), (3, 'lizard'),
              (4, 'snake'), (5, 'bird'), (6, 'hamster');
            INSERT INTO owners
              (id, first_name, last_name, address, city, telephone) VALUES
              (1, 'George', 'Franklin', '110 W. Liberty St.', 'Madison', '6085551023'),
              (2, 'Betty', 'Davis', '638 Cardinal Ave.', 'Sun Prairie', '6085551749'),
              (3, 'Eduardo', 'Rodriquez', '2693 Commerce St.', 'McFarland', '6085558763'),
              (4, 'Harold', 'Davis', '563 Friendly St.', 'Windsor', '6085553198'),
              (5, 'Peter', 'McTavish', '2387 S. Fair Way', 'Madison', '6085552765'),
              (6, 'Jean', 'Coleman', '105 N. Lake St.', 'Monona', '6085552654'),
              (7, 'Jeff', 'Black', '1450 Oak Blvd.', 'Monona', '6085555387'),
              (8, 'Maria', 'Escobito', '345 Maple St.', 'Madison', '6085557683'),
              (9, 'David', 'Schroeder', '2749 Blackhawk Trail', 'Madison', '6085559435'),
              (10, 'Carlos', 'Estaban', '2335 Independence La.', 'Waunakee', '6085555487');
            INSERT INTO pets (id, name, birth_date, type_id, owner_id) VALUES
              (1, 'Leo', '2000-09-07', 1, 1), (2, 'Basil', '2002-08-06', 6, 2),
              (3, 'Rosy', '2001-04-17', 2, 3), (4, 'Jewel', '2000-03-07', 2, 3),
              (5, 'Iggy', '2000-11-30', 3, 4), (6, 'George', '2000-01-20', 4, 5),
              (7, 'Samantha', '1995-09-04', 1, 6), (8, 'Max', '1995-09-04', 1, 6),
              (9, 'Lucky', '1999-08-06', 5, 7), (10, 'Mulligan', '1997-02-24', 2, 8),
              (11, 'Freddy', '2000-03-09', 5, 9), (12, 'Lucky', '2000-06-24', 2, 10),
              (13, 'Sly', '2002-06-08', 1, 10);
            INSERT INTO visits (id, pet_id, visit_date, description) VALUES
              (1, 7, '2010-03-04', 'rabies shot'),
              (2, 8, '2011-03-04', 'rabies shot'),
              (3, 8, '2009-06-04', 'neutered'),
              (4, 7, '2008-09-04', 'spayed');
            INSERT INTO users (username, password, enabled) VALUES
              ('admin', '$2a$10$ymaklWBnpBKlgdMgkjWVF.GMGyvH8aDuTK.glFOaKw712LHtRRymS', true);
            INSERT INTO roles (id, username, role) VALUES
              (1, 'admin', 'ROLE_OWNER_ADMIN'),
              (2, 'admin', 'ROLE_VET_ADMIN'),
              (3, 'admin', 'ROLE_ADMIN');
            SELECT setval(pg_get_serial_sequence('vets', 'id'), 6);
            SELECT setval(pg_get_serial_sequence('specialties', 'id'), 3);
            SELECT setval(pg_get_serial_sequence('types', 'id'), 6);
            SELECT setval(pg_get_serial_sequence('owners', 'id'), 10);
            SELECT setval(pg_get_serial_sequence('pets', 'id'), 13);
            SELECT setval(pg_get_serial_sequence('visits', 'id'), 4);
            SELECT setval(pg_get_serial_sequence('roles', 'id'), 3);
            """
        )
    )


def downgrade() -> None:
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_index(op.f("ix_visits_pet_id"), table_name="visits")
    op.drop_table("visits")
    op.drop_index("uq_pets_owner_name_ci", table_name="pets")
    op.drop_index(op.f("ix_pets_type_id"), table_name="pets")
    op.drop_index(op.f("ix_pets_owner_id"), table_name="pets")
    op.drop_index(op.f("ix_pets_name"), table_name="pets")
    op.drop_table("pets")
    op.drop_index(op.f("ix_owners_last_name"), table_name="owners")
    op.drop_table("owners")
    op.drop_index("uq_types_name_ci", table_name="types")
    op.drop_table("types")
    op.drop_table("vet_specialties")
    op.drop_index("uq_specialties_name_ci", table_name="specialties")
    op.drop_table("specialties")
    op.drop_index(op.f("ix_vets_last_name"), table_name="vets")
    op.drop_table("vets")
