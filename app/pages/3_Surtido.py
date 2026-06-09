"""
Análisis de surtido - drill-down jerárquico Familia -> Subfamilia -> Productos.

Vista principal: tres paneles apilados verticalmente.
  1. FAMILIAS: tabla con cobertura y oportunidad. Click en una fila la fija.
  2. SUBFAMILIAS: aparece tras seleccionar familia. Click fija subfamilia.
  3. PRODUCTOS: aparece tras seleccionar subfamilia. Aquí se decide comprar/descartar.
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

ui.setup_page("Surtido")
ui.page_header(
    "Análisis de surtido",
    "Drill-down jerárquico: selecciona una familia → subfamilia → productos que te faltan.",
)

fam = d.get_huecos_familia()
sub = d.get_huecos_subfamilia()
prod = d.get_huecos_productos()

if fam.empty and sub.empty and prod.empty:
    st.warning(
        "No hay datos de huecos. Ejecuta en el PC: "
        "`python scripts\\06_huecos_surtido.py --publish` o `python run_all.py`."
    )
    st.stop()


# ------------- Helpers --------------------------------------------------------

def _fmt_euro_compact(v) -> str:
    """Formatea un valor en € compacto: 1.234.567 € -> '1,2 M€'."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "-"
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f} M€".replace(".", ",")
    if abs(v) >= 1_000:
        return f"{v/1_000:.0f} K€"
    return f"{v:.0f} €"


# Inicializar estado de selección
if "fam_sel" not in st.session_state:
    st.session_state.fam_sel = None
if "sub_sel" not in st.session_state:
    st.session_state.sub_sel = None


# ------------- KPIs globales --------------------------------------------------
if not fam.empty:
    tot_skus = int(fam["SKUs_Mercado"].sum())
    tot_tengo = int(fam["SKUs_Que_Tengo"].sum())
    tot_falta_eur = float(fam["Venta_Faltantes"].sum() or 0)
    cobertura_pond = None
    tot_eur = fam["Venta_Mercado_Total"].sum()
    if tot_eur > 0:
        cobertura_pond = (fam["Cobertura_Pct"] * fam["Venta_Mercado_Total"]).sum() / tot_eur

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SKUs del mercado", f"{tot_skus:,}".replace(",", "."))
    c2.metric("SKUs que tengo", f"{tot_tengo:,}".replace(",", "."))
    c3.metric(
        "Cobertura ponderada",
        f"{cobertura_pond:.1f}%" if cobertura_pond is not None else "-",
    )
    c4.metric("Venta perdida (€)", _fmt_euro_compact(tot_falta_eur))

st.divider()


# ===================== PANEL 1: FAMILIAS ======================================
st.subheader("1. Familias")
st.caption("Click en una fila para ver sus subfamilias.")

if fam.empty:
    st.info("No hay datos de familias.")
else:
    fam_view = fam[[
        "Familia", "SKUs_Mercado", "SKUs_Que_Tengo", "SKUs_Que_Me_Faltan",
        "Cobertura_Pct", "Venta_Faltantes",
    ]].copy()
    fam_view = fam_view.sort_values("Venta_Faltantes", ascending=False).reset_index(drop=True)

    event = st.dataframe(
        fam_view,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tabla_familias",
        height=380,
        column_config={
            "Familia": st.column_config.TextColumn("Familia", width="medium"),
            "SKUs_Mercado": st.column_config.NumberColumn("SKUs mercado", format="%d", width="small"),
            "SKUs_Que_Tengo": st.column_config.NumberColumn("Tengo", format="%d", width="small"),
            "SKUs_Que_Me_Faltan": st.column_config.NumberColumn("Faltan", format="%d", width="small"),
            "Cobertura_Pct": st.column_config.ProgressColumn(
                "Cobertura", format="%.0f%%", min_value=0, max_value=100,
            ),
            "Venta_Faltantes": st.column_config.NumberColumn(
                "Te falta (€)", format="%.0f €", width="small",
            ),
        },
    )

    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        new_fam = fam_view.iloc[selected_rows[0]]["Familia"]
        # Si cambias de familia, reset de subfamilia
        if new_fam != st.session_state.fam_sel:
            st.session_state.sub_sel = None
        st.session_state.fam_sel = new_fam

    if st.session_state.fam_sel:
        a, b = st.columns([4, 1])
        a.success(f"Familia seleccionada: **{st.session_state.fam_sel}**")
        if b.button("Quitar selección de familia", use_container_width=True):
            st.session_state.fam_sel = None
            st.session_state.sub_sel = None
            st.rerun()


