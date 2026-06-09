"""
Catálogo Comparativo - Análisis completo de productos vs. mercado.

Visualiza todos los productos con sus precios, márgenes y ventas comparados
con el mercado. Filtra por familia/subfamilia y por disponibilidad de stock.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from lib import data as d  # noqa: E402
from lib import ui  # noqa: E402

ui.setup_page("Catálogo")
ui.page_header(
    "Catálogo Comparativo",
    "Análisis de precios y ventas de tus productos vs. el mercado",
)

# ── Cargar datos ──────────────────────────────────────────────────────────────
# Para Catálogo, usar todos los productos (incluyendo NO_TOCAR)
rec = d.get_catalogo_todos()
mercado = d.get_mercado()
lab_lookup = d.get_laboratorios_lookup()  # Tabla para convertir código → nombre


if mercado.empty:
    st.warning("No hay datos de mercado disponibles. Lanza el pipeline en el PC.")
    st.stop()

# Intentar cargar pricing_base.csv (tiene TODO: NO_TOCAR, GANCHO, etc)
pricing_base_path = Path(__file__).resolve().parent.parent.parent / "output" / "pricing_base.csv"
pricing_base = None
if pricing_base_path.exists():
    try:
        pricing_base = pd.read_csv(
            pricing_base_path,
            dtype={"IdArticulo": str},
            usecols=["IdArticulo", "PVP", "StockActual", "Ventas_365d"]
        )
        pricing_base["IdArticulo"] = pricing_base["IdArticulo"].astype(str).str.strip()
        pricing_base = pricing_base.rename(columns={"IdArticulo": "CN"})
    except Exception:
        pricing_base = None

# ── Preparar DataFrame combinado ───────────────────────────────────────────────
# Partir de MERCADO (todos los productos) y agregar datos de farmacia
# Seleccionar columnas que existan en mercado
cols_mercado = ["CN", "Familia", "Subfamilia", "PVP_Mercado", "Uds_por_Farmacia", "Uds_Mercado"]
cols_mercado = [c for c in cols_mercado if c in mercado.columns]

# Agregar descripción si existe (puede ser "Descripcion_Mercado" o "Descripcion")
desc_col = None
if "Descripcion_Mercado" in mercado.columns:
    desc_col = "Descripcion_Mercado"
elif "Descripcion" in mercado.columns:
    desc_col = "Descripcion"

if desc_col:
    cols_mercado.insert(1, desc_col)

# Agregar Laboratorio si existe (columna opcional de mercado)
if "Laboratorio" in mercado.columns:
    cols_mercado.append("Laboratorio")

df = mercado[cols_mercado].copy()

# Renombrar descripción si es necesario
if "Descripcion_Mercado" in df.columns:
    df = df.rename(columns={"Descripcion_Mercado": "Descripcion"})

df["CN"] = df["CN"].astype(str).str.strip()

# Si hay recomendaciones, agregar datos de la farmacia
if not rec.empty:
    # Usar columnas que existen en el CSV publicado
    cols_rec = ["Codigo", "PVP", "PMC", "Margen"]

    # Agregar opcionales si existen
    if "PrecioRecomendado" in rec.columns:
        cols_rec.append("PrecioRecomendado")
    if "TipoCambio" in rec.columns:
        cols_rec.append("TipoCambio")

    # Agregar Laboratorio y LaboratorioNombre si existen (para enriquecer datos)
    if "LaboratorioId" in rec.columns:
        cols_rec.append("LaboratorioId")
    if "LaboratorioNombre" in rec.columns:
        cols_rec.append("LaboratorioNombre")

    # Filtrar solo columnas que existen
    cols_rec = [c for c in cols_rec if c in rec.columns]

    rec_c = rec[cols_rec].copy()
    rec_c["Codigo"] = rec_c["Codigo"].astype(str).str.strip()
    rec_c = rec_c.rename(columns={"Codigo": "CN"})

    # Merge con los datos de la farmacia (left join en mercado para mantener todos)
    df = df.merge(rec_c, on="CN", how="left")
else:
    # Si no hay recomendaciones, crear columnas vacías con nombres correctos
    df["PVP"] = pd.NA
    df["PMC"] = pd.NA
    df["Margen"] = pd.NA

# Renombrar para claridad y mostrar
rename_dict = {
    "PVP": "Precio Farmacia",
    "PMC": "Costo Farmacia",
    "Margen": "Margen Farmacia (%)",
    "PVP_Mercado": "Precio Mercado",
}

# Renombrar si existen
df = df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns})

# Calcular margen de mercado si es posible
if "Costo Farmacia" in df.columns and "Precio Mercado" in df.columns:
    df["Margen Mercado (%)"] = (
        ((df["Precio Mercado"] - df["Costo Farmacia"]) / df["Precio Mercado"] * 100)
        .round(1)
    )

# Renombrar otras columnas si existen
other_renames = {
    "Uds_por_Farmacia": "Uds Promedio Mercado",
    "Uds_Mercado": "Uds Totales Mercado",
}
df = df.rename(columns={k: v for k, v in other_renames.items() if k in df.columns})

# Asegurar que LaboratorioNombre está en df
# Intentar primero con lab_lookup (datos de Google Sheets)
if not lab_lookup.empty and "Laboratorio" in df.columns and "LaboratorioNombre" not in df.columns:
    df = df.merge(lab_lookup[["Laboratorio", "LaboratorioNombre"]].drop_duplicates(),
                   on="Laboratorio", how="left")

# Si aún no tenemos LaboratorioNombre, intentar desde rec
if "LaboratorioNombre" not in df.columns and not rec.empty and "LaboratorioNombre" in rec.columns:
    rec_lab = rec[["Codigo", "LaboratorioNombre"]].copy()
    rec_lab["Codigo"] = rec_lab["Codigo"].astype(str).str.strip()
    rec_lab = rec_lab.rename(columns={"Codigo": "CN"})
    if "CN" in df.columns:
        df = df.merge(rec_lab, on="CN", how="left", suffixes=("", "_rec"))
        # Si tenía LaboratorioNombre de lab_lookup, mantener; sino usar de rec
        if "LaboratorioNombre_rec" in df.columns:
            df["LaboratorioNombre"] = df["LaboratorioNombre"].fillna(df["LaboratorioNombre_rec"])
            df = df.drop("LaboratorioNombre_rec", axis=1)

# ── Filtros ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

# Selector de stock
mostrar_stock = st.sidebar.radio(
    "Mostrar productos:",
    options=["Con stock", "Todos"],
    horizontal=False,
    help="Filtra por disponibilidad de stock en tu farmacia"
)

if mostrar_stock == "Con stock":
    df = df[df["Stock"] > 0].copy()

# Selector de competitividad de precios
competitividad = st.sidebar.radio(
    "Competitividad de precios:",
    options=["Todos", "Más baratos que mercado", "Más caros que mercado"],
    horizontal=False,
    help="Compara tu precio vs. el precio medio del mercado"
)

if competitividad == "Más baratos que mercado":
    df = df[(df["Precio Farmacia"] < df["Precio Mercado"]) & (df["Precio Farmacia"].notna())].copy()
elif competitividad == "Más caros que mercado":
    df = df[(df["Precio Farmacia"] > df["Precio Mercado"]) & (df["Precio Farmacia"].notna())].copy()

# Filtros de familia y subfamilia
fam_options = sorted([f for f in df["Familia"].dropna().unique() if f != ""])
if fam_options:
    fam_sel = st.sidebar.multiselect(
        "Familia",
        options=fam_options,
        default=[]
    )
    if fam_sel:
        df = df[df["Familia"].isin(fam_sel)]

subfam_options = sorted([s for s in df["Subfamilia"].dropna().unique() if s != ""])
if subfam_options:
    subfam_sel = st.sidebar.multiselect(
        "Subfamilia",
        options=subfam_options,
        default=[]
    )
    if subfam_sel:
        df = df[df["Subfamilia"].isin(subfam_sel)]

# Filtro por Laboratorio (Marca) - crear mapeo ANTES de filtrar
# Usar datos completos de rec para el mapeo
lab_map_complete = {}
if not rec.empty and "Laboratorio" in rec.columns:
    if "LaboratorioNombre" in rec.columns:
        for _, row in rec[["Laboratorio", "LaboratorioNombre"]].drop_duplicates().iterrows():
            codigo = str(row["Laboratorio"]).strip()
            nombre = str(row["LaboratorioNombre"]).strip() if pd.notna(row["LaboratorioNombre"]) else ""
            lab_map_complete[codigo] = nombre if nombre and nombre != "nan" else codigo
    else:
        for codigo in rec["Laboratorio"].dropna().unique():
            lab_map_complete[str(codigo).strip()] = str(codigo).strip()

# Si aún no tenemos mapeo, usar de df
if not lab_map_complete and "Laboratorio" in df.columns:
    if "LaboratorioNombre" in df.columns:
        for _, row in df[["Laboratorio", "LaboratorioNombre"]].drop_duplicates().iterrows():
            codigo = str(row["Laboratorio"]).strip()
            nombre = str(row["LaboratorioNombre"]).strip() if pd.notna(row["LaboratorioNombre"]) else ""
            lab_map_complete[codigo] = nombre if nombre and nombre != "nan" else codigo
    else:
        for codigo in df["Laboratorio"].dropna().unique():
            lab_map_complete[str(codigo).strip()] = str(codigo).strip()

if lab_map_complete and "Laboratorio" in df.columns:
    lab_displays = sorted(set(lab_map_complete.values()))
    lab_sel = st.sidebar.multiselect(
        "Laboratorio (Marca)",
        options=lab_displays,
        default=[]
    )
    if lab_sel:
        # Convertir displays seleccionados de vuelta a códigos para filtrar
        lab_codes = [codigo for codigo, display in lab_map_complete.items() if display in lab_sel]
        df = df[df["Laboratorio"].astype(str).str.strip().isin(lab_codes)]

# Búsqueda rápida multi-criterio
st.sidebar.write("---")
q = st.sidebar.text_input("🔍 Buscar en tabla", placeholder="CN, descripción, marca...")
if q:
    ql = q.lower()
    # Construir máscara de búsqueda
    mask = (
        df["CN"].astype(str).str.lower().str.contains(ql, na=False)
        | df["Descripcion"].astype(str).str.lower().str.contains(ql, na=False)
        | df["Familia"].astype(str).str.lower().str.contains(ql, na=False)
        | df["Subfamilia"].astype(str).str.lower().str.contains(ql, na=False)
    )
    # Agregar búsqueda en laboratorios (nombre si existe, sino código)
    if "LaboratorioNombre" in df.columns:
        mask = mask | df["LaboratorioNombre"].astype(str).str.lower().str.contains(ql, na=False)
    if "Laboratorio" in df.columns:
        mask = mask | df["Laboratorio"].astype(str).str.lower().str.contains(ql, na=False)

    df = df[mask]

# ── Resumen ───────────────────────────────────────────────────────────────────
st.divider()
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total de productos", len(df))
c2.metric("Productos con stock", (df["Stock"] > 0).sum())

# Calcular promedio solo de productos que sí tiene la farmacia
productos_con_precio = df[df["Precio Farmacia"].notna()]
precio_prom = productos_con_precio['Precio Farmacia'].mean() if len(productos_con_precio) > 0 else 0
margen_prom = productos_con_precio['Margen Farmacia (%)'].mean() if len(productos_con_precio) > 0 else 0

c3.metric("Precio promedio", f"€{precio_prom:.2f}" if precio_prom > 0 else "N/A")
c4.metric("Margen promedio", f"{margen_prom:.1f}%" if margen_prom > 0 else "N/A")

st.divider()

# ── Tabla de productos ────────────────────────────────────────────────────────
# Seleccionar y ordenar columnas para mostrar
columnas_mostrar = [
    "CN",
    "Descripcion",
    "Familia",
    "Subfamilia",
    "Precio Farmacia",
    "Precio Mercado",
    "Margen Farmacia (%)",
    "Margen Mercado (%)",
    "Stock",
    "Ventas 12m",
    "Uds Promedio Mercado",
]

# Filtrar columnas que existen
columnas_mostrar = [c for c in columnas_mostrar if c in df.columns]

# GUARDAR VALORES NUMÉRICOS ORIGINALES ANTES DE FORMATEAR
df_numericos = df[["Precio Farmacia", "Precio Mercado"]].copy().reset_index(drop=True)

# Formatear para visualización
df_display = df[columnas_mostrar].copy()

# Formatear números y truncar descripción
if "Descripcion" in df_display.columns:
    df_display["Descripcion"] = df_display["Descripcion"].apply(
        lambda x: str(x)[:30] + "..." if len(str(x)) > 30 else str(x)
    )

if "Precio Farmacia" in df_display.columns:
    df_display["Precio Farmacia"] = df_display["Precio Farmacia"].apply(
        lambda x: f"€{x:.2f}" if pd.notna(x) else "-"
    )

if "Precio Mercado" in df_display.columns:
    df_display["Precio Mercado"] = df_display["Precio Mercado"].apply(
        lambda x: f"€{x:.2f}" if pd.notna(x) else "-"
    )

if "Margen Farmacia (%)" in df_display.columns:
    df_display["Margen Farmacia (%)"] = df_display["Margen Farmacia (%)"].apply(
        lambda x: f"{x:.0f}%" if pd.notna(x) else "-"
    )

if "Margen Mercado (%)" in df_display.columns:
    df_display["Margen Mercado (%)"] = df_display["Margen Mercado (%)"].apply(
        lambda x: f"{x:.0f}%" if pd.notna(x) else "-"
    )

if "Ventas 30d" in df_display.columns:
    df_display["Ventas 30d"] = df_display["Ventas 30d"].apply(
        lambda x: int(x) if pd.notna(x) else 0
    )

if "Stock" in df_display.columns:
    df_display["Stock"] = df_display["Stock"].apply(
        lambda x: int(x) if pd.notna(x) else 0
    )

if "Uds Promedio Farmacia" in df_display.columns:
    df_display["Uds Promedio Farmacia"] = df_display["Uds Promedio Farmacia"].apply(
        lambda x: int(x) if pd.notna(x) else 0
    )

if "Uds Promedio Mercado" in df_display.columns:
    df_display["Uds Promedio Mercado"] = df_display["Uds Promedio Mercado"].apply(
        lambda x: int(x) if pd.notna(x) else 0
    )

# Renombrar columnas para hacerlas más compactas
df_display = df_display.rename(columns={
    "Precio Farmacia": "Precio",
    "Precio Mercado": "Merc.",
    "Margen Farmacia (%)": "Mg (%)",
    "Margen Mercado (%)": "Mg M (%)",
    "Ventas 30d": "Ventas",
    "Uds Promedio Farmacia": "Uds",
    "Uds Promedio Mercado": "Uds M",
})

# Resetear índices para sincronización
df_display_temp = df_display.reset_index(drop=True)

# Función para colorear precios
def color_precio_row(row_idx):
    """Retorna estilo CSS para la celda de precio"""
    if row_idx >= len(df_numericos):
        return ""

    p_farm = df_numericos.iloc[row_idx]["Precio Farmacia"]
    p_merc = df_numericos.iloc[row_idx]["Precio Mercado"]

    if pd.notna(p_farm) and pd.notna(p_merc):
        if p_farm > p_merc:
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"  # Rojo (caro)
        elif p_farm < p_merc:
            return "background-color: #ccffcc; color: #009900; font-weight: bold;"  # Verde (barato)
    return ""

# Aplicar estilos manualmente a cada celda de precio
styled_df = df_display_temp.style.apply(
    lambda row: [
        color_precio_row(row.name) if col == "Precio" else ""
        for col in df_display_temp.columns
    ],
    axis=1
)

# Mostrar tabla con estilos
st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True,
    height=600,
    column_config={
        "CN": st.column_config.TextColumn(width="small"),
        "Descripcion": st.column_config.TextColumn(width="medium"),
        "Familia": st.column_config.TextColumn(width="small"),
        "Subfamilia": st.column_config.TextColumn(width="small"),
        "Precio": st.column_config.TextColumn(width="small"),
        "Merc.": st.column_config.TextColumn(width="small"),
        "Mg (%)": st.column_config.TextColumn(width="small"),
        "Mg M (%)": st.column_config.TextColumn(width="small"),
        "Stock": st.column_config.NumberColumn(width="80px"),
        "Ventas": st.column_config.NumberColumn(width="80px"),
        "Uds": st.column_config.NumberColumn(width="60px"),
        "Uds M": st.column_config.NumberColumn(width="60px"),
    }
)

# ── Insights ──────────────────────────────────────────────────────────────────
st.divider()
st.header("📊 Insights")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Oportunidades de Margen")
    # Productos donde tu margen es menor que el mercado
    oportunidades = df[(df["Margen Farmacia (%)"] < df["Margen Mercado (%)"]) & (df["Stock"] > 0)]
    if not oportunidades.empty:
        st.info(f"📈 Tienes {len(oportunidades)} productos donde podrías mejorar margen")
        top_oportunidades = oportunidades.nlargest(5, "Margen Mercado (%)")
        for _, row in top_oportunidades.iterrows():
            diferencia = row["Margen Mercado (%)"] - row["Margen Farmacia (%)"]
            st.caption(
                f"**{row['Descripcion'][:40]}** (CN {row['CN']}): "
                f"Tu margen {row['Margen Farmacia (%)']:.1f}% → Mercado {row['Margen Mercado (%)']:.1f}% (+{diferencia:.1f}pp)"
            )
    else:
        st.success("✅ Tus márgenes están al nivel del mercado")

with col2:
    st.subheader("Productos sin Stock")
    sin_stock = df[df["Stock"] == 0]
    if not sin_stock.empty:
        st.warning(f"⚠️ Tienes {len(sin_stock)} productos sin stock")
        st.caption("Considera reabastecer los de mayor demanda en el mercado")
    else:
        st.success("✅ Todos tus productos tienen stock")

# ── Descarga de datos ─────────────────────────────────────────────────────────
st.divider()
st.subheader("📥 Descargar datos")

csv = df_display.to_csv(index=False)
st.download_button(
    label="Descargar como CSV",
    data=csv,
    file_name="catalogo_comparativo.csv",
    mime="text/csv",
)
