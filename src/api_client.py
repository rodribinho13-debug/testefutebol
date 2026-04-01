import requests
from datetime import date
from typing import List, Dict, Optional

from .config import API_BASE_URL, API_KEY, CAMPEONATOS_BR, NUM_JOGOS_HISTORICO


class APIFutebolClient:
    """
    Cliente para a API Futebol baseado na documentação:
    - Endpoint base: https://api.api-futebol.com.br/v1
    """

    def __init__(self, api_key: str = API_KEY, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "rodrigo-testefutebol/1.0",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            print(f"[HTTP {resp.status_code}] {url} -> {resp.text}")
        except Exception as e:
            print(f"[ERRO] {url}: {e}")
        return None

    # ---------- CAMPEONATOS ----------

    def listar_campeonatos(self) -> List[Dict]:
        """
        GET /campeonatos
        Use isso para descobrir os IDs dos campeonatos brasileiros.
        """
        data = self._get("campeonatos")
        return data or []

    # ---------- PARTIDAS DE HOJE ----------

    def partidas_hoje_campeonato(self, campeonato_id: int) -> List[Dict]:
        """
        GET /campeonatos/{id}/partidas?data=YYYY-MM-DD
        (o endpoint exato aparece na seção de campeonatos da doc)
        """
        hoje = date.today().strftime("%Y-%m-%d")
        response_data = self._get(f"campeonatos/{campeonato_id}/partidas",
                                  params={"data": hoje})
if isinstance(response_data, dict) and "partidas" in response_data:
            data = response_data["partidas"]
        else:
          
            # Se não for um dicionário com 'partidas', ou se for vazio, retorne vazio.
            return []

        if not data:
            return []

        partidas = []
        for p in data:
            # Esta verificação é para garantir que cada item 'p' na lista 'data' é um dicionário.
            if not isinstance(p, dict):
                print(f"Aviso: Item inesperado na lista de partidas: {p}. Ignorando.")
                continue

            partidas.append({
                "partida_id": p.get("partida_id"),
                "campeonato_id": campeonato_id,
                "campeonato_nome": p.get("campeonato", {}).get("nome"),
                "data": p.get("data_realizacao"),
                "hora": p.get("hora_realizacao"),
                "status": p.get("status"),
                "time_casa_id": p.get("time_mandante", {}).get("time_id"),
                "time_casa_nome": p.get("time_mandante", {}).get("nome_popular"),
                "time_fora_id": p.get("time_visitante", {}).get("time_id"),
                "time_fora_nome": p.get("time_visitante", {}).get("nome_popular"),
            })
        return partidas

    def partidas_hoje_brasil(self) -> List[Dict]:
        """
        Junta partidas de hoje de todos os campeonatos em CAMPEONATOS_BR.
        """
        todas = []
        for cid in CAMPEONATOS_BR:
            todas.extend(self.partidas_hoje_campeonato(cid))
        return todas

    # ---------- HISTÓRICO DE TIMES ----------

    def partidas_anteriores_time(self, time_id: int,
                                 limite: int = NUM_JOGOS_HISTORICO) -> List[Dict]:
        """
        GET /times/{id}/partidas-anteriores
        (confirme o endpoint na doc, pode ter variação de nome)
        """
        data = self._get(f"times/{time_id}/partidas-anteriores")
        if not data:
            return []

        partidas = []
        for p in data[:limite]:
            # Adicione a verificação de tipo aqui também, para robustez
            if not isinstance(p, dict):
                print(f"Aviso: Item inesperado na lista de partidas anteriores: {p}. Ignorando.")
                continue
            partidas.append({
                "partida_id": p.get("partida_id"),
                "data": p.get("data_realizacao"),
                "mandante_id": p.get("time_mandante", {}).get("time_id"),
                "visitante_id": p.get("time_visitante", {}).get("time_id"),
            })
        return partidas

    # ---------- ESTATÍSTICAS DE UMA PARTIDA ----------

    def estatisticas_partida_por_time(self, partida_id: int) -> Optional[Dict]:
        """
        GET /partidas/{id}

        A doc diz que vem um JSON com dados completos da partida.
        Normalmente há blocos de estatísticas por time (mandante/visitante).
        Como a doc de introdução não mostra o JSON completo, deixamos
        o parser flexível e você ajusta depois com base no retorno real.
        """
        data = self._get(f"partidas/{partida_id}")
        if not data:
            return None

        estat_m = data.get("estatisticas_mandante", []) or []
        estat_v = data.get("estatisticas_visitante", []) or []

        def extrair(stats_list):
            mapping = {
                "chutes": ["finalizacoes", "chutes", "chutes_totais"],
                "chutes_gol": ["finalizacoes_no_gol", "chutes_no_gol"],
                "escanteios": ["escanteios"],
                "laterais": ["laterais"],
            }
            res = {k: None for k in mapping}
            for item in stats_list:
                # Adicione a verificação de tipo aqui também
                if not isinstance(item, dict):
                    print(f"Aviso: Item inesperado na lista de estatísticas: {item}. Ignorando.")
                    continue
                tipo = str(item.get("tipo", "")).lower()
                valor = item.get("valor")
                for campo, aliases in mapping.items():
                    if any(a in tipo for a in aliases):
                        res[campo] = valor
            return res

        return {
            "mandante": extrair(estat_m),
            "visitante": extrair(estat_v),
        }