from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List
from database import get_session
from log.logger_config import get_logger
from models.voto_individual import VotoIndividual
from models.votacao_proposicao import VotacaoProposicao

logger = get_logger("votos_individuais_logger", "log/votos_individuais.log")
voto_router = APIRouter(prefix="/voto_individual", tags=["Voto Individual"])

# Obtém um voto individual pelo ID
@voto_router.get("/by_deputado/{id_deputado}")
def get_votos_by_deputado(id_deputado: int, session: Session = Depends(get_session)):
    votos = session.exec(
        select(VotoIndividual).where(VotoIndividual.id_deputado == id_deputado)
    ).all()
    return votos

# Obtém todos os votos individuais de uma proposição específica
@voto_router.get("/by_proposicao/{id_proposicao}", response_model=List[VotoIndividual])
def get_votos_by_proposicao(id_proposicao: int, session: Session = Depends(get_session)):
    # 1. Subquery: votações ligadas à proposição
    subquery = (
        select(VotacaoProposicao.id_votacao)
        .where(VotacaoProposicao.id_proposicao == id_proposicao)
    )

    # 2. Buscar votos nas votações da proposição
    stmt = (
        select(VotoIndividual)
        .where(VotoIndividual.id_votacao.in_(subquery))
    )

    votos = session.exec(stmt).all()
    return votos
