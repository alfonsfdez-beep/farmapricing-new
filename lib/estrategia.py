"""
Análisis estratégico: Pareto 20/80 para identificar productos top ventas.

Aplica la regla de Pareto a nivel familia/subfamilia para detectar:
- Qué 20% de SKUs generan 80% de venta
- Concentración de riesgo (si depende de pocos productos)
- Oportunidades de promoción en productos de alto impacto
"""
from __future__ import annotations

import pandas as pd


def calcular_pareto(
    df: pd.DataFrame,
    columna_venta: str = "Ventas_30d",
) -> pd.DataFrame:
    """
    Calcula análisis Pareto para el DataFrame.

    Args:
        df: DataFrame con datos (debe tener columna_venta)
        columna_venta: Columna a usar para cálculo (default: Ventas_30d)

    Returns:
        DataFrame ordenado por venta DESC con columnas adicionales:
        - rank: posición en ranking (1, 2, 3...)
        - venta_acumulada: suma acumulada de ventas
        - pct_acumulado: % acumulado respecto al total
        - es_top_20_pct: True si está en el 20% que suma ~80%
    """
    if df.empty:
        return df

    result = df.copy()

    # Validar que existe la columna
    if columna_venta not in result.columns:
        raise ValueError(f"Columna '{columna_venta}' no encontrada en DataFrame")

    # Convertir a numérico (por si viene como string)
    result[columna_venta] = pd.to_numeric(result[columna_venta], errors="coerce").fillna(0)

    # Ordenar por ventas descendente
    result = result.sort_values(columna_venta, ascending=False).reset_index(drop=True)

    # Calcular acumulados
    venta_total = result[columna_venta].sum()

    if venta_total <= 0:
        # Si no hay venta, marcar como vacío
        result["rank"] = range(1, len(result) + 1)
        result["venta_acumulada"] = 0
        result["pct_acumulado"] = 0.0
        result["es_top_20_pct"] = False
    else:
        result["rank"] = range(1, len(result) + 1)
        result["venta_acumulada"] = result[columna_venta].cumsum()
        result["pct_acumulado"] = (result["venta_acumulada"] / venta_total * 100).round(1)

        # Identificar top 20% que suman ~80%
        result["es_top_20_pct"] = result["pct_acumulado"] <= 80

    return result


def obtener_stats_pareto(
    df: pd.DataFrame,
    columna_venta: str = "Ventas_30d",
) -> dict:
    """
    Retorna estadísticas del análisis Pareto.

    Args:
        df: DataFrame con datos
        columna_venta: Columna de venta (default: Ventas_30d)

    Returns:
        {
            'n_total_skus': cantidad total de SKUs
            'n_top_20': cantidad de SKUs en top 20%
            'pct_top_20': porcentaje que representa top 20% del total
            'venta_total': total de ventas
            'venta_top_20': venta del top 20%
            'concentracion_pct': % de venta que genera el top 20%
        }
    """
    if df.empty:
        return {
            "n_total_skus": 0,
            "n_top_20": 0,
            "pct_top_20": 0.0,
            "venta_total": 0,
            "venta_top_20": 0,
            "concentracion_pct": 0.0,
        }

    pareto_df = calcular_pareto(df, columna_venta)

    n_total = len(pareto_df)
    top_20 = pareto_df[pareto_df["es_top_20_pct"]].shape[0]
    venta_top_20 = pareto_df[pareto_df["es_top_20_pct"]][columna_venta].sum()
    venta_total = pareto_df[columna_venta].sum()

    return {
        "n_total_skus": n_total,
        "n_top_20": top_20 if top_20 > 0 else 0,
        "pct_top_20": round(top_20 / n_total * 100, 1) if n_total > 0 else 0.0,
        "venta_total": venta_total,
        "venta_top_20": venta_top_20,
        "concentracion_pct": round(venta_top_20 / venta_total * 100, 1)
        if venta_total > 0
        else 0.0,
    }


def generar_insight_concentracion(stats: dict) -> str:
    """
    Genera texto de insight sobre concentración de venta.

    Args:
        stats: dict retornado por obtener_stats_pareto

    Returns:
        String con insight legible
    """
    n_top = stats.get("n_top_20", 0)
    n_total = stats.get("n_total_skus", 0)
    conc = stats.get("concentracion_pct", 0)

    if n_total == 0:
        return "Sin datos para analizar"

    if conc >= 90:
        return f"🚨 Concentración EXTREMA: Solo {n_top} de {n_total} SKUs generan {conc}% de venta. Riesgo muy alto."
    elif conc >= 85:
        return f"⚠️ Concentración ALTA: {n_top} SKUs ({round(n_top/n_total*100,1)}% del catálogo) generan {conc}% de venta."
    elif conc >= 80:
        return f"✓ Concentración NORMAL (Pareto): {n_top} SKUs ({round(n_top/n_total*100,1)}%) generan {conc}% de venta."
    else:
        return f"📊 Catálogo DIVERSO: {n_top} SKUs generan {conc}% de venta. Buena distribución de riesgo."
