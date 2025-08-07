from typing import Optional
import math
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from database import get_session
from models.gabinete import Gabinete
from utils.pagination import PaginationParams, PaginatedResponse
from models.despesa import Despesa
from models.deputado import Deputado
from models.partido import Partido
from sqlalchemy import desc

gabinete_router = APIRouter(prefix="/gabinete", tags=["Gabinete"])

@gabinete_router.get("/get_by_id/{gabinete_id}", response_model=Gabinete)
def get_gabinete_by_id(gabinete_id: int, session: Session = Depends(get_session)):
    """
    Busca um gabinete específico pelo seu ID.
    Inclui os dados do deputado associado.
    """

    gabinete = session.exec(
        select(Gabinete).where(Gabinete.id == gabinete_id).options(selectinload(Gabinete.deputado))
    ).first()
    
    if not gabinete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gabinete com ID {gabinete_id} não encontrado."
        )
    return gabinete

@gabinete_router.get("/get_all", response_model=PaginatedResponse[Gabinete])
def get_all_gabinetes(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    predio: Optional[str] = Query(None, description="Filtrar por número do prédio."),
    andar: Optional[str] = Query(None, description="Filtrar por número do andar.")
):
    """
    Lista todos os gabinetes com paginação e filtros opcionais por prédio e andar.
    """
    statement = select(Gabinete).options(selectinload(Gabinete.deputado))

    if predio:
        statement = statement.where(Gabinete.predio.ilike(f"%{predio}%"))
    if andar:
        statement = statement.where(Gabinete.andar.ilike(f"%{andar}%"))

    # Lógica de paginação
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    offset = (pagination.page - 1) * pagination.per_page
    results = session.exec(statement.offset(offset).limit(pagination.per_page)).all()

    return PaginatedResponse(
        items=results,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )
@gabinete_router.get("/analise/gastos_por_andar")
def get_analise_gastos_por_andar(
    ano: int = Query(2024, description="Ano de referência para a análise das despesas."),
    predio: Optional[str] = Query(None, description="Filtrar por um prédio específico (ex: 'Anexo IV')."),
    session: Session = Depends(get_session)
):
    """
    Retorna uma análise dos gastos totais e médios dos deputados,
    agrupados por andar e prédio de seus gabinetes.
    """
    # Consulta que junta Gabinete, Deputado e Despesa
    stmt = (
        select(
            Gabinete.predio,
            Gabinete.andar,
            func.sum(Despesa.valor_liquido).label("total_gasto"),
            func.avg(Despesa.valor_liquido).label("media_gasto"),
            func.count(func.distinct(Gabinete.id_deputado)).label("num_deputados")
        )
        .join(Deputado, Gabinete.id_deputado == Deputado.id)
        .join(Despesa, Deputado.id == Despesa.id_deputado)
        .where(Despesa.ano == ano)
    )

    if predio:
        stmt = stmt.where(Gabinete.predio.ilike(f"%{predio}%"))

    # Agrupando e ordenando pelo maior gasto total
    stmt = stmt.group_by(Gabinete.predio, Gabinete.andar).order_by(desc("total_gasto"))

    resultados = session.exec(stmt).all()

    # Formatando a resposta
    items = [
        {
            "predio": r.predio,
            "andar": r.andar,
            "total_gasto": round(r.total_gasto, 2) if r.total_gasto else 0,
            "media_gasto_por_deputado": round(r.media_gasto, 2) if r.media_gasto else 0,
            "numero_deputados_no_andar": r.num_deputados
        } for r in resultados
    ]

    return items


@gabinete_router.get("/analise/partidos_por_andar")
def get_analise_partidos_por_andar(
    andar: str = Query(..., description="Andar a ser analisado."),
    predio: Optional[str] = Query(None, description="Filtrar por um prédio específico."),
    session: Session = Depends(get_session)
):
    """
    Retorna a contagem de deputados por partido para um andar e/ou prédio específico.
    """
    stmt = (
        select(
            Partido.sigla,
            Partido.nome_completo,
            func.count(Deputado.id).label("quantidade_deputados")
        )
        .select_from(Gabinete)  
        .join(Deputado)         
        .join(Partido)          
        .where(Gabinete.andar.ilike(andar))
    )

    if predio:
        stmt = stmt.where(Gabinete.predio.ilike(f"%{predio}%"))

    # Agrupando por partido e ordenando pela maior quantidade
    stmt = stmt.group_by(Partido.sigla, Partido.nome_completo).order_by(desc("quantidade_deputados"))

    resultados = session.exec(stmt).all()

    # Formatando a resposta como uma lista de dicionários
    items = [
        {
            "sigla_partido": r.sigla,
            "nome_partido": r.nome_completo,
            "quantidade_deputados": r.quantidade_deputados
        } for r in resultados
    ]

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum deputado encontrado para o andar '{andar}'" + (f" no prédio '{predio}'." if predio else ".")
        )

    return items


@gabinete_router.get("/perfil_completo_por_andar")
def get_perfil_completo_por_andar(
    andar: str = Query(..., description="Andar a ser analisado."),
    ano: int = Query(2024, description="Ano de referência para a análise das despesas."),
    predio: Optional[str] = Query(None, description="Filtrar por um prédio específico."),
    session: Session = Depends(get_session)
):
    """
    Retorna um perfil completo de um andar, mostrando para cada partido presente:
    a quantidade de deputados, o gasto total e a média de gasto por deputado.
    """
    # Consulta que junta Gabinete, Deputado, Partido e Despesa
    stmt = (
        select(
            Partido.sigla,
            Partido.nome_completo,
            func.count(func.distinct(Deputado.id)).label("quantidade_deputados"),
            func.sum(Despesa.valor_liquido).label("total_gasto_partido_no_andar"),
            func.avg(Despesa.valor_liquido).label("media_gasto_por_deputado_no_andar")
        )
        .select_from(Gabinete)
        .join(Deputado, Gabinete.id_deputado == Deputado.id)
        .join(Partido, Deputado.id_partido == Partido.id)
        .join(Despesa, Deputado.id == Despesa.id_deputado)
        .where(Gabinete.andar.ilike(andar))
        .where(Despesa.ano == ano)
    )

    if predio:
        stmt = stmt.where(Gabinete.predio.ilike(f"%{predio}%"))

    # Agrupamento e Ordenação
    stmt = stmt.group_by(Partido.sigla, Partido.nome_completo).order_by(desc("total_gasto_partido_no_andar"))

    resultados = session.exec(stmt).all()

    if not resultados:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma informação de despesa encontrada para deputados no andar '{andar}' em {ano}" + (f" no prédio '{predio}'." if predio else ".")
        )

    # Formatando a resposta
    items = [
        {
            "sigla_partido": r.sigla,
            "nome_partido": r.nome_completo,
            "quantidade_deputados_no_andar": r.quantidade_deputados,
            "gasto_total_do_partido_no_andar": round(r.total_gasto_partido_no_andar, 2) if r.total_gasto_partido_no_andar else 0,
            "media_gasto_por_deputado_do_partido_no_andar": round(r.media_gasto_por_deputado_no_andar, 2) if r.media_gasto_por_deputado_no_andar else 0
        } for r in resultados
    ]

    return {
        "analise_andar": andar,
        "ano_referencia": ano,
        "predio_filtro": predio if predio else "Todos",
        "perfil_partidos": items
    }
