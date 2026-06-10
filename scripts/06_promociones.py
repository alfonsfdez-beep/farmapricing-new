#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 06: Gestión de Promociones
Lee la pestaña 'Promociones' de Google Sheets y aplica/revierte
descuentos en SQL Server (dbo.Descuento) según fechas de activación.

Columnas esperadas en Google Sheets (pestaña 'Promociones'):
  Codigo | Nombre | DtoMax | DtoDef | Modo | FechaInicio | FechaFin |
  DtoMax_Original | PVP | PMC | DtoDef_Original | Margen_Antes | Margen_Despues |
  Uds_Vendidas | Modo_Original | Estado | FechaAplicado | Notas
"""

import sys
import os
import logging
from datetime import datetime, date
import pandas as pd
import pyodbc

try:
    from google.oauth2.service_account import Credentials
    import gspread
except ImportError:
    pass

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'promociones.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ── Configuración ──────────────────────────────────────────────────────────────
GOOGLE_SHEET_ID  = "1_rn_2CTc8yEcnZUUei-ytKAEW0lph3QeUKojCS3WRd8"
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'google_credentials.json')
TAB_PROMOCIONES  = "Promociones"

SQL_CONFIG = {
    "server":      "localhost",
    "farmatic_db": "Farmatic",
    "user":        "sa",
    "password":    "farmatic",
    "drivers":     ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]
}

# Mapa Modo legible → código SQL
MODO_MAP = {
    "Automático":   "A",
    "Automatico":   "A",
    "De Familia":   "F",
    "Manual":       "M",
    "Con Aviso":    "C",
    "Deshabilitado":"D",
}


# ── Conexión SQL ───────────────────────────────────────────────────────────────
def connect_sql():
    for driver in SQL_CONFIG["drivers"]:
        try:
            cs = (f"DRIVER={{{driver}}};SERVER={SQL_CONFIG['server']};"
                  f"DATABASE={SQL_CONFIG['farmatic_db']};"
                  f"UID={SQL_CONFIG['user']};PWD={SQL_CONFIG['password']};"
                  f"TrustServerCertificate=yes;")
            cnx = pyodbc.connect(cs, timeout=30)
            logger.info(f"✓ Conectado a SQL con {driver}")
            return cnx
        except Exception as e:
            logger.warning(f"✗ Fallo {driver}: {e}")
    raise RuntimeError("No se pudo conectar a SQL Server")


# ── Google Sheets ──────────────────────────────────────────────────────────────
def get_sheets_client():
    credentials = Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return gspread.authorize(credentials)

def leer_promociones(client):
    """Lee la pestaña Promociones y devuelve DataFrame."""
    try:
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        ws    = sheet.worksheet(TAB_PROMOCIONES)
        data  = ws.get_all_values()
        if not data or len(data) < 2:
            logger.info("No hay promociones en el Sheet")
            return pd.DataFrame(), ws
        headers = data[0]
        df = pd.DataFrame(data[1:], columns=headers)
        df = df[df['Codigo'].str.strip() != '']  # eliminar filas vacías
        logger.info(f"✓ Leídas {len(df)} promociones del Sheet")
        return df, ws
    except Exception as e:
        logger.error(f"✗ Error leyendo Promociones: {e}")
        return pd.DataFrame(), None

def actualizar_estado(ws, fila_idx, estado, fecha_aplicado=""):
    """Actualiza columnas Estado y FechaAplicado en el Sheet (fila base 1, +2 por header)."""
    try:
        # fila_idx es 0-based del DataFrame → fila Sheet = idx + 2 (header en fila 1)
        fila_sheet = fila_idx + 2
        # Buscar índice de columnas Estado y FechaAplicado
        headers = ws.row_values(1)
        col_estado  = headers.index('Estado') + 1       if 'Estado'       in headers else None
        col_fecha   = headers.index('FechaAplicado') + 1 if 'FechaAplicado' in headers else None

        if col_estado:
            ws.update_cell(fila_sheet, col_estado, estado)
        if col_fecha and fecha_aplicado:
            ws.update_cell(fila_sheet, col_fecha, fecha_aplicado)
    except Exception as e:
        logger.warning(f"⚠ No se pudo actualizar estado fila {fila_idx+2}: {e}")

def guardar_valores_originales(ws, fila_idx, dto_max_orig, dto_def_orig, modo_orig):
    """Guarda los valores originales antes de aplicar la promo."""
    try:
        fila_sheet = fila_idx + 2
        headers = ws.row_values(1)
        cols = {
            'DtoMax_Original':  dto_max_orig,
            'DtoDef_Original':  dto_def_orig,
            'Modo_Original':    modo_orig,
        }
        for col_name, value in cols.items():
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                ws.update_cell(fila_sheet, col_idx, str(value))
    except Exception as e:
        logger.warning(f"⚠ No se pudieron guardar originales fila {fila_idx+2}: {e}")


# ── Leer datos del artículo desde SQL ─────────────────────────────────────────
def leer_articulo(cnx, codigo):
    """Devuelve (PVP, PMC) del artículo desde dbo.Articu."""
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT PVP, Pmc FROM dbo.Articu WHERE IdArticu = ?",
        (str(codigo),)
    )
    row = cursor.fetchone()
    if row:
        return float(row[0] or 0), float(row[1] or 0)
    return 0.0, 0.0

def leer_ventas_desde(cnx, codigo, fecha_desde):
    """Devuelve unidades vendidas desde fecha_desde hasta hoy."""
    cursor = cnx.cursor()
    cursor.execute("""
        SELECT ISNULL(SUM(l.Cantidad), 0)
        FROM dbo.Venta v WITH (NOLOCK)
        JOIN dbo.LineaVenta l WITH (NOLOCK) ON l.IdVenta = v.IdVenta
        WHERE v.FechaHora >= ?
          AND l.Codigo = ?
    """, (str(fecha_desde), str(codigo)))
    row = cursor.fetchone()
    return int(row[0]) if row else 0

def calcular_margen(pvp, pmc, dto_def):
    """Calcula margen considerando el descuento aplicado al cliente.
    Margen = (PVP_cliente - PMC) / PVP_cliente * 100
    donde PVP_cliente = PVP * (1 - DtoDef/100)
    """
    try:
        pvp_cliente = float(pvp) * (1 - float(dto_def) / 100)
        if pvp_cliente <= 0:
            return 0.0
        return round((pvp_cliente - float(pmc)) / pvp_cliente * 100, 2)
    except:
        return 0.0

def guardar_pvp_margenes(ws, fila_idx, pvp, pmc, margen_antes, margen_despues, uds_vendidas):
    """Guarda PVP, PMC, márgenes y unidades vendidas en el Sheet."""
    try:
        fila_sheet = fila_idx + 2
        headers = ws.row_values(1)
        datos = {
            'PVP':            round(pvp, 2),
            'PMC':            round(pmc, 2),
            'Margen_Antes':   margen_antes,
            'Margen_Despues': margen_despues,
            'Uds_Vendidas':   uds_vendidas,
        }
        for col_name, value in datos.items():
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                ws.update_cell(fila_sheet, col_idx, str(value))
    except Exception as e:
        logger.warning(f"⚠ No se pudieron guardar PVP/márgenes fila {fila_idx+2}: {e}")

def actualizar_uds_vendidas(ws, fila_idx, uds):
    """Actualiza solo la columna Uds_Vendidas en el Sheet."""
    try:
        fila_sheet = fila_idx + 2
        headers = ws.row_values(1)
        if 'Uds_Vendidas' in headers:
            col_idx = headers.index('Uds_Vendidas') + 1
            ws.update_cell(fila_sheet, col_idx, str(uds))
    except Exception as e:
        logger.warning(f"⚠ No se pudo actualizar Uds_Vendidas fila {fila_idx+2}: {e}")


# ── Leer/Escribir descuentos en SQL ───────────────────────────────────────────
def leer_descuento_actual(cnx, codigo):
    """Devuelve (DtoMax, DtoDef, Aplicacion) actuales del artículo."""
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT DtoMax, DtoDef, Aplicacion FROM dbo.Descuento WHERE IdCodigo = ? AND IdTipo = 'ART'",
        (str(codigo),)
    )
    row = cursor.fetchone()
    if row:
        return row[0], row[1], row[2]
    return None, None, None

def aplicar_descuento(cnx, codigo, dto_max, dto_def, modo_cod):
    """Hace UPSERT en dbo.Descuento para el artículo."""
    cursor = cnx.cursor()
    # Verificar si existe
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.Descuento WHERE IdCodigo = ? AND IdTipo = 'ART'",
        (str(codigo),)
    )
    existe = cursor.fetchone()[0] > 0

    if existe:
        cursor.execute(
            "UPDATE dbo.Descuento SET DtoMax = ?, DtoDef = ?, Aplicacion = ? WHERE IdCodigo = ? AND IdTipo = 'ART'",
            (float(dto_max), float(dto_def), modo_cod, str(codigo))
        )
    else:
        cursor.execute(
            "INSERT INTO dbo.Descuento (IdTipo, IdCodigo, DtoMax, DtoDef, Aplicacion, Opciones) VALUES ('ART', ?, ?, ?, ?, 0)",
            (str(codigo), float(dto_max), float(dto_def), modo_cod)
        )
    cnx.commit()


# ── Lógica principal ──────────────────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info("GESTIÓN DE PROMOCIONES")
    logger.info("=" * 60)

    hoy = date.today()
    logger.info(f"Fecha hoy: {hoy}")

    client = get_sheets_client()
    df, ws = leer_promociones(client)

    if df.empty:
        logger.info("Sin promociones. Fin.")
        return

    cnx = connect_sql()

    activadas  = 0
    revertidas = 0
    errores    = 0

    for idx, row in df.iterrows():
        codigo = str(row.get('Codigo', '')).strip()
        if not codigo:
            continue

        estado       = str(row.get('Estado', '')).strip()
        fecha_inicio = str(row.get('FechaInicio', '')).strip()
        fecha_fin    = str(row.get('FechaFin', '')).strip()
        dto_max      = str(row.get('DtoMax', '0')).strip() or '0'
        dto_def      = str(row.get('DtoDef', '0')).strip() or '0'
        modo_str     = str(row.get('Modo', 'Automático')).strip()
        modo_cod     = MODO_MAP.get(modo_str, 'A')

        # Parsear fechas
        try:
            f_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date() if fecha_inicio else None
        except ValueError:
            try:
                f_inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y").date()
            except:
                f_inicio = None

        try:
            f_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date() if fecha_fin else None
        except ValueError:
            try:
                f_fin = datetime.strptime(fecha_fin, "%d/%m/%Y").date()
            except:
                f_fin = None

        nombre = str(row.get('Nombre', codigo))

        try:
            # ── ACTIVAR promo ──────────────────────────────────────────────
            if estado in ('Pendiente', '') and f_inicio and hoy >= f_inicio:
                # Guardar valores originales antes de cambiar
                orig_max, orig_def, orig_modo = leer_descuento_actual(cnx, codigo)
                guardar_valores_originales(ws, idx, orig_max or 0, orig_def or 0, orig_modo or 'F')

                # Leer PVP y PMC del artículo
                pvp, pmc = leer_articulo(cnx, codigo)

                # Calcular márgenes antes y después de la promo
                margen_antes   = calcular_margen(pvp, pmc, orig_def or 0)
                margen_despues = calcular_margen(pvp, pmc, dto_def)

                # Guardar PVP, PMC, márgenes y ventas=0 al inicio (se actualizarán cada día)
                guardar_pvp_margenes(ws, idx, pvp, pmc, margen_antes, margen_despues, uds_vendidas=0)

                # Aplicar nuevos descuentos
                aplicar_descuento(cnx, codigo, dto_max, dto_def, modo_cod)
                actualizar_estado(ws, idx, 'Aplicado', str(hoy))
                logger.info(f"✅ ACTIVADA: {codigo} {nombre} → DtoMax={dto_max}% DtoDef={dto_def}% "
                            f"Margen: {margen_antes}% → {margen_despues}%")
                activadas += 1

            # ── REVERTIR promo al acabar (por fecha) ──────────────────────
            elif estado == 'Aplicado' and f_fin and hoy > f_fin:
                orig_max  = str(row.get('DtoMax_Original', '0')).strip() or '0'
                orig_def  = str(row.get('DtoDef_Original', '0')).strip() or '0'
                orig_modo = str(row.get('Modo_Original', 'F')).strip()
                orig_modo_cod = MODO_MAP.get(orig_modo, orig_modo)

                aplicar_descuento(cnx, codigo, orig_max, orig_def, orig_modo_cod)
                actualizar_estado(ws, idx, 'Finalizado', str(hoy))
                logger.info(f"🔄 REVERTIDA (fecha): {codigo} {nombre} → valores originales restaurados")
                revertidas += 1

            # ── ACTUALIZAR ventas de promo activa (ejecución diaria) ──────
            elif estado == 'Aplicado' and not (f_fin and hoy > f_fin):
                # Leer FechaAplicado para contar ventas desde ese día
                fecha_aplicado_str = str(row.get('FechaAplicado', '')).strip()
                try:
                    f_aplicado = datetime.strptime(fecha_aplicado_str, "%Y-%m-%d").date()
                except:
                    f_aplicado = hoy  # fallback: desde hoy

                uds = leer_ventas_desde(cnx, codigo, f_aplicado)
                actualizar_uds_vendidas(ws, idx, uds)
                logger.info(f"📊 SEGUIMIENTO: {codigo} {nombre} → Uds_Vendidas desde {f_aplicado}: {uds}")

            # ── CANCELAR manualmente (escribir 'Cancelar' en Estado) ──────
            elif estado == 'Cancelar':
                orig_max  = str(row.get('DtoMax_Original', '0')).strip() or '0'
                orig_def  = str(row.get('DtoDef_Original', '0')).strip() or '0'
                orig_modo = str(row.get('Modo_Original', 'F')).strip()
                orig_modo_cod = MODO_MAP.get(orig_modo, orig_modo)

                aplicar_descuento(cnx, codigo, orig_max, orig_def, orig_modo_cod)
                actualizar_estado(ws, idx, 'Cancelado', str(hoy))
                logger.info(f"❌ CANCELADA: {codigo} {nombre} → valores originales restaurados")
                revertidas += 1

        except Exception as e:
            logger.error(f"✗ Error procesando {codigo}: {e}")
            errores += 1

    cnx.close()

    logger.info("=" * 60)
    logger.info(f"RESUMEN: Activadas={activadas} | Revertidas={revertidas} | Errores={errores}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