# ===================== PANEL 2: SUBFAMILIAS ===================================
if st.session_state.fam_sel:
    st.divider()
    st.subheader(f"2. Subfamilias de {st.session_state.fam_sel}")
    st.caption("Haz clic en una fila para ver los productos que te faltan.")

    sub_view = sub[sub["Familia"] == st.session_state.fam_sel].copy()
    if sub_view.empty:
        st.info("No hay subfamilias para esta familia.")
    else:
        sub_view = sub_view[[
            "Subfamilia", "SKUs_Mercado", "SKUs_Que_Tengo", "SKUs_Que_Me_Faltan",
            "Cobertura_Pct", "Venta_Faltantes",
        ]].copy()
        sub_view = sub_view.sort_values("Venta_Faltantes", ascending=False).reset_index(drop=True)

        event_sub = st.dataframe(
            sub_view,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"tabla_subfamilias_{st.session_state.fam_sel}",
            column_config={
                "Subfamilia": st.column_config.TextColumn("Subfamilia", width="large"),
                "SKUs_Mercado": st.column_config.NumberColumn("SKUs mercado", format="%d", width="small"),
                "SKUs_Que_Tengo": st.column_config.NumberColumn("Tengo", format="%d", width="small"),
                "SKUs_Que_Me_Faltan": st.column_config.NumberColumn("Faltan", format="%d", width="small"),
                "Cobertura_Pct": st.column_config.ProgressColumn(
                    "Cobertura", format="%.0f%%", min_value=0, max_value=100,
                ),
                "Venta_Faltantes": st.column_config.NumberColumn(
                    "Venta perdida (€)", format="%.0f €", width="medium",
                ),
            },
        )

        selected_sub_rows = event_sub.selection.rows if event_sub.selection else []
        if selected_sub_rows:
            new_sub = sub_view.iloc[selected_sub_rows[0]]["Subfamilia"]
            if new_sub != st.session_state.sub_sel:
                st.session_state.sub_sel = new_sub
                st.rerun()

        if st.session_state.sub_sel and st.session_state.sub_sel in sub_view["Subfamilia"].values:
            a, b = st.columns([4, 1])
            a.success(f"Subfamilia seleccionada: **{st.session_state.sub_sel}**")
            if b.button("✕ Quitar selección", use_container_width=True):
                st.session_state.sub_sel = None
                st.rerun()


