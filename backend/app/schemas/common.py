from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: f'{value:.2f}', return_type=str),
]
