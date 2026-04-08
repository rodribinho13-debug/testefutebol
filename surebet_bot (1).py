# -*- coding: utf-8 -*-
"""
SureBet Bot — TheOddsAPI + ZenRows Scraping (Casas BR)
URLs atualizadas em Abril/2026 conforme nova regulamentação .bet.br
"""

import sys
import json
import requests
import time
import logging
import os
from datetime import datetime, date
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# CONFIGURAÇÕES
# ============================================================
TELEGRAM_TOKEN   = "8631114381:AAHX-mxjH-QVAoWOoFTc34sY62Yh4M63u7M"
TELEGRAM_CHAT_ID = "5438218123"

ODDS_API_BASE          = "https://api.the-odds-api.com/v4"
CHECK_INTERVAL_SECONDS = 7200
MIN_PROFIT_PERCENT     = 2.0
STAKE_TOTAL_MAX        = 300
LIMITE_MINIMO_RESTANTE = 50
MARKETS                = ["h2h"]

API_KEYS = [
    "7f360fae9c049ce94a29416222f2b7b6",
]

# ── ZenRows ─────────────────────────────────────────────────
# Coloque sua chave aqui diretamente OU use variável de ambiente:
#   Linux/Mac:  export ZENROWS_API_KEY="sua_chave"
#   Windows:    set ZENROWS_API_KEY=sua_chave
ZENROWS_API_KEY = os.environ.get("ZENROWS_API_KEY", "SUA_CHAVE_ZENROWS_AQUI")
ZENROWS_BASE    = "https://api.zenrows.com/v1/"

ZENROWS_PARAMS_DEFAULT = {
    "apikey":          ZENROWS_API_KEY,
    "js_render":       "true",
    "premium_proxy":   "true",
    "proxy_country":   "br",
    "wait":            "5000",
    "block_resources": "image,media",
    "antibot":         "true",
}

CACHE_FILE = Path("zenrows_odds_cache.json")

# ── Casas e comissoes ────────────────────────────────────────
COMISSOES_EXCHANGE = {
    "matchbook": 0.02,
    "smarkets":  0.02,
}

CASAS_ODDS_API = {
    "pinnacle":     "Pinnacle",
    "betsson":      "Betsson",
    "betway":       "Betway",
    "onexbet":      "1xBet",
    "sport888":     "888sport",
    "marathonbet":  "Marathon Bet",
    "bwin":         "Bwin",
    "livescorebet": "LiveScore Bet",
    "leovegas":     "LeoVegas",
    "casumo":       "Casumo",
    "betvictor":    "Bet Victor",
    "betclic_fr":   "Betclic",
}

