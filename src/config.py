import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (que deve ficar fora do GitHub)
load_dotenv()

# Endpoint base da API, igual está na documentação
API_BASE_URL = "https://api.api-futebol.com.br/v1"

# Chave da API, lida de variável de ambiente
API_KEY = os.getenv("API_FUTEBOL_KEY", "")

# IDs dos campeonatos brasileiros que você quer acompanhar.
# Você pega esses IDs usando GET /campeonatos.
CAMPEONATOS_BR = [  10
]

# Quantos jogos anteriores de cada time usar nas estatísticas
NUM_JOGOS_HISTORICO = 10

# Caminho do arquivo CSV de saída
ARQUIVO_RESULTADO = "data/probabilidades_hoje.csv"
