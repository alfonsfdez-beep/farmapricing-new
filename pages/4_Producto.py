"""
Drill-down por producto: ficha individual con datos de Farmatic, comparación con
mercado y histórico de decisiones tomadas sobre ese artículo.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from lib import data as d  # noqa: E402
from lib import decisions as dec  # noqa: E402
from lib import ui  # noqa: E402

ui.setup_page("Producto")
ui.page_header("Ficha de producto", "Drill-down individual: datos, comparación con mercado e histórico")

rec = d.get_recomendaciones()
mer = d.get_mercado()
hist_p = dec.get_pricing_decisions()
hist_s = dec.get_surtido_decisions()

# Buscador
left, right = st.columns([3, 1])
with left:
    q = st.text_input("Busca por CN o descripción", placeholder="ej: 166701 o THEALOZ")
with right:
    st.write("")
    st.write("")
    if st.button("Limpiar"):
        st.session_state.pop("prod_q", None)
        st.rerun()

if not q:
    st.info("Empieza escribiendo un código nacional o parte de la descripción del producto.")
    ui.sidebar_refresh_button()
    st.stop()

ql = q.lower().strip()

# Buscar en recomendaciones primero, luego en mercado
matches_rec = pd.DataFrame()
if not rec.empty:
    matches_rec = rec[
        rec["IdArticulo"].astype(str).str.lower().str.contains(ql, na=False)
        | rec["Descripcion"].astype(str).str.lower().str.contains(ql, na=False)
    ].copy()

matches_mer = pd.DataFrame()
if not mer.empty:
    cn_match = mer["CN"].astype(str).str.lower().str.contains(ql, na=False)
    desc_col = "Descripcion_Mercado" if "Descripcion_Mercado" in mer.columns else "Descripcion"
    desc_match = mer[desc_col].astype(str).str.lower().str.contains(ql, na=False) if desc_col in mer.columns else False
    matches_mer = mer[cn_match | desc_match].copy()

# Lista de candidatos (CN únicos)
candidatos = pd.concat([
    matches_rec[["IdArticulo", "Descripcion"]].rename(columns={"IdArticulo": "CN"})
        if not matches_rec.empty else pd.DataFrame(),
    matches_mer[["CN", "Descripcion_Mercado"]].rename(columns={"Descripcion_Mercado": "Descripcion"})
        if not matches_mer.empty else pd.DataFrame(),
], ignore_index=True).drop_duplicates(subset=["CN"]).head(40)

if candidatos.empty:
    st.warning("No se encontraron productos que coincidan.")
    ui.sidebar_refresh_button()
    st.stop()

# Selector
candidatos["label"] = candidatos["CN"] + " — " + candidatos["Descripcion"].astype(str).str.slice(0, 80)
selected_label = st.selectbox(f"{len(candidatos)} coincidencias", candidatos["label"].tolist())
cn = candidatos.loc[candidatos["label"] == selected_label, "CN"].iloc[0]

st.divider()

# --- Cargar datos del producto seleccionado ---
in_rec = rec[rec["IdArticulo"].astype(str) == str(cn)] if not rec.empty else pd.DataFrame()
in_mer = mer[mer["CN"].astype(str) == str(cn)] if not mer.empty else pd.DataFrame()

# Encabezado
desc = ""
if not in_rec.empty:
    desc = str(in_rec.iloc[0].get("Descripcion", ""))
elif not in_mer.empty and "Descripcion_Mercado" in in_mer.columns:
    desc = str(in_mer.iloc[0]["Descripcion_Mercado"])

st.markdown(f"### {desc}")
st.caption(f"CN: **{cn}**")

# Métricas clave
if not in_rec.empty:
    r = in_rec.iloc[0]
    clasif = str(r.get("Clasificacion", "-"))
    badge = ui.clasif_badge(clasif)
    st.markdown(f"Clasificación actual: {badge}", unsafe_allow_html=True)
    st.caption(
        f"Familia: {r.get('Familia', '-')} · Subfamilia: {r.get('Subfamilia', '-')} · "
        f"Laboratorio: {r.get('Laboratorio', '-')}"
    )

# --- Datos básicos ---
st.subheader("Mi farmacia")
if in_rec.empty:
    st.warning("Este producto no está en tu catálogo de Farmatic (o no está en el cruce con mercado).")
else:
    r = in_rec.iloc[0]
    c = st.columns(5)
    c[0].metric("PVP", ui.euro(r.get("PVP")))
    c[1].metric("Coste (PUC)", ui.euro(r.get("PUC")))
    c[2].metric("Stock", f"{int(r.get('StockActual') or 0)}")
    c[3].metric("Ventas 30d", f"{int(r.get('Ventas_30d') or 0)}")
    dias = r.get("DiasStock")
    c[4].metric("Días stock", f"{dias:.0f}" if pd.notna(dias) else "-")

    c2 = st.columns(4)
    c2[0].metric("Ventas 7d", f"{int(r.get('Ventas_7d') or 0)}")
    c2[1].metric("Ventas 90d", f"{int(r.get('Ventas_90d') or 0)}")
    c2[2].metric("Facturación 30d", ui.euro(r.get("Facturacion_30d")))
    c2[3].metric("Margen %", ui.pct(r.get("MargenPct")) if pd.notna(r.get("MargenPct")) else "-")

# --- Comparación con mercado ---
st.subheader("Mercado (350 farmacias)")
if in_mer.empty and (in_rec.empty or pd.isna(in_rec.iloc[0].get("PVP_Mercado"))):
    st.info("Sin referencia de mercado para este producto.")
else:
    # Preferir datos de la pestaña 'mercado' por ser la fuente; fallback a rec
    if not in_mer.empty:
        m = in_mer.iloc[0]
    else:
        m = in_rec.iloc[0]
    c = st.columns(4)
    c[0].metric("PVP mercado", ui.euro(m.get("PVP_Mercado")))
    c[1].metric("Uds/farmacia (media)", f"{m.get('Uds_por_Farmacia') or 0:.1f}")
    if "Uds_Mercado" in m:
        c[2].metric("Uds totales mercado", f"{int(m.get('Uds_Mercado') or 0):,}".replace(",", "."))
    if "VentaTotal_Mercado" in m:
        c[3].metric("Venta total mercado", ui.euro(m.get("VentaTotal_Mercado")))

    if not in_rec.empty:
        r = in_rec.iloc[0]
        delta = r.get("DeltaPctMercado")
        if pd.notna(delta):
            color = "#C00000" if delta > 0 else "#00B050"
            sign = "+" if delta > 0 else ""
            st.markdown(
                f"<div style='font-size:18px;margin-top:8px'>"
                f"Tu PVP vs mercado: "
                f"<span style='color:{color};font-weight:600'>{sign}{delta*100:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# --- Recomendación actual ---
st.subheader("Recomendación del motor")
if in_rec.empty:
    st.info("Sin recomendación.")
else:
    r = in_rec.iloc[0]
    tipo = str(r.get("TipoCambio", "NINGUNO"))
    if tipo == "NINGUNO":
        motivo = r.get("MotivoBloqueo") or r.get("Justificacion") or "-"
        st.info(f"NO_TOCAR — {motivo}")
    else:
        c = st.columns(4)
        c[0].metric("Tipo", tipo)
        if tipo == "PVP":
            c[1].metric("PVP propuesto", ui.euro(r.get("PVP_Propuesto")))
        elif tipo == "PROMO":
            c[1].metric("Descuento", ui.pct_already(r.get("Descuento_Pct")))
        c[2].metric("Impacto facturación", ui.euro(r.get("Impacto_Facturacion_30d_est")))
        c[3].metric(
            "BreakEven uplift",
            ui.pct_already(r.get("BreakEven_Uplift_Pct")) if pd.notna(r.get("BreakEven_Uplift_Pct")) else "-",
        )

        just = str(r.get("Justificacion", "") or "")
        if just:
            st.caption(f"Justificación: {just}")

        with st.expander("Decidir sobre esta recomendación"):
            notas = st.text_input("Notas", key=f"ficha_notas_{cn}")
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("Aprobar", key=f"ficha_ap_{cn}", type="primary", use_container_width=True):
                    dec.log_pricing_decision(r.to_dict(), "Aprobado", notas)
                    st.success("Aprobado.")
                    d.refresh_all(); st.rerun()
            with b2:
                if st.button("Aplicado", key=f"ficha_apl_{cn}", use_container_width=True):
                    dec.log_pricing_decision(r.to_dict(), "Aplicado", notas)
                    st.success("Marcado como aplicado.")
                    d.refresh_all(); st.rerun()
            with b3:
                if st.button("Posponer", key=f"ficha_po_{cn}", use_container_width=True):
                    dec.log_pricing_decision(r.to_dict(), "Pospuesto", notas)
                    st.info("Pospuesto.")
                    d.refresh_all(); st.rerun()
            with b4:
                if st.button("Rechazar", key=f"ficha_re_{cn}", use_container_width=True):
                    dec.log_pricing_decision(r.to_dict(), "Rechazado", notas)
                    st.warning("Rechazado.")
                    d.refresh_all(); st.rerun()

# --- Histórico de decisiones ---
st.subheader("Histórico de decisiones sobre este producto")
hist_pp = hist_p[hist_p["IdArticulo"].astype(str) == str(cn)] if not hist_p.empty else pd.DataFrame()
hist_ss = hist_s[hist_s["CN"].astype(str) == str(cn)] if not hist_s.empty else pd.DataFrame()

if hist_pp.empty and hist_ss.empty:
    st.info("Aún no hay decisiones tomadas sobre este artículo.")
else:
    if not hist_pp.empty:
        st.markdown("**Pricing**")
        st.dataframe(
            hist_pp.sort_values("Timestamp_dt", ascending=False)[
                [c for c in ["Timestamp", "TipoCambio", "PVP_Actual", "PVP_Propuesto",
                              "Descuento_Pct", "Decision", "Estado", "Notas"]
                 if c in hist_pp.columns]
            ],
            use_container_width=True, hide_index=True,
        )
    if not hist_ss.empty:
        st.markdown("**Surtido**")
        st.dataframe(
            hist_ss.sort_values("Timestamp_dt", ascending=False)[
                [c for c in ["Timestamp", "Decision", "Notas"] if c in hist_ss.columns]
            ],
            use_container_width=True, hide_index=True,
        )

ui.sidebar_refresh_button()