# ============================================================
# CASAS BR — URLs CORRETAS ABRIL 2026
# Todos migraram para .bet.br pela nova regulamentacao brasileira
# Formato: (nome, key, url_principal, url_fallback, wait_for_seletor)
# ============================================================
CASAS_BR = [
    (
        "Betano", "betano",
        "https://www.betano.bet.br/sport/futebol/",
        "https://www.betano.com/br/sport/futebol/",
        "[class*='events-list__item'], [class*='event-card']"
    ),
    (
        "Superbet", "superbet",
        "https://www.superbet.bet.br/apostas-esportivas/futebol",
        "https://www.superbet.com.br/apostas-esportivas/futebol",
        "[class*='event-row'], [class*='event-item']"
    ),
    (
        "KTO", "kto",
        "https://www.kto.bet.br/pt-br/apostas/futebol",
        "https://www.kto.com/pt-br/apostas/futebol",
        "[class*='event'], [class*='fixture']"
    ),
    (
        "Novibet", "novibet",
        "https://www.novibet.bet.br/apostas/futebol",
        "https://www.novibet.com.br/apostas/futebol",
        "[class*='event'], [class*='match']"
    ),
    (
        "EstrelaBet", "estrelabet",
        "https://www.estrelabet.bet.br/esportes/futebol",
        "https://www.estrelabet.com.br/esportes/futebol",
        "[class*='event-card'], [class*='match-card']"
    ),
    (
        "Betnacional", "betnacional",
        "https://betnacional.bet.br/sport-event/1/3",
        "https://betnacional.bet.br/",
        "[class*='event'], [class*='match']"
    ),
    (
        "PixBet", "pixbet",
        "https://www.pixbet.bet.br/esportes/futebol",
        "https://www.pixbet.com/esportes/futebol",
        "[class*='event'], [class*='odd']"
    ),
    (
        "Sportingbet", "sportingbet",
        "https://sports.sportingbet.bet.br/pt-br/sports/futebol",
        "https://sports.sportingbet.com/pt-br/sports/futebol",
        "[class*='event-item'], [class*='match-row']"
    ),
    (
        "GaleraBet", "galerabet",
        "https://www.galera.bet.br/sportsbook",
        "https://www.galerabet.com/sports/futebol",
        "[class*='event'], [class*='match']"
    ),
    (
        "Rivalo", "rivalo",
        "https://www.rivalo.bet.br/pt/sports/soccer",
        "https://www.rivalo.bet.br/pt/sportsbook",
        "[class*='event'], [class*='match']"
    ),
    (
        "Betmotion", "betmotion",
        "https://www.betmotion.bet.br/esportes/futebol",
        "https://www.betmotion.com/esportes/futebol",
        "[class*='event-row'], [class*='match-item']"
    ),
]

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("surebet.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

api_key_index    = 0
alertas_enviados = set()


# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(message: str):
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        log.info("Mensagem enviada ao Telegram.")
    except Exception as e:
        log.error(f"Erro Telegram: {e}")


# ============================================================
# GERENCIADOR DE API KEY (TheOddsAPI)
# ============================================================
def get_current_key():
    return API_KEYS[api_key_index % len(API_KEYS)]


def rotate_key(motivo="limite atingido"):
    global api_key_index
    proximo = (api_key_index + 1) % len(API_KEYS)
    if proximo == api_key_index:
        log.error("Todas as API keys esgotadas.")
        return False
    api_key_index = proximo
    nova_key = get_current_key()
    log.warning(f"Rotacionando API key ({motivo}). Nova key: ...{nova_key[-6:]}")
    send_telegram(f"API key rotacionada!\nMotivo: {motivo}\nKey {api_key_index+1} de {len(API_KEYS)}")
    return True


def verificar_limite(remaining_header):
    try:
        restantes = int(remaining_header)
        log.info(f"Requisicoes restantes TheOddsAPI: {restantes}")
        if restantes <= LIMITE_MINIMO_RESTANTE:
            rotate_key(f"apenas {restantes} requisicoes restantes")
    except Exception:
        pass


# ============================================================
# AJUSTAR ODD PELA COMISSAO
# ============================================================
def ajustar_odd_exchange(odd: float, bookie_key: str) -> float:
    comissao = COMISSOES_EXCHANGE.get(bookie_key, 0.0)
    if comissao == 0:
        return odd
    return round(1 + (odd - 1) * (1 - comissao), 4)


# ============================================================
# ZENROWS — REQUISICAO COM RETRY E FALLBACK DE URL
# ============================================================
def zenrows_get(url: str, extra_params: dict = None) -> requests.Response | None:
    if ZENROWS_API_KEY in ("", "SUA_CHAVE_ZENROWS_AQUI"):
        log.error("ZENROWS_API_KEY nao configurada!")
        return None

    params = {**ZENROWS_PARAMS_DEFAULT, "apikey": ZENROWS_API_KEY, "url": url}
    if extra_params:
        params.update(extra_params)

    for tentativa in range(1, 3):
        try:
            log.info(f"ZenRows -> {url} (tentativa {tentativa})")
            r = requests.get(ZENROWS_BASE, params=params, timeout=120)

            if r.status_code == 200:
                log.info(f"ZenRows OK <- {url}")
                return r

            if r.status_code == 404:
                log.warning(f"ZenRows 404 - URL nao encontrada: {url}")
                return None

            if r.status_code == 422:
                log.warning(f"ZenRows 422 - tentando sem wait_for: {url}")
                params.pop("wait_for", None)
                continue

            if r.status_code == 429:
                log.warning("ZenRows 429 - cota atingida. Aguardando 60s.")
                time.sleep(60)
                continue

            if r.status_code == 403:
                log.warning(f"ZenRows 403 - bloqueado: {url}")
                return None

            log.warning(f"ZenRows {r.status_code}: {r.text[:200]}")

        except requests.exceptions.Timeout:
            log.error(f"ZenRows timeout ({tentativa}/2) para {url}")
        except Exception as e:
            log.error(f"Erro ZenRows: {e}")

        time.sleep(5)

    return None


# ============================================================
# PARSING HTML
# ============================================================
def extrair_odds_do_html(html: str, bookmaker_nome: str, bookmaker_key: str) -> dict:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("BeautifulSoup nao instalado: pip install beautifulsoup4 lxml")
        return {}

    soup = BeautifulSoup(html, "lxml")
    odds = {}

    EVENT_CLASSES = ["event", "match", "fixture", "game", "sport-item",
                     "event-row", "event-card", "match-card", "match-row", "event-item"]
    TEAM_CLASSES  = ["team", "participant", "competitor", "team-name",
                     "participant-name", "home", "away", "team-home", "team-away"]
    ODD_CLASSES   = ["odd", "price", "coef", "odds-value", "odd-value",
                     "btn-odds", "market-odd", "outcome-odds", "selection-price", "odd__value"]

    def class_match(tag, keywords):
        classes = tag.get("class", [])
        return any(kw in cls.lower() for cls in classes for kw in keywords)

    containers = soup.find_all(
        lambda t: t.name in ["div", "li", "article", "tr", "section"]
        and class_match(t, EVENT_CLASSES)
    )

    for container in containers:
        try:
            time_tags = container.find_all(
                lambda t: t.name in ["span", "div", "p", "a", "td"]
                and class_match(t, TEAM_CLASSES)
            )
            nomes = list(dict.fromkeys(
                t.get_text(strip=True) for t in time_tags if t.get_text(strip=True)
            ))

            if len(nomes) < 2:
                continue
            home, away = nomes[0], nomes[-1]

            odd_tags = container.find_all(
                lambda t: t.name in ["span", "div", "button", "td", "strong"]
                and class_match(t, ODD_CLASSES)
            )

            valores = []
            for tag in odd_tags:
                txt = tag.get_text(strip=True).replace(",", ".").replace(" ", "")
                try:
                    v = float(txt)
                    if 1.01 <= v <= 50.0:
                        valores.append(v)
                except ValueError:
                    pass

            if len(valores) < 2:
                continue

            chave    = f"{home} vs {away}"
            outcomes = {
                home: {"odd": valores[0], "bookmaker_nome": bookmaker_nome, "bookmaker_key": bookmaker_key}
            }
            if len(valores) == 3:
                outcomes["Empate"] = {"odd": valores[1], "bookmaker_nome": bookmaker_nome, "bookmaker_key": bookmaker_key}
                outcomes[away]     = {"odd": valores[2], "bookmaker_nome": bookmaker_nome, "bookmaker_key": bookmaker_key}
            else:
                outcomes[away] = {"odd": valores[-1], "bookmaker_nome": bookmaker_nome, "bookmaker_key": bookmaker_key}

            odds[chave] = outcomes

        except Exception as e:
            log.debug(f"Erro ao parsear container ({bookmaker_nome}): {e}")

    return odds


# ============================================================
# SCRAPER UNICO COM FALLBACK DE URL
# ============================================================
def scrape_casa(nome: str, key: str, url_principal: str,
                url_fallback: str, wait_for: str) -> dict:
    params = {"wait_for": wait_for} if wait_for else {}

    # Tenta URL principal
    response = zenrows_get(url_principal, params)

    # Se 422, tenta sem wait_for
    if response is None and wait_for:
        log.info(f"{nome}: tentando sem wait_for...")
        response = zenrows_get(url_principal, {})

    # Se ainda falhou, tenta URL de fallback
    if response is None and url_fallback:
        log.info(f"{nome}: tentando URL fallback -> {url_fallback}")
        response = zenrows_get(url_fallback, params)
        if response is None:
            response = zenrows_get(url_fallback, {})

    if not response:
        log.warning(f"{nome}: nenhuma resposta valida.")
        send_telegram(f"⚠️ <b>{nome}</b>: falha no scraping. URL pode ter mudado.")
        return {}

    resultado = extrair_odds_do_html(response.text, nome, key)
    log.info(f"{nome}: {len(resultado)} eventos extraidos")

    if len(resultado) == 0:
        log.warning(f"{nome}: HTML recebido mas 0 odds extraidas — seletores podem precisar ajuste.")

    return resultado


# ============================================================
# CACHE DIARIO
# ============================================================
def cache_valido() -> bool:
    if not CACHE_FILE.exists():
        return False
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("data_coleta", "") == str(date.today())
    except Exception:
        return False


def salvar_cache(odds: dict):
    payload = {"data_coleta": str(date.today()), "odds": odds}
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info(f"Cache salvo: {len(odds)} eventos em {CACHE_FILE}")


def carregar_cache() -> dict:
    with CACHE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f).get("odds", {})


