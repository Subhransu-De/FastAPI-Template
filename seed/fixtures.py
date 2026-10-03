from uuid import UUID

from seed import Fixtures

FIXTURES: Fixtures = {
    "entities": [
        {
            "id": UUID("6f1c2a52-8d3b-4c1e-9a4f-0b7e5d2c1a01"),
            "name": "Sample entity",
            "description": "Reference data loaded by make seed.",
        },
        {
            "id": UUID("6f1c2a52-8d3b-4c1e-9a4f-0b7e5d2c1a02"),
            "name": "Second sample entity",
            "description": None,
        },
    ],
}
