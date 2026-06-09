#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 03: Unificación de datos
Combina datos de múltiples fuentes, aplica reglas de negocio
Output: pricing_unificado.csv
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
    logger.info("UNIFICACION DE DATOS")
    logger.info("="*60)

    try:
        input_path = os.path.join(os.path.dirname(__file__), 'pricing_normalizado.csv')
        output_path = os.path.join(os.path.dirname(__file__), 'pricing_unificado.csv')

        # Leer CSV normalizado
        df = pd.read_csv(input_path, sep=';', encoding='utf-8')
        logger.info(f"Leyendo {input_path} ({len(df)} filas)")

        # Aplicar reglas de unificación
        # 1. Margen = (PVP - PMC) / PVP
        df['Margen'] = ((df['PVP'] - df['PMC']) / df['PVP'] * 100).round(2)
        df['Margen'] = df['Margen'].fillna(0.0)

        # 2. Categorizar por margen
        def categorizar_margen(m):
            if m < 20:
                return 'Bajo'
            elif m < 35:
                return 'Medio'
            else:
                return 'Alto'

        df['CategoriaMargen'] = df['Margen'].apply(categorizar_margen)

        # 3. Flags
        df['EsGenerico'] = df['Nombre'].str.contains('EFG|GENERI', case=False, na=False)
        df['TieneNombre'] = df['LaboratorioNombre'].notna() & (df['LaboratorioNombre'] != '')

        logger.info(f"✓ Unificados: {len(df)} artículos")
        logger.info(f"  - Genéricos: {df['EsGenerico'].sum()}")
        logger.info(f"  - Con nombre lab: {df['TieneNombre'].sum()}")

        # Guardar
        df.to_csv(output_path, index=False, sep=';', encoding='utf-8')
        logger.info(f"✓ Guardado: {output_path}")

        logger.info("="*60)
        logger.info("UNIFICACION COMPLETADA")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
