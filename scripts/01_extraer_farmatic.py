#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 01: Extracción de datos desde SQL Server Farmatic
Extrae: artículos, laboratorios, familias, precios
Output: pricing_base.csv en la carpeta del script
"""

import sys
import os
import logging
import pyodbc
import pandas as pd
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'extraction.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Credenciales SQL
SQL_CONFIG = {
    "server": "localhost",
    "farmatic_db": "Farmatic",
    "consejo_db": "Consejo",
    "user": "sa",
    "password": "farmatic",
    "drivers": ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]
}

def connect_sql(db_name):
    """Conecta a SQL Server con reintentos"""
    for driver in SQL_CONFIG["drivers"]:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={SQL_CONFIG['server']};"
                f"DATABASE={db_name};"
                f"UID={SQL_CONFIG['user']};"
                f"PWD={SQL_CONFIG['password']};"
                f"TrustServerCertificate=yes;"
            )
            cnx = pyodbc.connect(conn_str, timeout=30)
            logger.info(f"✓ Conectado a {db_name} con {driver}")
            return cnx
        except Exception as e:
            logger.warning(f"✗ Fallo con {driver}: {e}")

    raise RuntimeError(f"No se pudo conectar a {db_name}")

def extract_articulos():
    """Extrae artículos de Farmatic con nombres de laboratorio desde CONSEJO"""
    logger.info("Extrayendo artículos...")

    cnx = connect_sql(SQL_CONFIG["farmatic_db"])

    # Query con JOIN a [CONSEJO].dbo.LABOR y vRG_Articu para obtener laboratorios y descuentos
    query = """
    SELECT TOP 10000
        a.IdArticu AS Codigo,
        a.Descripcion AS Nombre,
        a.PVP AS PVP,
        a.Pmc AS PMC,
        a.Laboratorio AS LaboratorioId,
        ISNULL(l.NOMBRE, '') AS LaboratorioNombre,
        a.XFam_IdFamilia AS FamiliaId,
        NULL AS FamiliaNombre,
        ISNULL(a.StockActual, 0) AS Stock,
        ISNULL(d.DtoMax, 0) AS DtoMaximo,
        ISNULL(d.DtoDef, 0) AS DtoPorDefecto,
        CASE d.Aplicacion
            WHEN 'A' THEN 'Automático'
            WHEN 'M' THEN 'Manual'
            WHEN 'F' THEN 'De Familia'
            WHEN 'C' THEN 'Con Aviso'
            WHEN 'D' THEN 'Deshabilitado'
            ELSE ISNULL(d.Aplicacion, '')
        END AS TipoDescuento,
        ISNULL(f.pctoMargenFam, 0) AS MargenFamilia,
        GETDATE() AS FechaExtraccion
    FROM dbo.Articu a WITH (NOLOCK)
    LEFT JOIN [Consejo].dbo.LABOR l WITH (NOLOCK)
        ON a.Laboratorio = l.CODIGO
    LEFT JOIN dbo.Descuento d WITH (NOLOCK)
        ON d.IdCodigo = a.IdArticu AND d.IdTipo = 'ART'
    LEFT JOIN dbo.vRG_Familia f WITH (NOLOCK)
        ON f.IdFamilia = a.XFam_IdFamilia
    WHERE a.IdArticu IS NOT NULL
    ORDER BY a.IdArticu
    """

    try:
        df = pd.read_sql_query(query, cnx)
        logger.info(f"✓ Extrayeron {len(df)} artículos")
        return df
    finally:
        cnx.close()

def extract_laboratorios():
    """Extrae laboratorios de ambas BD"""
    logger.info("Extrayendo laboratorios...")

    labs = []

    # Laboratorios CONSEJO (códigos P****)
    try:
        cnx = connect_sql(SQL_CONFIG["consejo_db"])
        query = """
        SELECT
            CODIGO AS Laboratorio,
            NOMBRE AS LaboratorioNombre
        FROM dbo.LABOR WITH (NOLOCK)
        WHERE CODIGO IS NOT NULL
        ORDER BY CODIGO
        """
        df_consejo = pd.read_sql_query(query, cnx)
        logger.info(f"✓ Extrayeron {len(df_consejo)} laboratorios de CONSEJO")
        labs.append(df_consejo)
        cnx.close()
    except Exception as e:
        logger.warning(f"✗ Error leyendo CONSEJO.dbo.LABOR: {e}")

    # Laboratorios locales (códigos E****)
    try:
        cnx = connect_sql(SQL_CONFIG["farmatic_db"])
        # Intentar múltiples nombres de tabla
        for tabla in ["dbo.Labor", "dbo.Labora", "dbo.Laboratorio"]:
            try:
                query = f"""
                SELECT
                    CODIGO AS Laboratorio,
                    NOMBRE AS LaboratorioNombre
                FROM {tabla} WITH (NOLOCK)
                WHERE CODIGO IS NOT NULL
                ORDER BY CODIGO
                """
                df_local = pd.read_sql_query(query, cnx)
                logger.info(f"✓ Extrayeron {len(df_local)} laboratorios de {tabla}")
                labs.append(df_local)
                break
            except:
                continue
        cnx.close()
    except Exception as e:
        logger.warning(f"✗ Error leyendo laboratorios locales: {e}")

    if labs:
        df_combined = pd.concat(labs, ignore_index=True).drop_duplicates(subset=['Laboratorio'])
        logger.info(f"✓ Total {len(df_combined)} laboratorios únicos")
        return df_combined

    logger.warning("⚠ No se extrajeron laboratorios")
    return pd.DataFrame(columns=['Laboratorio', 'LaboratorioNombre'])

def extract_ventas_90d():
    """Extrae ventas de los últimos 90 días agrupadas por artículo"""
    logger.info("Extrayendo ventas de los últimos 90 días...")

    cnx = connect_sql(SQL_CONFIG["farmatic_db"])

    query = """
    SELECT
        l.Codigo AS Codigo,
        SUM(l.Cantidad) AS Ventas_90d
    FROM dbo.Venta v WITH (NOLOCK)
    JOIN dbo.LineaVenta l WITH (NOLOCK) ON l.IdVenta = v.IdVenta
    WHERE v.FechaHora >= DATEADD(DAY, -90, CAST(GETDATE() AS DATE))
      AND l.Codigo IS NOT NULL
    GROUP BY l.Codigo
    """

    try:
        df = pd.read_sql_query(query, cnx)
        logger.info(f"✓ Extrayeron ventas de {len(df)} artículos en últimos 90 días")
        return df
    except Exception as e:
        logger.warning(f"⚠ Error extrayendo ventas: {e}")
        return pd.DataFrame(columns=['Codigo', 'Ventas_90d'])
    finally:
        cnx.close()

def main():
    logger.info("="*60)
    logger.info("INICIO EXTRACCIÓN SQL SERVER")
    logger.info("="*60)

    try:
        # Extraer datos
        df_articulos = extract_articulos()
        df_labs = extract_laboratorios()
        df_ventas = extract_ventas_90d()

        # Mapear laboratorios
        lab_map = dict(zip(df_labs['Laboratorio'].astype(str), df_labs['LaboratorioNombre']))
        df_articulos['LaboratorioNombre'] = df_articulos['LaboratorioId'].astype(str).map(lab_map)

        # Log de NaN (sin rellenar en este script)
        nan_count = df_articulos['LaboratorioNombre'].isna().sum()
        logger.info(f"LaboratorioNombre: {nan_count} NaN (sin rellenar en Script 01)")

        # ── Mapear ventas de últimos 90 días ──────────────────────────────
        if not df_ventas.empty:
            # Convertir Codigo a string en ambos para asegurar merge correcto
            df_articulos['Codigo'] = df_articulos['Codigo'].astype(str).str.strip()
            df_ventas['Codigo'] = df_ventas['Codigo'].astype(str).str.strip()

            # LEFT JOIN para mapear ventas
            df_articulos = df_articulos.merge(df_ventas, on='Codigo', how='left')
            con_ventas = df_articulos['Ventas_90d'].notna().sum()
            logger.info(f"✓ Mapeadas ventas para {con_ventas}/{len(df_articulos)} artículos")
        else:
            df_articulos['Ventas_90d'] = None
            logger.info("⚠ No se obtuvieron datos de ventas")

        # Guardar CSV
        output_path = os.path.join(os.path.dirname(__file__), 'pricing_base.csv')
        df_articulos.to_csv(output_path, index=False, sep=';', encoding='utf-8')
        logger.info(f"✓ Guardado: {output_path} ({len(df_articulos)} filas)")

        logger.info("="*60)
        logger.info("EXTRACCIÓN COMPLETADA")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
