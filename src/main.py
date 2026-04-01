import os
import csv

from .config import ARQUIVO_RESULTADO, NUM_JOGOS_HISTORICO
from .api_client import APIFutebolClient
from .stats_engine import analisar_times


def salvar_csv(caminho: str, linhas: list, campos: list):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)


def main():
    api = APIFutebolClient()

    print("Buscando partidas de hoje...")
    partidas = api.partidas_hoje_brasil()
    if not partidas:
        print("Nenhuma partida encontrada ou CAMPEONATOS_BR vazio.")
        return

    resultados = []

    for p in partidas:
        print(f"- {p['time_casa_nome']} x {p['time_fora_nome']} ({p['campeonato_nome']})")

        hist_casa = api.partidas_anteriores_time(p["time_casa_id"], NUM_JOGOS_HISTORICO)
        hist_fora = api.partidas_anteriores_time(p["time_fora_id"], NUM_JOGOS_HISTORICO)
        if not hist_casa or not hist_fora:
            print("  -> histórico insuficiente, pulando.")
            continue

        def coletar_stats(hist, time_id):
            stats = []
            for h in hist:
                est = api.estatisticas_partida_por_time(h["partida_id"])
                if not est:
                    continue
                if h["mandante_id"] == time_id:
                    stats.append(est["mandante"])
                else:
                    stats.append(est["visitante"])
            return stats

        stats_casa = coletar_stats(hist_casa, p["time_casa_id"])
        stats_fora = coletar_stats(hist_fora, p["time_fora_id"])

        if not stats_casa or not stats_fora:
            print("  -> sem estatísticas suficientes, pulando.")
            continue

        analise = analisar_times(stats_casa, stats_fora)

        linha = {
            "campeonato": p["campeonato_nome"],
            "data": p["data"],
            "hora": p["hora"],
            "time_casa": p["time_casa_nome"],
            "time_fora": p["time_fora_nome"],

            "media_chutes_total": analise["chutes"]["total"]["media"],
            "prob_chutes_gt_10": analise["chutes"]["total"]["prob_gt_10"],
            "prob_chutes_gt_15": analise["chutes"]["total"]["prob_gt_15"],

            "media_chutes_gol_total": analise["chutes_gol"]["total"]["media"],

            "media_escanteios_total": analise["escanteios"]["total"]["media"],
            "prob_escanteios_gt_10": analise["escanteios"]["total"]["prob_gt_10"],

            "media_laterais_total": analise["laterais"]["total"]["media"],
            "prob_laterais_gt_15": analise["laterais"]["total"]["prob_gt_15"],
        }
        resultados.append(linha)

    if not resultados:
        print("Nenhuma análise gerada.")
        return

    campos = list(resultados[0].keys())
    salvar_csv(ARQUIVO_RESULTADO, resultados, campos)
    print(f"CSV gerado em: {ARQUIVO_RESULTADO}")


if __name__ == "__main__":
    main()
