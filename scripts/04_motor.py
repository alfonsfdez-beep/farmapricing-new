#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 04: Motor de cálculos y recomendaciones
Calcula recomendaciones de precio, margen, etc.
Output: recomendaciones.csv
"""

import sys
import os
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'extraction.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("MOTOR DE CALCULOS")
    logger.info("="*60)

    try:
        input_path = os.path.join(os.path.dirname(__file__), 'pricing_unificado.csv')
        output_path = os.path.join(os.path.dirname(__file__), 'recomendaciones.csv')

        # Leer CSV unificado
        df = pd.read_csv(input_path, sep=';', encoding='utf-8')
        logger.info(f"Leyendo {input_path} ({len(df)} filas)")

        # Calcular recomendaciones
        df['PrecioRecomendado'] = df['PMC'] * 1.35  # Margen 35% por defecto
        df['DeltaPrecio'] = (df['PrecioRecomendado'] - df['PVP']).round(2)
        df['DeltaPorcentaje'] = ((df['DeltaPrecio'] / df['PVP'] * 100).fillna(0)).round(2)

        # Clasificar
        def tipo_cambio(delta):
            if delta < -10:
                return 'BAJADA'
            elif delta > 10:
                return 'SUBIDA'
            else:
                return 'MANTENER'

        df['TipoCambio'] = df['DeltaPorcentaje'].apply(tipo_cambio)

        # Impacto estimado (mock)
        df['ImpactoMargen30d'] = (df['DeltaPrecio'] * 10).round(2)  # Estimado
        df['ImpactoFacturacion30d'] = (df['DeltaPrecio'] * 5).round(2)

        logger.info(f"✓ Calculadas {len(df)} recomendaciones")
        logger.info(f"  - Bajadas: {(df['TipoCambio'] == 'BAJADA').sum()}")
        logger.info(f"  - Subidas: {(df['TipoCambio'] == 'SUBIDA').sum()}")
        logger.info(f"  - Mantener: {(df['TipoCambio'] == 'MANTENER').sum()}")

        # Guardar
        df.to_csv(output_path, index=False, sep=';', encoding='utf-8')
        logger.info(f"✓ Guardado: {output_path}")

        logger.info("="*60)
        logger.info("MOTOR COMPLETADO")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
