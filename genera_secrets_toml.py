"""
Convierte google_credentials.json a formato TOML para Streamlit Cloud Secrets.

Uso:
    python genera_secrets_toml.py

Lee ../google_credentials.json (la raíz del proyecto) y escribe en consola
el TOML listo para pegar en Streamlit Cloud -> Advanced settings -> Secrets.
"""
from __future__ import annotations

import json
from pathlib import Path

# Buscar el JSON en raíz del proyecto o en la carpeta actual
candidates = [
    Path(__file__).resolve().parent.parent / "google_credentials.json",
    Path(__file__).resolve().parent / "google_credentials.json",
    Path.cwd() / "google_credentials.json",
]

creds_path = next((p for p in candidates if p.exists()), None)
if creds_path is None:
    raise SystemExit(
        "No se encuentra google_credentials.json. Asegúrate de que está en "
        "la raíz del proyecto Farmapricing Agent."
    )

creds = json.loads(creds_path.read_text(encoding="utf-8"))

print()
print("# ==========================================================")
print("# Pega este bloque en Streamlit Cloud:")
print("#   App settings -> Secrets")
print("# ==========================================================")
print()
print('GOOGLE_SHEET_ID = "1_rn_2CTc8yEcnZUUei-ytKAEW0lph3QeUKojCS3WRd8"')
print('SHEET_TAB_MERCADO = "mercado"')
print('SHEET_TAB_RECOMENDACIONES = "Recomendaciones"')
print('SHEET_TAB_RECOMENDACIONES_RESUMEN = "Recomendaciones_Resumen"')
print('SHEET_TAB_HUECOS_FAMILIA = "Huecos_Familia"')
print('SHEET_TAB_HUECOS_SUBFAMILIA = "Huecos_Subfamilia"')
print('SHEET_TAB_HUECOS_PRODUCTOS = "Huecos_Productos"')
print('SHEET_TAB_DECISIONES_PRICING = "Decisiones_Pricing"')
print('SHEET_TAB_DECISIONES_SURTIDO = "Decisiones_Surtido"')
print()
print("[gcp_service_account]")
for k in ("type", "project_id", "private_key_id"):
    if k in creds:
        print(f'{k} = "{creds[k]}"')

# private_key con saltos de línea, formato multilínea TOML
if "private_key" in creds:
    print('private_key = """' + creds["private_key"] + '"""')

for k in ("client_email", "client_id", "auth_uri", "token_uri",
          "auth_provider_x509_cert_url", "client_x509_cert_url",
          "universe_domain"):
    if k in creds:
        print(f'{k} = "{creds[k]}"')

print()
print("# ==========================================================")
print(f"# (Generado desde: {creds_path})")
print("# ==========================================================")
