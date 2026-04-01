# get_campeonatos.py
import os
from dotenv import load_dotenv
from src.api_client import APIFutebolClient

# Carrega a chave da API do arquivo .env
load_dotenv()

api = APIFutebolClient()
print("Buscando lista de campeonatos...")
campeonatos = api.listar_campeonatos()

if campeonatos:
    print("\n--- IDs e Nomes dos Campeonatos Disponíveis ---")
    for c in campeonatos:
        print(f"ID: {c.get('campeonato_id')}, Nome: {c.get('nome')}, Tipo: {c.get('tipo')}")
    print("\nAnote os IDs dos campeonatos brasileiros que você quer usar.")
else:
    print("Não foi possível obter a lista de campeonatos.")
    print("Verifique sua chave da API no arquivo .env e sua conexão com a internet.")