# ============================================================
# COLETA PRINCIPAL BR — 1x/dia
# ============================================================
def coletar_odds_br(forcar: bool = False) -> dict:
    if not forcar and cache_valido():
        log.info("Cache valido — reutilizando odds BR do dia.")
        return carregar_cache()

    log.info("Iniciando coleta diaria de odds BR via ZenRows...")
    send_telegram("<i>Iniciando coleta diaria de odds das casas brasileiras...</i>")

    todos  = {}
    ok     = []
    falhas = []

    for nome, key, url_principal, url_fallback, wait_for in CASAS_BR:
        try:
            log.info(f"--- Scraping: {nome} ---")
            resultado = scrape_casa(nome, key, url_principal, url_fallback, wait_for)

            if resultado:
                ok.append(f"{nome} ({len(resultado)} ev.)")
                for chave, outcomes in resultado.items():
                    todos.setdefault(chave, {})
                    for outcome_name, data in outcomes.items():
                        existente = todos[chave].get(outcome_name)
                        if not existente or data["odd"] > existente["odd"]:
                            todos[chave][outcome_name] = data
            else:
                falhas.append(nome)

            time.sleep(5)

        except Exception as e:
            log.error(f"Erro ao coletar {nome}: {e}")
            falhas.append(nome)

    salvar_cache(todos)

    linhas = [f"<b>Coleta BR concluida</b>: {len(todos)} eventos unicos\n"]
    if ok:
        linhas.append(f"OK ({len(ok)}): {', '.join(ok)}")
    if falhas:
        linhas.append(f"Falhas ({len(falhas)}): {', '.join(falhas)}")
        linhas.append("<i>Sites com falha podem ter mudado de URL.</i>")

    send_telegram("\n".join(linhas))
    return todos