# ===================== PANEL 3: PRODUCTOS =====================================
if st.session_state.fam_sel and st.session_state.sub_sel:
    st.divider()
    st.subheader(
        f"3. Productos que te faltan en {st.session_state.sub_sel}"
    )
    st.caption(
        f"Familia: {st.session_state.fam_sel} · "
        f"Subfamilia: {st.session_state.sub_sel}"
    )

    if prod.empty:
        st.info(
            "No hay listado de productos. Lanza `python scripts\\06_huecos_surtido.py --publish` "
            "con un filtro --min-uds adecuado."
        )
    else:
        # Filtro por familia + subfamilia activas
        view = prod[
            (prod["Familia"] == st.session_state.fam_sel)
            & (prod["Subfamilia"] == st.session_state.sub_sel)
        ].copy()

        # Filtros adicionales en sidebar
        st.sidebar.header("Filtros productos")
        min_uds = st.sidebar.slider("Min. uds/farmacia", 0, 100, 5)
        incluir_decididos = st.sidebar.checkbox("Incluir ya decididos", value=False)
        q = st.sidebar.text_input("Buscar (CN o descripción)", "")

        if min_uds:
            view = view[view["Uds_por_Farmacia"] >= min_uds]
        if q:
            ql = q.lower()
            view = view[
                view["CN"].astype(str).str.lower().str.contains(ql, na=False)
                | view["Descripcion"].astype(str).str.lower().str.contains(ql, na=False)
            ]

        ya = dec.get_decided_ids("surtido")
        view["_decidido"] = view["CN"].astype(str).isin(ya)
        if not incluir_decididos:
            view = view[~view["_decidido"]]

        view = view.sort_values("Uds_por_Farmacia", ascending=False)

        if view.empty:
            st.warning(
                "No hay productos para esta subfamilia con los filtros actuales. "
                "Quizá no están en `Huecos_Productos` (filtro min-uds del script 06) o ya decidiste todos."
            )
        else:
            st.write(f"**{len(view)} productos** que te faltan en esta subfamilia")

            # Paginación si la lista es larga
            PAGE = 12
            page_key = f"prod_page_{st.session_state.fam_sel}_{st.session_state.sub_sel}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 0
            total_pages = max(1, (len(view) + PAGE - 1) // PAGE)
            st.session_state[page_key] = min(st.session_state[page_key], total_pages - 1)

            if total_pages > 1:
                a, b, c = st.columns([1, 2, 1])
                with a:
                    if st.button("← Anterior", disabled=st.session_state[page_key] == 0,
                                  key=f"{page_key}_prev"):
                        st.session_state[page_key] -= 1
                        st.rerun()
                with b:
                    st.markdown(
                        f"<div style='text-align:center'>Página "
                        f"<b>{st.session_state[page_key] + 1}</b> / {total_pages}</div>",
                        unsafe_allow_html=True,
                    )
                with c:
                    if st.button(
                        "Siguiente →",
                        disabled=st.session_state[page_key] >= total_pages - 1,
                        key=f"{page_key}_next",
                    ):
                        st.session_state[page_key] += 1
                        st.rerun()

            start = st.session_state[page_key] * PAGE
            page_df = view.iloc[start:start + PAGE].copy()

            # Cabecera tipo tabla
            h1, h2, h3, h4, h5 = st.columns([1.2, 5, 1.2, 1.2, 2.5])
            h1.markdown("**CN**")
            h2.markdown("**Descripción**")
            h3.markdown("**PVP €**")
            h4.markdown("**Uds/farm.**")
            h5.markdown("**Acción**")

            for idx, row in page_df.iterrows():
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([1.2, 5, 1.2, 1.2, 2.5])
                    c1.write(str(row.get("CN", "")))
                    desc = str(row.get("Descripcion", ""))
                    if len(desc) > 90:
                        desc = desc[:87] + "..."
                    c2.write(desc)
                    pvp = row.get("PVP_Mercado")
                    c3.write(f"{pvp:.2f}" if pd.notna(pvp) else "-")
                    uds = row.get("Uds_por_Farmacia") or 0
                    c4.write(f"{uds:.0f}")

                    with c5:
                        if row.get("_decidido"):
                            st.success("Decidido")
                        else:
                            bc, bn = st.columns(2)
                            with bc:
                                if st.button(
                                    "Comprar", key=f"buy_{idx}",
                                    type="primary", use_container_width=True,
                                ):
                                    dec.log_surtido_decision(row.to_dict(), "Comprar", "")
                                    d.refresh_all()
                                    st.rerun()
                            with bn:
                                if st.button(
                                    "Descartar", key=f"no_{idx}",
                                    use_container_width=True,
                                ):
                                    dec.log_surtido_decision(row.to_dict(), "No me interesa", "")
                                    d.refresh_all()
                                    st.rerun()
                    st.divider()

elif st.session_state.fam_sel and not st.session_state.sub_sel:
    st.info("Selecciona una subfamilia para ver sus productos.")
elif not st.session_state.fam_sel:
    st.info("Selecciona una familia arriba para empezar.")

ui.sidebar_refresh_button()
