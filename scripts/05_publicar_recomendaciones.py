#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 05: Publicación a Google Sheets
Lee recomendaciones.csv y publica a Google Sheets
Alimenta: Recomendaciones, Catalogo_Todos_Productos, Laboratorios_Lookup
"""

import sys
import os
import logging
import json
import pandas as pd
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import gspread

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'extraction.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configuración
GOOGLE_SHEET_ID = "1_rn_2CTc8yEcnZUUei-ytKAEW0lph3QeUKojCS3WRd8"
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'google_credentials.json')

def limpiar_infinitos(df):
    """Limpia valores infinitos y NaN para JSON"""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32']:
            # Reemplazar infinitos con 0 y NaN con vacío
            df[col] = df[col].replace([float('inf'), float('-inf')], 0.0)
            df[col] = df[col].fillna(0.0)
    return df

def get_sheets_client():
    """Autentica y devuelve cliente de Google Sheets"""
    try:
        credentials = Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(credentials)
        logger.info("✓ Autenticado con Google Sheets")
        return client
    except Exception as e:
        logger.error(f"✗ Error autenticación Google: {e}")
        raise

def publicar_recomendaciones(client, df):
    """Publica recomendaciones en la pestaña Recomendaciones"""
    logger.info("Publicando recomendaciones...")

    try:
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        ws = sheet.worksheet("Recomendaciones")

        # Limpiar
        ws.clear()

        # Headers - solo usar columnas que existen
        headers = [col for col in ['Codigo', 'Nombre', 'PVP', 'PMC', 'LaboratorioId', 'LaboratorioNombre',
                   'PrecioRecomendado', 'DeltaPrecio', 'DeltaPorcentaje', 'TipoCambio',
                   'Margen', 'CategoriaMargen'] if col in df.columns]

        # Convertir a valores
        rows = [headers] + df[headers].fillna('').values.tolist()

        ws.append_rows(rows, value_input_option='RAW')
        logger.info(f"✓ Publicadas {len(df)} recomendaciones en 'Recomendaciones'")

    except Exception as e:
        logger.error(f"✗ Error publicando Recomendaciones: {e}")

def publicar_catalogo(client, df):
    """Publica catálogo completo en Catalogo_Todos_Productos"""
    logger.info("Publicando catálogo...")

    try:
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        ws = sheet.worksheet("Catalogo_Todos_Productos")

        # Limpiar
        ws.clear()

        # Headers - solo usar columnas que existen
        headers = [col for col in ['Codigo', 'Nombre', 'PVP', 'PMC', 'LaboratorioId', 'LaboratorioNombre',
                   'Margen', 'EsGenerico'] if col in df.columns]

        # Convertir a valores
        rows = [headers] + df[headers].fillna('').values.tolist()

        ws.append_rows(rows, value_input_option='RAW')
        logger.info(f"✓ Publicados {len(df)} productos en 'Catalogo_Todos_Productos'")

    except Exception as e:
        logger.warning(f"⚠ Error publicando Catálogo: {e}")

def publicar_laboratorios(client, df):
    """Publica tabla de laboratorios única en Laboratorios_Lookup"""
    logger.info("Publicando laboratorios...")

    try:
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        ws = sheet.worksheet("Laboratorios_Lookup")

        # Limpiar
        ws.clear()

        # Deduplicar y limpiar laboratorios
        df_labs = df[['LaboratorioId', 'LaboratorioNombre']].copy()
        df_labs = df_labs.dropna(subset=['LaboratorioNombre'])
        df_labs = df_labs[df_labs['LaboratorioNombre'] != ''].drop_duplicates()
        df_labs = df_labs.sort_values('LaboratorioId')

        # Renombrar para Google Sheets
        df_labs = df_labs.rename(columns={'LaboratorioId': 'Laboratorio'})

        # Headers y datos
        headers = ['Laboratorio', 'LaboratorioNombre']
        rows = [headers] + df_labs.values.tolist()

        ws.append_rows(rows, value_input_option='RAW')
        logger.info(f"✓ Publicados {len(df_labs)} laboratorios en 'Laboratorios_Lookup'")

    except Exception as e:
        logger.warning(f"⚠ Error publicando Laboratorios: {e}")

def main():
    logger.info("="*60)
    logger.info("PUBLICACION A GOOGLE SHEETS")
    logger.info("="*60)

    try:
        # Leer recomendaciones
        input_path = os.path.join(os.path.dirname(__file__), 'recomendaciones.csv')
        df = pd.read_csv(input_path, sep=';', encoding='utf-8')
        logger.info(f"Leyendo {input_path} ({len(df)} filas)")

        # Limpiar infinitos antes de publicar
        df = limpiar_infinitos(df)

        # Autenticar
        client = get_sheets_client()

        # Publicar a tres pestañas
        publicar_recomendaciones(client, df)
        publicar_catalogo(client, df)
        publicar_laboratorios(client, df)

        logger.info("="*60)
        logger.info("PUBLICACION COMPLETADA")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
