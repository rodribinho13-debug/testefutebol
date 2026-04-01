from typing import List, Dict, Optional
import math


def media_desvio(valores: List[Optional[float]]) -> Dict[str, Optional[float]]:
    nums = [float(v) for v in valores if v is not None]
    if not nums:
        return {"media": None, "desvio": None}
    n = len(nums)
    media = sum(nums) / n
    if n == 1:
        return {"media": media, "desvio": 0.0}
    var = sum((v - media) ** 2 for v in nums) / (n - 1)
    return {"media": media, "desvio": math.sqrt(var)}


def prob_maior_que(limite: float,
                   media: Optional[float],
                   desvio: Optional[float]) -> Optional[float]:
    if media is None or desvio is None or desvio == 0:
        return None
    z = (limite - media) / desvio
    t = 1.0 / (1.0 + 0.5 * abs(z))
    erf_approx = 1 - t * math.exp(
        -z*z - 1.26551223 + t * (1.00002368 +
        t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 +
        t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 +
        t * (-0.82215223 + t * 0.17087277))))))))
    )
    cdf = 0.5 * (1 + erf_approx if z >= 0 else 1 - erf_approx)
    return 1 - cdf  # prob de X > limite


def analisar_times(stats_casa: List[Dict], stats_fora: List[Dict]) -> Dict:
    campos = ["chutes", "chutes_gol", "escanteios", "laterais"]
    resultado: Dict[str, Dict] = {}

    for campo in campos:
        casa_vals = [s.get(campo) for s in stats_casa]
        fora_vals = [s.get(campo) for s in stats_fora]

        m_c = media_desvio(casa_vals)
        m_f = media_desvio(fora_vals)

        media_total = None
        desvio_total = None
        if m_c["media"] is not None and m_f["media"] is not None:
            media_total = m_c["media"] + m_f["media"]
            dc = m_c["desvio"] or 0
            df = m_f["desvio"] or 0
            desvio_total = math.sqrt(dc**2 + df**2)

        resultado[campo] = {
            "casa": m_c,
            "fora": m_f,
            "total": {
                "media": media_total,
                "desvio": desvio_total,
                "prob_gt_10": prob_maior_que(10, media_total, desvio_total),
                "prob_gt_15": prob_maior_que(15, media_total, desvio_total),
            }
        }

    return resultado
