"""
Cliente Google Sheets para la app. Lee credenciales de st.secrets (cloud)
o de un fichero local google_credentials.json (desarrollo).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

from . import config as cfg

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource(show_spinner=False)
def _client() -> gspread.Client:
    """Construye el cliente gspread. Se cachea durante la sesión."""
    creds_info = None

    # 1) Streamlit secrets — formato esperado: una tabla [gcp_service_account]
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
    except Exception:
        pass

    # 2) Variable de entorno con JSON inline
    if creds_info is None:
        env_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if env_json:
            creds_info = json.loads(env_json)

    # 3) Fichero local (desarrollo)
    if creds_info is None:
        for candidate in (
            Path.cwd() / "google_credentials.json",
            Path(__file__).resolve().parent.parent.parent / "google_credentials.json",
        ):
            if candidate.exists():
                creds_info = json.loads(candidate.read_text())
                break

    if creds_info is None:
        raise RuntimeError(
            "No se encontraron credenciales. Configura st.secrets['gcp_service_account'] "
            "en Streamlit Cloud, o coloca google_credentials.json en la raíz del proyecto."
        )

    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(creds)


def open_sheet():
    return _client().open_by_key(cfg.GOOGLE_SHEET_ID)


def list_tabs() -> list[str]:
    return [ws.title for ws in open_sheet().worksheets()]


def _find_worksheet(tab_name: str):
    sh = open_sheet()
    by_title = {ws.title: ws for ws in sh.worksheets()}
    if tab_name in by_title:
        return by_title[tab_name]
    # Tolerancia: case-insensitive y substring
    lower_map = {t.lower(): t for t in by_title}
    if tab_name.lower() in lower_map:
        return by_title[lower_map[tab_name.lower()]]
    for t in by_title:
        if tab_name.lower() in t.lower():
            return by_title[t]
    raise WorksheetNotFound(tab_name)


def read_tab(tab_name: str):
    """Lee una pestaña como lista de listas (incluye cabecera)."""
    ws = _find_worksheet(tab_name)
    return ws.get_all_values()


def append_row(tab_name: str, row: list[str], create_if_missing: bool = True,
               header: list[str] | None = None) -> None:
    """Añade una fila a una pestaña. Si no existe y create_if_missing, la crea con cabecera."""
    sh = open_sheet()
    try:
        ws = _find_worksheet(tab_name)
    except WorksheetNotFound:
        if not create_if_missing:
            raise
        ws = sh.add_worksheet(title=tab_name, rows=200, cols=max(len(row) + 2, 20))
        if header:
            ws.append_row(header, value_input_option="USER_ENTERED")
    ws.append_row(row, value_input_option="USER_ENTERED")
