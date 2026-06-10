"""
Centro de decisiones de Pricing.

Permite filtrar, revisar y decidir sobre cada recomendación del motor.
Muestra impacto en margen y permite ajustar stock mínimo/máximo.
Las decisiones se escriben al Sheet (pestaña Decisiones_Pricing).
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

ui.setup_page("Pricing")
ui.page_header(
    "Centro de decisiones · Pricing",
    "Revisa, aprueba y registra las recomendaciones del motor de precios",
)

rec = d.get_recomendaciones()
if rec.empty:
    st.warning("No hay recomendaciones disponibles. Lanza el pipeline en el PC.")
    st.stop()

# --- Solo accionables ---
accionables = rec[rec["TipoCambio"].isin(["PVP", "PROMO"])].copy()
ya = dec.get_decided_ids("pricing")
accionables["_decidido"] = accionables["IdArticulo"].astype(str).isin(ya)

# ── Config margen mínimo ──────────────────────────────────────────────────────
st.sidebar.header("Configuración de pricing")
margen_minimo = st.sidebar.slider(
    "Margen mínimo (%)", min_value=0, max_value=50, value=20, step=1,
    help="El precio propuesto nunca podrá resultar en un margen inferior a este valor",
) / 100.0

# ── Filtros ───────────────────────────────────────────────────────────────────
ui.filter_card()
f1, f2, f3, f4 = st.columns([2, 2, 2, 2])

with f1:
    clasif_options = sorted([c for c in accionables["Clasificacion"].dropna().unique()
                              if c not in ("NO_TOCAR",)])
    clasif_sel = st.multiselect("Clasificación", clasif_options, default=clasif_options)
with f2:
    tipo_options = sorted(accionables["TipoCambio"].dropna().unique())
    tipo_sel = st.multiselect("Tipo cambio", tipo_options, default=tipo_options)
with f3:
    fam_options = sorted(accionables["Familia"].dropna().unique()) if "Familia" in accionables.columns else []
    fam_sel = st.multiselect("Familia", fam_options, default=[])
with f4:
    q = st.text_input("🔍 Buscar (CN o descripción)", "")

# ── Filtros adicionales (segunda fila) ──────────────────────────────────────────
f5, f6, f7 = st.columns([2, 2, 2])

with f5:
    solo_ventas = st.checkbox("🔥 Solo con ventas últimos 30d", value=False,
                              help="Muestra solo productos con ventas en los últimos 30 días")
with f6:
    incluir_decididos = st.checkbox("Incluir ya decididos", value=False)
with f7:
    st.write("")  # Espaciador

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df = accionables.copy()
if not incluir_decididos:
    df = df[~df["_decidido"]]
if clasif_sel:
    df = df[df["Clasificacion"].isin(clasif_sel)]
if tipo_sel:
    df = df[df["TipoCambio"].isin(tipo_sel)]
if fam_sel:
    df = df[df["Familia"].isin(fam_sel)]
if solo_ventas and "Ventas_90d" in df.columns:
    df = df[(df["Ventas_90d"] > 0) | (df["Ventas_90d"].isna() == False)]
if q:
    ql = q.lower()
    df = df[
        df["IdArticulo"].astype(str).str.lower().str.contains(ql, na=False)
        | df["Descripcion"].astype(str).str.lower().str.contains(ql, na=False)
    ]

if "Impacto_Margen_30d_est" in df.columns:
    df = df.assign(_abs=df["Impacto_Margen_30d_est"].abs()).sort_values("_abs", ascending=False).drop(columns="_abs")

# ── KPIs resumen ──────────────────────────────────────────────────────────────
st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
by_cls = df["Clasificacion"].value_counts().to_dict()
c1.metric("Total en vista", len(df))
c2.metric("📈 Subir margen", by_cls.get("MARGEN", 0))
c3.metric("🏷️ Gancho/Promo", by_cls.get("GANCHO", 0))
c4.metric("⚡ Dinamizar", by_cls.get("DINAMIZAR", 0))
c5.metric("🔻 Liquidar", by_cls.get("LIQUIDAR", 0))

st.divider()


# ── Helper: visualización de impacto de precio ────────────────────────────────
def _price_impact_html(pvp_act, pvp_prop, pvp_mkt, delta_pct, imp_margen, imp_fact, breakeven) -> str:
    try:
        pvp_act = float(pvp_act)
    except (TypeError, ValueError):
        return ""

    try:
        pvp_prop = float(pvp_prop) if pvp_prop is not None and not pd.isna(pvp_prop) else None
    except (TypeError, ValueError):
        pvp_prop = None
    try:
        pvp_mkt = float(pvp_mkt) if pvp_mkt is not None and not pd.isna(pvp_mkt) else None
    except (TypeError, ValueError):
        pvp_mkt = None

    if pvp_prop and pvp_prop > pvp_act:
        color, arrow = "#16a34a", "↑"
    elif pvp_prop and pvp_prop < pvp_act:
        color, arrow = "#dc2626", "↓"
    else:
        color, arrow = "#f59e0b", "→"

    try:
        pct_str = f"{float(delta_pct)*100:+.1f}%" if delta_pct is not None and not pd.isna(delta_pct) else ""
    except (TypeError, ValueError):
        pct_str = ""

    pvp_prop_str = f"{pvp_prop:.2f} €" if pvp_prop is not None else "-"
    pvp_mkt_str  = f"{pvp_mkt:.2f} €"  if pvp_mkt  is not None else "-"

    # Bloques opcionales construidos por separado (sin f-strings anidados)
    bloque_margen = ""
    try:
        m = float(imp_margen)
        sign = "+" if m >= 0 else ""
        m_color = "#16a34a" if m >= 0 else "#dc2626"
        bloque_margen = (
            '<div style="text-align:center;">'
            '<div style="font-size:0.68rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;">Imp. margen 30d</div>'
            '<div style="font-size:1rem;font-weight:700;color:' + m_color + ';">' + sign + f"{m:.0f} €" + '</div>'
            '</div>'
        )
    except (TypeError, ValueError):
        pass

    bloque_fact = ""
    try:
        f_ = float(imp_fact)
        sign = "+" if f_ >= 0 else ""
        bloque_fact = (
            '<div style="text-align:center;">'
            '<div style="font-size:0.68rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;">Imp. facturación 30d</div>'
            '<div style="font-size:1rem;font-weight:600;color:#475569;">' + sign + f"{f_:.0f} €" + '</div>'
            '</div>'
        )
    except (TypeError, ValueError):
        pass

    bloque_be = ""
    try:
        be = float(breakeven)
        bloque_be = (
            '<div style="text-align:center;">'
            '<div style="font-size:0.68rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;">BreakEven uplift</div>'
            '<div style="font-size:1rem;font-weight:600;color:#F59E0B;">' + f"{be:.1f}%" + '</div>'
            '</div>'
        )
    except (TypeError, ValueError):
        pass

    extras = bloque_margen + bloque_fact + bloque_be

    return (
        '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'
        'padding:0.85rem 1.1rem;margin:0.4rem 0;">'
        '<div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">'

        '<div style="text-align:center;min-width:80px;">'
        '<div style="font-size:0.68rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;">PVP actual</div>'
        '<div style="font-size:1.25rem;font-weight:700;color:#0F172A;">' + f"{pvp_act:.2f} €" + '</div>'
        '</div>'

        '<div style="font-size:1.5rem;font-weight:800;color:' + color + ';">' + arrow + '</div>'

        '<div style="text-align:center;min-width:80px;">'
        '<div style="font-size:0.68rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;">PVP propuesto</div>'
        '<div style="font-size:1.25rem;font-weight:700;color:' + color + ';">' + pvp_prop_str + '</div>'
        '<div style="font-size:0.78rem;font-weight:600;color:' + color + ';">' + pct_str + '</div>'
        '</div>'

        '<div style="width:1px;background:#E2E8F0;height:36px;"></div>'

        '<div style="text-align:center;min-width:80px;">'
        '<div style="font-size:0.68rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;">Precio mercado</div>'
        '<div style="font-size:1rem;font-weight:600;color:#475569;">' + pvp_mkt_str + '</div>'
        '</div>'

        + ('<div style="width:1px;background:#E2E8F0;height:36px;"></div>'
           '<div style="display:flex;gap:1.2rem;flex-wrap:wrap;">' + extras + '</div>'
           if extras else '') +

        '</div></div>'
    )


# ── Paginación ────────────────────────────────────────────────────────────────
PAGE_SIZE = 15
if "pricing_page" not in st.session_state:
    st.session_state.pricing_page = 0

total_pages = max(1, (len(df) + PAGE_SIZE - 1) // PAGE_SIZE)
st.session_state.pricing_page = min(st.session_state.pricing_page, total_pages - 1)

st.write(f"**{len(df)} recomendaciones** en la vista actual")

col_a, col_b, col_c = st.columns([1, 2, 1])
with col_a:
    if st.button("← Anterior", disabled=st.session_state.pricing_page == 0):
        st.session_state.pricing_page -= 1
        st.rerun()
with col_b:
    st.markdown(
        f"<div style='text-align:center'>Página <b>{st.session_state.pricing_page + 1}</b> "
        f"/ {total_pages}</div>",
        unsafe_allow_html=True,
    )
with col_c:
    if st.button("Siguiente →", disabled=st.session_state.pricing_page >= total_pages - 1):
        st.session_state.pricing_page += 1
        st.rerun()

start     = st.session_state.pricing_page * PAGE_SIZE
page_df   = df.iloc[start:start + PAGE_SIZE].copy()

# ── Tarjetas de recomendación ─────────────────────────────────────────────────
if page_df.empty:
    st.info("No hay recomendaciones con los filtros actuales.")
else:
    for idx, row in page_df.iterrows():
        with st.container(border=True):

            # ── Datos base ────────────────────────────────────────────────────
            pvp_act  = float(row.get("PVP") or 0)
            pvp_mkt  = float(row.get("PVP_Mercado") or 0) if pd.notna(row.get("PVP_Mercado")) else None
            coste    = float(row.get("PrecioCoste") or 0) if pd.notna(row.get("PrecioCoste")) else None
            margen_act_pct = float(row.get("MargenActual_Pct") or 0) if pd.notna(row.get("MargenActual_Pct")) else None
            pvp_min_margen = (coste / (1 - margen_minimo)) if coste and (1 - margen_minimo) > 0 else 0.0
            pvp_default = round(max(pvp_mkt or pvp_act, pvp_min_margen), 2)

            # ── CABECERA ──────────────────────────────────────────────────────
            h_l, h_r = st.columns([6, 1])
            with h_l:
                badge = ui.clasif_badge(row.get("Clasificacion", ""))
                st.markdown(
                    f"{badge} &nbsp; **{row.get('Descripcion', '')}**"
                    f"<span style='color:#94A3B8;font-size:0.82rem;'> · CN {row.get('IdArticulo', '')}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Familia: {row.get('Familia', '-')} · Subfamilia: {row.get('Subfamilia', '-')}")
            with h_r:
                if row.get("_decidido"):
                    st.success("✓ Decidido")

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # ── ZONA DE PRECIOS ───────────────────────────────────────────────
            # Columna A: PVP actual  |  B: precio propuesto + botones  |  C: métricas impacto
            za, zb, zc = st.columns([1.2, 1.5, 2.3])

            with za:
                st.markdown(
                    '<div style="background:#F8FAFC;border:1px solid #E9ECEF;border-radius:10px;'
                    'padding:0.8rem 1rem;text-align:center;min-height:120px;'
                    'display:flex;flex-direction:column;justify-content:center;">'
                    '<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:.6px;color:#94A3B8;margin-bottom:4px;">PVP actual</div>'
                    '<div style="font-size:1.5rem;font-weight:800;color:#0F172A;">'
                    + f"{pvp_act:.2f} €" +
                    '</div>'
                    + (f'<div style="font-size:0.72rem;color:#64748B;margin-top:2px;">Mercado: <b>{pvp_mkt:.2f} €</b></div>' if pvp_mkt else '') +
                    '</div>',
                    unsafe_allow_html=True,
                )

            with zb:
                # Inicializar session_state con precio por defecto
                key_pvp = f"pvp_{idx}"
                if key_pvp not in st.session_state:
                    st.session_state[key_pvp] = pvp_default

                pvp_nuevo = st.session_state[key_pvp]

                # Botones +/- verticales y precio en tarjeta
                col_btn, col_card = st.columns([0.35, 0.65], gap="small")

                with col_btn:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    if st.button("＋", key=f"btn_up_{idx}", use_container_width=True, help="Aumentar 0.05€"):
                        st.session_state[key_pvp] = min(pvp_nuevo + 0.05, 9999.0)
                        st.rerun()
                    if st.button("−", key=f"btn_down_{idx}", use_container_width=True, help="Disminuir 0.05€"):
                        st.session_state[key_pvp] = max(pvp_nuevo - 0.05, 0.01)
                        st.rerun()

                with col_card:
                    # Calcular delta precio
                    delta_p = ((pvp_nuevo - pvp_act) / pvp_act * 100) if pvp_act else 0
                    col_p   = "#16a34a" if delta_p > 0 else ("#dc2626" if delta_p < 0 else "#94A3B8")
                    arr     = "↑" if delta_p > 0 else ("↓" if delta_p < 0 else "→")

                    # Tarjeta con precio + delta
                    st.markdown(
                        '<div style="background:#F8FAFC;border:1px solid #E9ECEF;border-radius:10px;'
                        'padding:0.8rem 1rem;text-align:center;min-height:120px;'
                        'display:flex;flex-direction:column;justify-content:center;cursor:pointer;">'
                        '<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;'
                        'letter-spacing:.6px;color:#94A3B8;margin-bottom:4px;">Precio propuesto</div>'
                        '<div style="font-size:1.5rem;font-weight:800;color:#0F172A;margin-bottom:8px;">'
                        + f"{pvp_nuevo:.2f} €" +
                        '</div>'
                        '<div style="font-size:0.9rem;font-weight:700;">'
                        '<span style="font-size:1rem;color:' + col_p + ';">' + arr + '</span>'
                        '<span style="color:' + col_p + ';margin-left:4px;">' + f"{delta_p:+.1f}%" + '</span>'
                        '</div></div>',
                        unsafe_allow_html=True,
                    )

                # Input oculto para edición directa (no visible, solo para session_state)
                col_hidden, _ = st.columns([0.01, 2.99])
                with col_hidden:
                    pvp_input_hidden = st.number_input(
                        "edit",
                        min_value=0.01, max_value=9999.0,
                        value=pvp_nuevo,
                        step=0.05, format="%.2f",
                        key=f"pvp_edit_{idx}",
                        label_visibility="collapsed",
                    )
                    if pvp_input_hidden != pvp_nuevo:
                        st.session_state[key_pvp] = pvp_input_hidden
                        st.rerun()

            with zc:
                # Calcular margen nuevo
                # Detectar si MargenActual_Pct viene como decimal (<2) o porcentaje (>2)
                if margen_act_pct is not None and margen_act_pct < 2:
                    margen_act_pct_pct = margen_act_pct * 100  # viene como decimal (0.548 → 54.8)
                else:
                    margen_act_pct_pct = margen_act_pct  # ya es porcentaje
                margen_nuevo_pct = ((pvp_nuevo - coste) / pvp_nuevo * 100) if coste and pvp_nuevo > 0 else None
                delta_m = (margen_nuevo_pct - margen_act_pct_pct) if (margen_nuevo_pct is not None and margen_act_pct_pct is not None) else None
                alerta  = margen_nuevo_pct is not None and margen_nuevo_pct < margen_minimo

                m_act_s  = f"{margen_act_pct_pct:.1f}%" if margen_act_pct_pct is not None else "—"
                m_new_s  = f"{margen_nuevo_pct:.1f}%" if margen_nuevo_pct is not None else "—"
                dm_s     = f"{delta_m:+.1f}pp" if delta_m is not None else ""
                # Color: gris si sin datos, rojo si bajo mínimo, verde si sube, naranja si baja
                if coste is None:
                    col_m = "#94A3B8"
                elif alerta:
                    col_m = "#dc2626"
                elif (delta_m or 0) >= 0:
                    col_m = "#16a34a"
                else:
                    col_m = "#f59e0b"

                imp_m  = row.get("Impacto_Margen_30d_est")
                imp_f  = row.get("Impacto_Facturacion_30d_est")
                be     = row.get("BreakEven_Uplift_Pct")

                def _val(v, fmt=".0f", suffix="€", sign=True):
                    try:
                        f = float(v)
                        s = "+" if sign and f > 0 else ""
                        return f"{s}{f:{fmt}} {suffix}"
                    except Exception:
                        return "—"

                imp_m_s = _val(imp_m)
                imp_f_s = _val(imp_f)
                be_s    = _val(be, fmt=".1f", suffix="%", sign=False)
                col_im  = "#dc2626" if (imp_m is not None and not pd.isna(imp_m) and float(imp_m) < 0) else "#16a34a"
                col_be  = "#f59e0b"

                alerta_html = '<div style="color:#dc2626;font-size:0.7rem;font-weight:700;margin-top:4px;">⚠ Por debajo del margen mínimo</div>' if alerta else ""

                st.markdown(
                    '<div style="background:#F8FAFC;border:1px solid #E9ECEF;border-radius:10px;'
                    'padding:0.8rem 1rem;">'

                    # Fila 1: margen
                    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
                    '<div>'
                    '<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;">Margen actual</div>'
                    '<div style="font-size:1rem;font-weight:700;color:#475569;">' + m_act_s + '</div>'
                    '</div>'
                    '<div style="color:#CBD5E1;font-size:1rem;">→</div>'
                    '<div>'
                    '<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;">Margen nuevo</div>'
                    '<div style="font-size:1rem;font-weight:700;color:' + col_m + ';">' + m_new_s + ' <span style="font-size:0.75rem;">' + dm_s + '</span></div>'
                    '</div>'
                    '</div>'

                    # Fila 2: impactos
                    '<div style="display:flex;gap:16px;border-top:1px solid #E9ECEF;padding-top:8px;">'
                    '<div><div style="font-size:0.62rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.4px;">Imp. margen 30d</div>'
                    '<div style="font-size:0.9rem;font-weight:700;color:' + col_im + ';">' + imp_m_s + '</div></div>'
                    '<div><div style="font-size:0.62rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.4px;">Imp. facturación 30d</div>'
                    '<div style="font-size:0.9rem;font-weight:600;color:#475569;">' + imp_f_s + '</div></div>'
                    '<div><div style="font-size:0.62rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.4px;">BreakEven</div>'
                    '<div style="font-size:0.9rem;font-weight:600;color:' + col_be + ';">' + be_s + '</div></div>'
                    '</div>'

                    + alerta_html
                    + ('' if coste is not None else
                       '<div style="font-size:0.65rem;color:#94A3B8;margin-top:6px;">'
                       '&#9888; Sin dato de coste &mdash; ejecuta scripts 04 y 05 en el PC</div>')
                    + '</div>',
                    unsafe_allow_html=True,
                )

            # ── STRIP DE MÉTRICAS + JUSTIFICACIÓN ─────────────────────────────
            ventas = int(row.get("Ventas_30d") or 0)
            stock  = int(row.get("StockActual") or 0)
            dto    = row.get("Descuento_Pct")
            dto_s  = f"Dto: {float(dto):.1f}%" if (dto and pd.notna(dto)) else ""
            just   = str(row.get("Justificacion", "") or "")

            strip_parts = [
                f"Ventas 30d: <b>{ventas} uds</b>",
                f"Stock: <b>{stock}</b>",
            ]
            if dto_s:
                strip_parts.append(f"<b>{dto_s}</b>")
            strip = "  ·  ".join(strip_parts)
            st.markdown(
                f"<div style='font-size:0.82rem;color:#64748B;margin:6px 0 2px;'>{strip}</div>",
                unsafe_allow_html=True,
            )
            if just:
                st.caption(f"💡 {just}")

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # ── DECISIÓN: qué aprobar ─────────────────────────────────────────
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.5px;color:#94A3B8;margin:6px 0 4px;">¿Qué aplicar en Farmatic?</div>',
                unsafe_allow_html=True,
            )
            chk1, chk2, chk3 = st.columns([1.5, 2, 2])
            with chk1:
                ap_precio = st.checkbox(
                    f"Cambio precio → **{pvp_nuevo:.2f} €**",
                    value=True, key=f"chk_precio_{idx}",
                )
            with chk2:
                ap_stock  = st.checkbox(
                    "Actualizar niveles de stock", value=False, key=f"chk_stock_{idx}",
                )
            if ap_stock:
                with chk2:
                    st.caption("Stock mín / máx:")
                sk1, sk2 = st.columns(2)
                stock_min = sk1.number_input("Mínimo", min_value=0, max_value=9999,
                                              value=1, step=1, key=f"smin_{idx}")
                stock_max = sk2.number_input("Máximo", min_value=0, max_value=9999,
                                              value=1, step=1, key=f"smax_{idx}")
            else:
                stock_min = stock_max = None

            # ── BOTONES + NOTAS ───────────────────────────────────────────────
            b1, b2, b3, b4, bn = st.columns([1, 1, 1, 1, 2])
            notas = bn.text_input("", key=f"notas_{idx}", placeholder="Notas...",
                                   label_visibility="collapsed")

            row_data = {**row.to_dict(), "PVP_Propuesto": pvp_nuevo}

            with b1:
                if st.button("✅ Aprobar", key=f"ap_{idx}", type="primary", use_container_width=True):
                    dec.log_pricing_decision(row_data, "Aprobado", notas,
                                             aplicar_precio=ap_precio,
                                             stock_min=stock_min, stock_max=stock_max,
                                             aplicar_stock=ap_stock)
                    d.refresh_all(); st.rerun()
            with b2:
                if st.button("✔ Aplicado", key=f"apl_{idx}", use_container_width=True):
                    dec.log_pricing_decision(row_data, "Aplicado", notas,
                                             aplicar_precio=ap_precio,
                                             stock_min=stock_min, stock_max=stock_max,
                                             aplicar_stock=ap_stock)
                    d.refresh_all(); st.rerun()
            with b3:
                if st.button("⏸ Posponer", key=f"po_{idx}", use_container_width=True):
                    dec.log_pricing_decision(row_data, "Pospuesto", notas)
                    d.refresh_all(); st.rerun()
            with b4:
                if st.button("✗ Rechazar", key=f"re_{idx}", use_container_width=True):
                    dec.log_pricing_decision(row_data, "Rechazado", notas)
                    d.refresh_all(); st.rerun()

# ── HISTORIAL DE DECISIONES ───────────────────────────────────────────────────
st.divider()
st.subheader("📋 Historial de decisiones")

hist = dec.get_pricing_decisions()
if hist.empty:
    st.info("Aún no hay decisiones registradas.")
else:
    hist_sorted = hist.sort_values("Timestamp_dt", ascending=False).head(50)

    for _, h in hist_sorted.iterrows():
        decision    = str(h.get("Decision", ""))
        estado      = str(h.get("Estado", ""))
        cn          = str(h.get("IdArticulo", ""))
        desc        = str(h.get("Descripcion", ""))[:60]
        ts          = str(h.get("Timestamp", ""))[:16]
        pvp_a       = h.get("PVP_Actual", "—")
        pvp_p       = h.get("PVP_Propuesto", "—")
        ap_precio   = str(h.get("Aplicar_Precio", ""))
        ap_stock_h  = str(h.get("Aplicar_Stock", ""))
        smin        = h.get("StockMinimo_Nuevo", "")
        smax        = h.get("StockMaximo_Nuevo", "")

        col_dec = {"Aprobado": "#16a34a", "Aplicado": "#00897B",
                   "Rechazado": "#dc2626", "Pospuesto": "#f59e0b",
                   "Anulado": "#94A3B8"}.get(decision, "#475569")

        cambios = []
        if ap_precio == "Sí":
            cambios.append(f"Precio: {pvp_a} € → {pvp_p} €")
        if ap_stock_h == "Sí":
            cambios.append(f"Stock: mín {smin} / máx {smax}")
        cambios_str = "  ·  ".join(cambios) if cambios else "Sin cambios en Farmatic"

        h_l, h_r = st.columns([6, 1])
        with h_l:
            st.markdown(
                f'<div style="padding:0.5rem 0.75rem;background:#F8FAFC;'
                f'border-left:3px solid {col_dec};border-radius:6px;margin-bottom:4px;">'
                f'<span style="font-size:0.72rem;font-weight:700;color:{col_dec};">{decision.upper()}</span>'
                f'<span style="font-size:0.72rem;color:#94A3B8;margin-left:8px;">{ts}</span>'
                f'<span style="font-size:0.82rem;font-weight:600;color:#212529;margin-left:10px;">{desc}</span>'
                f'<span style="font-size:0.72rem;color:#94A3B8;"> · CN {cn}</span><br>'
                f'<span style="font-size:0.72rem;color:#64748B;">{cambios_str}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with h_r:
            if decision not in ("Anulado", "Rechazado"):
                if st.button("↩ Anular", key=f"anular_{cn}_{ts}",
                              use_container_width=True,
                              help="Marca esta decisión como anulada (vuelve a aparecer en la lista)"):
                    dec.log_pricing_decision(
                        {"IdArticulo": cn, "Descripcion": desc,
                         "PVP": pvp_a, "PVP_Propuesto": pvp_p},
                        "Anulado",
                        notas=f"Anulación de decisión {decision} del {ts}",
                    )
                    d.refresh_all(); st.rerun()

st.divider()

# ── Aplicar cambios en Farmatic ───────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.header("Aplicar cambios en Farmatic")

    # Detectar si está en Streamlit Cloud (no tiene acceso a Farmatic local)
    import os
    is_streamlit_cloud = os.getenv("STREAMLIT_SERVER_HEADLESS") == "true" or not os.path.exists(
        str(Path(__file__).parent.parent.parent / "scripts" / "07_aplicar_decisiones.py")
    )

    if is_streamlit_cloud:
        st.warning("⚠️ Este botón solo funciona en **local**")
        st.caption(
            "Streamlit Cloud no tiene acceso a tu Farmatic en Windows. "
            "Para aplicar cambios, usa la app en http://localhost:8501"
        )
    else:
        if st.button("📤 Aplicar decisiones aprobadas", use_container_width=True, type="primary"):
            st.info("Ejecutando script de aplicación en Farmatic...")
            try:
                import subprocess

                script_path = Path(__file__).parent.parent.parent / "scripts" / "07_aplicar_decisiones.py"
                result = subprocess.run(
                    ["python", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    st.success("✅ Cambios aplicados exitosamente en Farmatic")
                    st.write(result.stdout)
                    d.refresh_all()
                    st.rerun()
                else:
                    st.error("❌ Error al aplicar cambios:")
                    st.write(result.stderr)
            except Exception as e:
                st.error(f"❌ Error ejecutando script: {str(e)}")

        st.caption("Aplica los cambios de PVP y Stock aprobados en la base de datos SQL de Farmatic")

st.divider()

ui.sidebar_refresh_button()
