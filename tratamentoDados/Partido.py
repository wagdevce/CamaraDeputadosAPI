from sqlmodel import SQLModel, Session
from database import engine
import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

from models.partido import Partido

app = SQLModel()

def carregar_partidos_json(caminho_arquivo: str) -> List[Dict]:
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

def buscar_detalhes_partido_xml(uri: str) -> Optional[Dict]:
    try:
        headers = {'accept': 'application/xml'}
        response = requests.get(uri, headers=headers)

        if response.status_code == 200:
            root = ET.fromstring(response.content) # root armazena todo o xml            
       
            dados = root.find('.//dados')
            uri_logo = dados.findtext('urlLogo')
            id_legislativo = dados.findtext('status/idLegislatura')
            situacao = dados.findtext('status/situacao')
            total_membros = dados.findtext('status/totalMembros')
            total_posse_legislatura = dados.findtext('status/totalPosse')

            detalhes = {
                "uri_logo": uri_logo,
                "id_legislativo": id_legislativo,
                "situacao": situacao,
                "total_membros": total_membros,
                "total_posse_legislatura": total_posse_legislatura
            }

            return detalhes
        else:
            print(f"  - Falha ao buscar dados da URI {uri}. Status: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"  - Erro de conexão ao acessar {uri}: {e}")
        return None
    except ET.ParseError:
        print(f"  - Falha ao analisar o XML da URI {uri}.")
        return None

def main():
    arquivo_json = 'data/partidos_57.json'
    partidos_base = carregar_partidos_json(arquivo_json)
    
    if not partidos_base:
        return 
    
    partidos_completos = []

    for partido in partidos_base:        
        uri_detalhes = partido.get('uri')
        if not uri_detalhes:
            print(f"{partido.get('id')} - URI não encontrada para este partido. Pulando.")
            continue
        
        detalhes_json = buscar_detalhes_partido_xml(uri_detalhes)
        
        if detalhes_json:
            partido_combinado = Partido(
                id_dados_abertos=partido.get('id'),
                sigla=partido.get("sigla"),
                nome_completo=partido.get("nome"),
                uri_logo=detalhes_json.get('uri_logo'),
                id_legislativo=detalhes_json.get('id_legislativo'),
                situacao=detalhes_json.get('situacao'),
                total_membros=detalhes_json.get('total_membros'),
                total_posse_legislatura=detalhes_json.get('total_posse_legislatura'),
            )
            partidos_completos.append(partido_combinado)

    with Session(engine) as session:
        for partido in partidos_completos:
            session.add(partido)
        
        session.commit()
        
main()
            
