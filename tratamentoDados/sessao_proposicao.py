import datetime
from typing import List, Dict, Optional
import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session
import json
from models.proposicao import Proposicao
from models.sessao_votacao import SessaoVotacao
from database import engine
import xml.etree.ElementTree as ET
from models.votacao_proposicao import VotacaoProposicao

def carregar_sessao_json(caminho_arquivo: str) -> List[Dict]:
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return dados.get("dados", [])
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
        return []
    except json.JSONDecodeError:
        print(f"Erro: O arquivo '{caminho_arquivo}' não é um JSON válido.")
        return []

def buscar_detalhes_sessao_xml(uri: str) -> Optional[Dict]:
    try:
        headers = {'accept': 'application/xml'}
        response = requests.get(uri, headers=headers, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        
        proposicoes_afetadas_ids: List[str] = []

        for prop_afetada_elem in root.findall('.//proposicoesAfetadas/proposicoesAfetadas/id'):
            if prop_afetada_elem.text:
                proposicoes_afetadas_ids.append(prop_afetada_elem.text)
        
        return {"proposicoes_afetadas_ids": proposicoes_afetadas_ids}

    except requests.exceptions.RequestException as e:
        print(f"  - Erro de conexão ao acessar {uri}: {e}")
        return None
    except ET.ParseError:
        print(f"  - Falha ao analisar o XML da URI {uri}.")
        return None

def buscar_detalhes_proposicao_api(proposicao_id: str) -> Optional[Dict]:
    try:
        url = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao_id}'
        headers = {'accept': 'application/json'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get('dados', {})
    except requests.exceptions.RequestException as e:
        print(f"ERRO: Falha na requisição da proposição {proposicao_id}: {e}.")
        return None
    except json.JSONDecodeError:
        print(f"ERRO: Resposta da API para proposição {proposicao_id} não é um JSON válido.")
        return None


def main():
    arquivo_json = 'data/votacoes_2024.json'
    sessoes_base = carregar_sessao_json(arquivo_json)
    
    if not sessoes_base:
        print('Sem sessões para processar. Encerrando.')
        return 

    total_sessoes = len(sessoes_base)
    for i, sessao_dict in enumerate(sessoes_base):
        id_sessao_json = sessao_dict.get('id')
        print(f"\n--- Processando sessão {i+1}/{total_sessoes} (ID JSON: {id_sessao_json}) ---")

        # Inicia uma nova sessão para cada item do JSON.
        with Session(engine) as session:
            try:
                # 1. VERIFICAR/CRIAR SESSÃO DE VOTAÇÃO
                uri_detalhes = sessao_dict.get('uri')
                if not uri_detalhes:
                    print(f"DEBUG: URI de detalhes não encontrada. Pulando.")
                    continue

                # Verifica se a sessão já existe no banco
                sessao_row = session.exec(
                    select(SessaoVotacao).where(SessaoVotacao.id_dados_abertos == id_sessao_json)
                ).first()

                if sessao_row:
                    nova_sessao = sessao_row.SessaoVotacao
                    print(f"DEBUG: Sessão {id_sessao_json} já existe no DB (ID: {nova_sessao.id}). Usando existente.")
                else:
                    print(f"DEBUG: Sessão {id_sessao_json} não encontrada. Criando...")
                    nova_sessao = SessaoVotacao(
                        id_dados_abertos=sessao_dict['id'],
                        data_hora_registro=sessao_dict.get('dataHoraRegistro'),
                        descricao=sessao_dict.get('descricao'),
                        sigla_orgao=sessao_dict.get('siglaOrgao'),
                        descricao_ultima_abertura_votacao=sessao_dict.get('ultimaAberturaVotacao', {}).get('descricao'),
                        aprovacao=str(sessao_dict['aprovacao']) if sessao_dict.get('aprovacao') is not None else None,
                        uri=sessao_dict['uri']
                    )
                    session.add(nova_sessao)
                    session.flush() 
                    print(f"DEBUG: Sessão {id_sessao_json} adicionada (DB ID: {nova_sessao.id}).")

                # 2. BUSCAR DETALHES E PROPOSIÇÕES ASSOCIADAS
                detalhes_xml = buscar_detalhes_sessao_xml(uri_detalhes)
                if not detalhes_xml:
                    print(f"AVISO: Não foi possível obter detalhes XML para URI {uri_detalhes}. Pulando proposições desta sessão.")
                    session.commit()
                    continue
                
                ids_proposicoes = detalhes_xml['proposicoes_afetadas_ids']
                if not ids_proposicoes:
                    print("DEBUG: Sessão não possui proposições afetadas.")
                    session.commit() # Salva a sessão mesmo sem proposições
                    continue

                # 3. PROCESSAR CADA PROPOSIÇÃO E CRIAR O LINK
                for prop_id in ids_proposicoes:
                    print(f"  -> Processando proposição afetada ID: {prop_id}")

                    proposicao_row = session.exec(
                        select(Proposicao).where(Proposicao.id_dados_abertos == prop_id)
                    ).first()

                    if proposicao_row:
                        nova_proposicao = proposicao_row.Proposicao
                        print(f"  DEBUG: Proposição {prop_id} já existe no DB (ID: {nova_proposicao.id}).")
                    else:
                        print(f"  DEBUG: Proposição {prop_id} não encontrada. Buscando na API...")
                        dados_prop = buscar_detalhes_proposicao_api(prop_id)
                        if not dados_prop:
                            print(f"  AVISO: Falha ao buscar dados da proposição {prop_id}. Link não será criado.")
                            continue 
                        
                        nova_proposicao = Proposicao(
                            id_dados_abertos=str(dados_prop.get('id')),
                            sigla_tipo=dados_prop.get('siglaTipo'),
                            ano=dados_prop.get('ano'),
                            ementa=dados_prop.get('ementa'),
                            data_apresentacao=dados_prop.get('dataApresentacao'),
                            status=dados_prop.get('statusProposicao', {}).get('descricaoSituacao'),
                            url_inteiro_teor=dados_prop.get('urlInteiroTeor')
                        )
                        session.add(nova_proposicao)
                        session.flush()
                        print(f"  DEBUG: Proposição {prop_id} adicionada (DB ID: {nova_proposicao.id}).")

                    # 4. CRIAR O LINK ASSOCIATIVO
                    existing_link = session.exec(
                        select(VotacaoProposicao).where(
                            VotacaoProposicao.id_votacao == nova_sessao.id,
                            VotacaoProposicao.id_proposicao == nova_proposicao.id
                        )
                    ).first()

                    if existing_link:
                        print(f"  DEBUG: Link Votação-Proposição já existe.")
                    else:
                        tabela_associativa = VotacaoProposicao(
                            id_votacao=nova_sessao.id,
                            id_proposicao=nova_proposicao.id,
                        )
                        session.add(tabela_associativa)
                        print(f"  DEBUG: Link Votação-Proposição adicionado à sessão.")
                
                # 5. COMMIT FINAL DA TRANSAÇÃO DA SESSÃO
                print(f"SUCESSO: Finalizando processamento da sessão {id_sessao_json}. Commitando no banco de dados...")
                session.commit()

            except Exception as e:
                print(f"ERRO CRÍTICO ao processar sessão {id_sessao_json}: {repr(e)}")
                print("Realizando rollback e INTERROMPENDO a execução.")
                session.rollback()
                raise 

main()