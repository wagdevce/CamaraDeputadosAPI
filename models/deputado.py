from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from models.despesa import Despesa
from models.voto_individual import VotoIndividual
from models.gabinete import Gabinete
from models.partido import Partido

class Deputado(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_dados_abertos: int = Field(index=True, unique=True, description="ID do deputado nos Dados Abertos da Câmara.")
    nome_civil: Optional[str] = Field(default=None, max_length=255)
    nome_eleitoral: str = Field(max_length=255, description="Nome pelo qual o deputado é conhecido eleitoralmente.")
    sigla_partido: str = Field(max_length=50, description="Sigla do partido político do deputado.")
    sigla_uf: str = Field(max_length=2, description="Sigla da Unidade Federativa (estado) do deputado.")

    id_partido: Optional[int] = Field(default=None,  foreign_key="partido.id")
    id_legislativo: Optional[int] = Field(default=None)
    url_foto: Optional[str] = Field(default=None, max_length=500)
    sexo: Optional[str] = Field(default=None, max_length=1, description="M ou F")

    gabinete: Optional["Gabinete"] = Relationship(back_populates="deputado")
    partido: Optional["Partido"] = Relationship(back_populates="deputados")
    despesas: List["Despesa"] = Relationship(back_populates="deputado")
    votos_individuais: List["VotoIndividual"] = Relationship(back_populates="deputado")