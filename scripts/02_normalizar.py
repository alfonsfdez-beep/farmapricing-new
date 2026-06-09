#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 02: Normalización de datos
Lee pricing_base.csv y normaliza valores, tipos de datos, etc.
Output: pricing_normalizado.csv
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
    logger.info("NORMALIZACION DE DATOS")
    logger.info("="*60)

    try:
        input_path = os.path.join(os.path.dirname(__file__), 'pricing_base.csv')
        output_path = os.path.join(os.path.dirname(__file__), 'pricing_normalizado.csv')

        # Leer CSV
        df = pd.read_csv(input_path, sep=';', encoding='utf-8')
        logger.info(f"Leyendo {input_path} ({len(df)} filas)")

        # Normalizar valores numéricos
        for col in ['PVP', 'PMC']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Normalizar strings
        for col in ['Codigo', 'Nombre', 'LaboratorioId', 'LaboratorioNombre']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()

        # Eliminar duplicados por código
        df = df.drop_duplicates(subset=['Codigo'], keep='first')
        logger.info(f"✓ Deduplicados: {len(df)} filas únicas")

        # Guardar
        df.to_csv(output_path, index=False, sep=';', encoding='utf-8')
        logger.info(f"✓ Guardado: {output_path}")

        logger.info("="*60)
        logger.info("NORMALIZACION COMPLETADA")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
