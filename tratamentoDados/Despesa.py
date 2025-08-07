from sqlmodel import SQLModel, Session, select
from database import engine
import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

from models.deputado import Deputado
from models.despesa import Despesa

app = SQLModel()

def salvando_despesas_localmente_json():
    # Primeiro é preciso carregar os deputados na memoria
    with Session(engine) as session:
        statement = select(Deputado)
        deputados = session.exec(statement).all()
    
    despesas_completos = []

    for i, deputado in enumerate(deputados):

        print("Processando deputado:", deputado.nome_eleitoral, "I:", i)
        # É preciso acessar a api das despesas do deputado
        url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado.id_dados_abertos}/despesas?ano=2024&itens=1500"
        response = requests.get(url, headers={"accept": "application/json"})
        if response.status_code == 200:
            dados = response.json().get("dados", [])
        else:
            print(f"Erro ao buscar despesas para deputado {deputado.nome}: {response.status_code}")
            dados = []
        despesas_completos.append({
            "id_deputado": deputado.id,
            "nome_deputado": deputado.nome_eleitoral,
            "despesas": dados
        })

    # Salvar todas as despesas em um arquivo JSON
    with open("data/despesas_deputados_2024.json", "w", encoding="utf-8") as f:
        json.dump(despesas_completos, f, ensure_ascii=False, indent=2)

def carregar_despesas_json(caminho_arquivo: str) -> List[Dict]:
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados

def main():
    arquivo_json = 'data/despesas_deputados_2024.json'
    despesas_base = carregar_despesas_json(arquivo_json)
    
    despesas_completas = []

    for despesas_json in despesas_base:        
        print("Processando despesa do deputado:", despesas_json.get('nome_deputado'))
        
        despesas = despesas_json.get('despesas')

        for despesa in despesas:

            print(despesa,  "\n\n")
            # Cria uma instância de Despesa para cada item
            despesa_combinado = Despesa(
                id_deputado=despesas_json.get('id_deputado'),
                ano=despesa.get('ano'),
                mes=despesa.get('mes'),
                tipo_despesa=despesa.get('tipoDespesa'),
                valor_liquido=despesa.get('valorLiquido'),
                tipo_documento=despesa.get('tipoDocumento'),
                url_documento=despesa.get('urlDocumento'),
                nome_fornecedor=despesa.get('nomeFornecedor')
            )
    
            despesas_completas.append(despesa_combinado)

    with Session(engine) as session:
        for despesa in despesas_completas:
            session.add(despesa)
        
        session.commit()

main()
# [
#   {
#     "id_deputado": 220593,
#     "nome_deputado": "Abilio Brunini",
#     "despesas": [
#       {
#         "ano": 2024,
#         "mes": 1,
#         "tipoDespesa": "MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR",
#         "codDocumento": 7684463,
#         "tipoDocumento": "Nota Fiscal",
#         "codTipoDocumento": 0,
#         "dataDocumento": "2024-01-04T00:00:00",
#         "numDocumento": "11533012024001",
#         "valorDocumento": 67.3,
#         "urlDocumento": "https://www.camara.leg.br/cota-parlamentar/documentos/publ/3687/2024/7684463.pdf",
#         "nomeFornecedor": "AGUAS CUIABA S.A",
#         "cnpjCpfFornecedor": "14995581000153",
#         "valorLiquido": 67.3,
#         "valorGlosa": 0.0,
#         "numRessarcimento": "",
#         "codLote": 2011692,
#         "parcela": 0
#       },
#       {
#         "ano": 2024,
#         "mes": 2,
#         "tipoDespesa": "MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR",
#         "codDocumento": 7698890,
#         "tipoDocumento": "Recibos/Outros",
#         "codTipoDocumento": 1,
#         "dataDocumento": "2024-02-02T00:00:00",
#         "numDocumento": "11533022024001",
#         "valorDocumento": 67.3,
#         "urlDocumento": "https://www.camara.leg.br/cota-parlamentar/documentos/publ/3687/2024/7698890.pdf",
#         "nomeFornecedor": "AGUAS CUIABA S.A",
#         "cnpjCpfFornecedor": "14995581000153",
#         "valorLiquido": 67.3,
#         "valorGlosa": 0.0,
#         "numRessarcimento": "",
#         "codLote": 2019609,
#         "parcela": 0
#       },
#       {
#         "ano": 2024,
#         "mes": 5,
#         "tipoDespesa": "MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR",
#         "codDocumento": 7749701,
#         "tipoDocumento": "Recibos/Outros",
#         "codTipoDocumento": 1,
#         "dataDocumento": "2024-05-11T00:00:00",
#         "numDocumento": "01",
#         "valorDocumento": 224.85,
#         "urlDocumento": "https://www.camara.leg.br/cota-parlamentar/documentos/publ/3687/2024/7749701.pdf",
#         "nomeFornecedor": "BRASIL ADM E SERVIÇOS DE COBRANÇA",
#         "cnpjCpfFornecedor": "33488393000183",
#         "valorLiquido": 224.85,
#         "valorGlosa": 0.0,
#         "numRessarcimento": "",
#         "codLote": 2047008,
#         "parcela": 0
#       },
#       {
#         "ano": 2024,
#         "mes": 5,
#         "tipoDespesa": "MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR",
#         "codDocumento": 7735772,
#         "tipoDocumento": "Nota Fiscal",
#         "codTipoDocumento": 0,
#         "dataDocumento": "2024-04-12T00:00:00",
#         "numDocumento": "1",
#         "valorDocumento": 250.0,
#         "urlDocumento": "https://www.camara.leg.br/cota-parlamentar/documentos/publ/3687/2024/7735772.pdf",
#         "nomeFornecedor": "BRASIL ADM E SERVIÇOS DE COBRANÇA",
#         "cnpjCpfFornecedor": "33488393000183",
#         "valorLiquido": 250.0,
#         "valorGlosa": 0.0,
#         "numRessarcimento": "",
#         "codLote": 2039715,
#         "parcela": 0
#       },