# ============================================================
# THEODDSAPI
# ============================================================
def get_sports() -> list:
    url    = f"{ODDS_API_BASE}/sports"
    params = {"apiKey": get_current_key()}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return [s["key"] for s in r.json() if not s.get("has_outrights", False)]
    except Exception as e:
        log.error(f"Erro ao buscar esportes: {e}")
        return []


def get_odds_api(sport_key: str, market: str) -> list:
    url    = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey":     get_current_key(),
        "regions":    "eu,us,uk,au",
        "markets":    market,
        "oddsFormat": "decimal",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 422:
            return []
        if r.status_code in [401, 429]:
            rotate_key(f"erro HTTP {r.status_code}")
            return []
        r.raise_for_status()
        remaining = r.headers.get("x-requests-remaining", "")
        if remaining:
            verificar_limite(remaining)
        return r.json()
    except Exception as e:
        log.error(f"Erro odds API [{sport_key}][{market}]: {e}")
        return []


# ============================================================
# CALCULO DE SUREBET — API PURA
# ============================================================
def calculate_surebet_api(events: list, market_key: str) -> list:
    resultados = []
    for event in events:
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        candidatos = {}
        for bookmaker in bookmakers:
            bookie_key = bookmaker["key"]
            if bookie_key not in CASAS_ODDS_API:
                continue
            bookie_nome = CASAS_ODDS_API[bookie_key]
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    name  = outcome["name"]
                    if "point" in outcome:
                        name = f"{name} {outcome['point']}"
                    price         = outcome["price"]
                    price_efetivo = ajustar_odd_exchange(price, bookie_key)
                    candidatos.setdefault(name, []).append({
                        "odd": price_efetivo, "odd_original": price,
                        "bookmaker_nome": bookie_nome, "bookmaker_key": bookie_key,
                    })

        if len(candidatos) < 2:
            continue

        for name in candidatos:
            candidatos[name].sort(key=lambda x: x["odd"], reverse=True)

        outcomes_escolhidos = {}
        for outcome_name, opcoes in candidatos.items():
            for opcao in opcoes:
                casas_usadas = {v["bookmaker_nome"] for v in outcomes_escolhidos.values()}
                if opcao["bookmaker_nome"] not in casas_usadas:
                    outcomes_escolhidos[outcome_name] = opcao
                    break

        if len(outcomes_escolhidos) < 2:
            continue

        outcomes    = list(outcomes_escolhidos.items())
        implied_sum = sum(1 / d["odd"] for _, d in outcomes)
        if implied_sum >= 1:
            continue

        profit_percent = ((1 / implied_sum) - 1) * 100
        if profit_percent < MIN_PROFIT_PERCENT:
            continue

        chave_alerta = f"{event.get('home_team')}_{event.get('away_team')}_{market_key}"
        if chave_alerta in alertas_enviados:
            continue
        alertas_enviados.add(chave_alerta)

        resultados.append(_montar_resultado(
            event_label    = f"{event.get('home_team')} vs {event.get('away_team')}",
            commence       = event.get("commence_time", ""),
            market_key     = market_key,
            outcomes       = outcomes,
            implied_sum    = implied_sum,
            profit_percent = profit_percent,
            fonte          = "TheOddsAPI",
        ))
    return resultados


