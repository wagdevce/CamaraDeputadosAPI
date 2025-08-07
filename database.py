from sqlmodel import SQLModel, Session, create_engine

from models.deputado import Deputado
from models.despesa import Despesa
from models.gabinete import Gabinete
from models.partido import Partido
from models.proposicao import Proposicao
from models.sessao_votacao import SessaoVotacao
from models.votacao_proposicao import VotacaoProposicao
from models.voto_individual import VotoIndividual

DATABASE_URL = "postgresql://postgres:Wfrso2022@localhost:5432/CamaraDeputadosDB"

engine = create_engine(DATABASE_URL)

target_metadata = SQLModel.metadata

def get_session():
    with Session(engine) as session:
        yield session