from sqlalchemy import select
from sqlmodel import Session
from database import engine
import requests
from typing import Optional

# Assumindo que os seus modelos estão definidos nestes ficheiros
from models.voto_individual import VotoIndividual
from models.sessao_votacao import SessaoVotacao
from models.deputado import Deputado

def main():
    """
    Este script busca os votos individuais para cada sessão de votação,
    verifica se os deputados existem na base de dados,
    e insere os registos de votos na tabela VotoIndividual.
    """    
    # Contador para fazer commits periódicos
    sessoes_processadas = 0
    
    with Session(engine) as session:
        # 1. Buscar todas as sessões de votação da nossa base de dados
        statement_sessoes = select(SessaoVotacao)
        # .all() retorna uma lista de objetos Row
        todas_sessoes_rows = session.exec(statement_sessoes).all()
        total_sessoes = len(todas_sessoes_rows)
        print(f"DEBUG: Encontradas {total_sessoes} sessões de votação para processar.")

        for i, sessao_row in enumerate(todas_sessoes_rows):
            # CORREÇÃO: Extrai a instância do modelo do objeto Row pelo índice [0]
            sessao_db = sessao_row[0]
            
            print(f"\n--- Processando Sessão {i+1}/{total_sessoes} ---")

            try:
                # 2. Construir a URL e buscar os votos na API para a sessão atual
                url = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{sessao_db.id_dados_abertos}/votos'
                headers = {'accept': 'application/json'}
                
                print(f"DEBUG: Buscando votos na URL: {url}")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()  # Lança um erro para status HTTP 4xx/5xx
                
                votos_api = response.json().get('dados', [])
                if not votos_api:
                    print("INFO: Esta sessão não possui registos de votos individuais na API. Pulando.")
                    continue
                
                print(f"DEBUG: Encontrados {len(votos_api)} votos para esta sessão.")

                # 3. Iterar sobre cada voto recebido da API
                for voto_api in votos_api:
                    deputado_info = voto_api.get('deputado_')
                    if not deputado_info:
                        print("AVISO: Voto sem informação do deputado. Pulando.")
                        continue

                    id_deputado_api = deputado_info.get('id')
                    if not id_deputado_api:
                        print(f"AVISO: Voto com info de deputado, mas sem ID. Pulando. Info: {deputado_info}")
                        continue
                    
                    # 4. Verificar se o deputado já existe na nossa base de dados
                    deputado_row = session.exec(
                        select(Deputado).where(Deputado.id_dados_abertos == id_deputado_api)
                    ).first()

                    if deputado_row:
                        # CORREÇÃO: Extrai a instância do modelo do objeto Row pelo índice [0]
                        deputado_db = deputado_row[0]
                    else:
                        # 5. Se o deputado não existe, cria um novo registo
                        print(f"  -> INFO: Deputado ID {id_deputado_api} não encontrado.")
                        break
                    
                    # 6. Verificar se este voto específico já foi inserido para evitar duplicados
                    voto_existente = session.exec(
                        select(VotoIndividual).where(
                            VotoIndividual.id_votacao == sessao_db.id,
                            VotoIndividual.id_deputado == deputado_db.id
                        )
                    ).first()

                    if voto_existente:
                        print(f"  -> INFO: Voto para o deputado nesta sessão já existe. Pulando.")
                        continue

                    # 7. Criar a nova instância de VotoIndividual com todos os dados
                    novo_voto = VotoIndividual(
                        id_votacao=sessao_db.id,
                        id_deputado=deputado_db.id,
                        tipo_voto=voto_api.get('tipoVoto'),
                        data_hora_registro=voto_api.get("dataRegistroVoto"),
                        sigla_partido_deputado=deputado_db.sigla_partido,
                        uri_deputado=deputado_info.get('uri'),
                        uri_sessao_votacao=sessao_db.uri
                    )
                    session.add(novo_voto)
                    print(f"  -> DEBUG: Voto do Dep. {deputado_db.nome_eleitoral} ({voto_api.get('tipoVoto')}) adicionado à sessão.")

            except requests.exceptions.RequestException as e:
                print(f"ERRO: Falha de conexão ao buscar votos para a sessão {sessao_db.id_dados_abertos}: {e}")
                continue
            except Exception as e:
                print(f"ERRO INESPERADO ao processar a sessão {sessao_db.id_dados_abertos}: {repr(e)}")
                break

            sessoes_processadas += 1
            # 8. Fazer commit a cada 50 sessões para salvar o progresso
            if sessoes_processadas % 50 == 0:
                print(f"\n--- COMMIT PARCIAL: Salvando {sessoes_processadas} sessões processadas na base de dados... ---")
                session.commit()
                print("--- SUCESSO: Dados salvos. Continuando... ---")

        # 9. Commit final para salvar quaisquer registos restantes
        print("\n--- PROCESSAMENTO CONCLUÍDO: Realizando commit final... ---")
        session.commit()
        print("--- SUCESSO: Todos os votos foram carregados com êxito! ---")

main()