# ============================================================
# CALCULO DE SUREBET — CRUZAMENTO BR + API
# ============================================================
def calculate_surebet_cruzado(scraping_odds: dict, api_events: list) -> list:
    resultados = []

    api_index = {}
    for event in api_events:
        home = event.get("home_team", "").lower().strip()
        away = event.get("away_team", "").lower().strip()
        api_index[f"{home} vs {away}"] = event

    for evento_label, outcomes_scraping in scraping_odds.items():
        chave_norm = evento_label.lower().strip()
        event_api  = api_index.get(chave_norm)

        pool = {}
        for outcome_name, data in outcomes_scraping.items():
            pool.setdefault(outcome_name, []).append(data)

        if event_api:
            for bookmaker in event_api.get("bookmakers", []):
                bookie_key = bookmaker["key"]
                if bookie_key not in CASAS_ODDS_API:
                    continue
                bookie_nome = CASAS_ODDS_API[bookie_key]
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        name  = outcome["name"]
                        price = outcome["price"]
                        pool.setdefault(name, []).append({
                            "odd":            ajustar_odd_exchange(price, bookie_key),
                            "odd_original":   price,
                            "bookmaker_nome": bookie_nome,
                            "bookmaker_key":  bookie_key,
                        })

        if len(pool) < 2:
            continue

        for name in pool:
            pool[name].sort(key=lambda x: x["odd"], reverse=True)

        outcomes_escolhidos = {}
        for outcome_name, opcoes in pool.items():
            for opcao in opcoes:
                casas_usadas = {v["bookmaker_nome"] for v in outcomes_escolhidos.values()}
                if opcao["bookmaker_nome"] not in casas_usadas:
                    outcomes_escolhidos[outcome_name] = opcao
                    break

        if len(outcomes_escolhidos) < 2:
            continue

        outcomes    = list(outcomes_escolhidos.items())
        implied_sum = sum(1 / d["odd"] for _, d in outcomes)
        if implied_sum >= 1:
            continue

        profit_percent = ((1 / implied_sum) - 1) * 100
        if profit_percent < MIN_PROFIT_PERCENT:
            continue

        chave_alerta = f"cruzado_{evento_label}"
        if chave_alerta in alertas_enviados:
            continue
        alertas_enviados.add(chave_alerta)

        fonte = "Scraping BR + TheOddsAPI" if event_api else "Scraping BR"

        resultados.append(_montar_resultado(
            event_label    = evento_label,
            commence       = event_api.get("commence_time", "") if event_api else "",
            market_key     = "h2h",
            outcomes       = outcomes,
            implied_sum    = implied_sum,
            profit_percent = profit_percent,
            fonte          = fonte,
        ))
    return resultados


