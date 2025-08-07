from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Gabinete(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_deputado: int = Field(foreign_key="deputado.id", unique=True, index=True)
    nome: Optional[str] = Field(default=None)
    predio: Optional[str] = Field(default=None)
    sala: str = Field()
    andar: Optional[str] = Field(default=None)
    telefone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, max_length=255)

    deputado: "Deputado" = Relationship(back_populates="gabinete")