# ============================================================
# HELPER — MONTAR RESULTADO
# ============================================================
def _montar_resultado(event_label, commence, market_key, outcomes,
                      implied_sum, profit_percent, fonte) -> dict:
    total_stake       = STAKE_TOTAL_MAX
    retorno_garantido = total_stake / implied_sum
    lucro_liquido     = retorno_garantido - total_stake

    stakes = {}
    for outcome_name, data in outcomes:
        stake   = (total_stake / data["odd"]) / implied_sum
        retorno = stake * data["odd"]
        stakes[outcome_name] = {
            "stake":        round(stake, 2),
            "retorno":      round(retorno, 2),
            "odd_original": data.get("odd_original", data["odd"]),
            "odd_efetiva":  data["odd"],
        }

    return {
        "event_label":       event_label,
        "commence":          commence,
        "market_key":        market_key,
        "profit_percent":    round(profit_percent, 2),
        "implied_sum":       round(implied_sum, 4),
        "outcomes":          outcomes,
        "stakes":            stakes,
        "total_stake":       round(sum(s["stake"] for s in stakes.values()), 2),
        "retorno_garantido": round(retorno_garantido, 2),
        "lucro_liquido":     round(lucro_liquido, 2),
        "fonte":             fonte,
    }


# ============================================================
# FORMATAR MENSAGEM TELEGRAM
# ============================================================
MARKET_LABELS = {
    "h2h":     "Resultado Final (1X2)",
    "spreads": "Handicap Asiatico",
    "totals":  "Over/Under",
}


def format_message(surebet: dict, sport_key: str = "") -> str:
    evento      = surebet.get("event_label", "?")
    commence    = surebet.get("commence", "")
    fonte       = surebet.get("fonte", "")
    sport_label = sport_key.replace("_", " ").upper() if sport_key else "FUTEBOL"

    date_str = ""
    if commence:
        try:
            dt       = datetime.fromisoformat(commence.replace("Z", "+00:00"))
            date_str = dt.strftime("%d/%m/%Y %H:%M UTC")
        except Exception:
            date_str = commence

    lines = [
        "SUREBET DETECTADA!",
        "",
        f"<b>Esporte:</b> {sport_label}",
        f"<b>Evento:</b> {evento}",
    ]
    if date_str:
        lines.append(f"<b>Data/Hora:</b> {date_str}")

    lines += [
        f"<b>Mercado:</b> {MARKET_LABELS.get(surebet['market_key'], surebet['market_key'].upper())}",
        f"<b>Fonte:</b> {fonte}",
        "",
        f"<b>Lucro garantido:</b> {surebet['profit_percent']}%",
        f"<b>Lucro liquido:</b> R$ {surebet['lucro_liquido']:.2f}",
        f"<b>Stake total:</b> R$ {surebet['total_stake']:.2f}",
        f"<b>Retorno total:</b> R$ {surebet['retorno_garantido']:.2f}",
        "",
        "--- ONDE E QUANTO APOSTAR ---",
    ]

    for outcome_name, data in surebet["outcomes"]:
        s            = surebet["stakes"].get(outcome_name, {})
        comissao     = COMISSOES_EXCHANGE.get(data.get("bookmaker_key", ""), 0)
        comissao_str = f" (exchange, comissao {int(comissao*100)}%)" if comissao > 0 else ""
        lines += [
            "",
            f"<b>{outcome_name}</b> -> <b>{data['bookmaker_nome']}</b>{comissao_str}",
            f"   Odd original: <b>{s.get('odd_original', data['odd'])}</b> | Efetiva: <b>{s.get('odd_efetiva', data['odd'])}</b>",
            f"   Apostar: <b>R$ {s.get('stake', 0):.2f}</b>",
            f"   Retorno: R$ {s.get('retorno', 0):.2f}",
        ]

    lines += [
        "",
        "<i>Odds efetivas ja descontam comissao das exchanges.</i>",
        "<i>Confirme as odds antes de apostar!</i>",
        f"<i>Bot SureBet | {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC</i>",
    ]
    return "\n".join(lines)


# ============================================================
# CICLO PRINCIPAL
# ============================================================
def run_cycle(odds_br: dict):
    log.info("=== Iniciando ciclo de verificacao ===")
    found = 0

    log.info("--- Buscando via TheOddsAPI ---")
    sports = get_sports()
    log.info(f"Esportes ativos: {len(sports)}")

    todos_events_api = []
    for sport_key in sports:
        for market in MARKETS:
            events = get_odds_api(sport_key, market)
            if not events:
                time.sleep(0.3)
                continue
            todos_events_api.extend(events)
            for sb in calculate_surebet_api(events, market):
                send_telegram(format_message(sb, sport_key))
                log.info(f"[API] {sb['event_label']} | Lucro: {sb['profit_percent']}%")
                found += 1
                time.sleep(1.5)
            time.sleep(0.5)

    if odds_br:
        log.info("--- Cruzando odds BR com TheOddsAPI ---")
        for sb in calculate_surebet_cruzado(odds_br, todos_events_api):
            send_telegram(format_message(sb))
            log.info(f"[{sb['fonte']}] {sb['event_label']} | Lucro: {sb['profit_percent']}%")
            found += 1
            time.sleep(1.5)
    else:
        log.warning("Sem odds BR para cruzamento.")

    summary = (
        f"Ciclo concluido. {found} surebet(s) acima de {MIN_PROFIT_PERCENT}% encontrada(s)."
        if found > 0
        else f"Ciclo concluido. Nenhuma surebet acima de {MIN_PROFIT_PERCENT}% encontrada."
    )
    log.info(summary)
    send_telegram(f"<i>{summary}</i>")


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    casas_br_nomes = ", ".join(c[0] for c in CASAS_BR)
    send_telegram(
        "<b>Bot de Surebet iniciado!</b>\n"
        f"Ciclo API: a cada {CHECK_INTERVAL_SECONDS // 60} min\n"
        f"Scraping BR (ZenRows): 1x por dia\n"
        f"Casas BR: {casas_br_nomes}\n"
        f"Stake maxima: R$ {STAKE_TOTAL_MAX} | Lucro minimo: {MIN_PROFIT_PERCENT}%"
    )
    log.info("Bot iniciado.")

    odds_br = coletar_odds_br()

    ciclo = 0
    while True:
        ciclo += 1
        try:
            if ciclo > 1:
                odds_br = coletar_odds_br()
            run_cycle(odds_br)
        except Exception as e:
            log.error(f"Erro no ciclo: {e}")
            send_telegram(f"<b>Erro no bot:</b> {e}")

        log.info(f"Aguardando {CHECK_INTERVAL_SECONDS // 60} minutos...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
