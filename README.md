# Farmapricing - App de Decisiones

App web (Streamlit) para gestionar las recomendaciones de pricing y los huecos
de surtido que genera el pipeline. Lee y escribe contra el mismo Google Sheet
que alimenta el motor — no requiere acceso a SQL ni a Farmatic.

## Pantallas

1. **Dashboard ejecutivo** — KPIs globales, distribución por clasificación, top
   oportunidades, cobertura por familia, decisiones recientes.
2. **Pricing** — lista filtrable de recomendaciones; aprueba / rechaza / pospone
   / marca como aplicado cada una.
3. **Surtido** — huecos del catálogo vs mercado, en tres vistas (familia,
   subfamilia, productos individuales). Marca productos como comprar o
   descartar.
4. **Producto** — drill-down por artículo individual con datos de la farmacia,
   comparación con mercado, recomendación y histórico de decisiones.

## Estructura

```
app/
├── streamlit_app.py            # entry point (Inicio)
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Pricing.py
│   ├── 3_Surtido.py
│   └── 4_Producto.py
├── lib/
│   ├── config.py               # lee de st.secrets o env vars
│   ├── sheets_client.py        # cliente gspread con caché
│   ├── data.py                 # lectura de pestañas (cacheada 60s)
│   ├── decisions.py            # log de decisiones a Sheets
│   └── ui.py                   # componentes UI reutilizables
├── .streamlit/
│   ├── config.toml             # tema/configuración Streamlit
│   └── secrets.toml.example    # plantilla de secrets
├── requirements.txt
└── README.md
```

## Desarrollo local

```bash
cd app
python -m venv .venv
.\.venv\Scripts\activate    # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Opción A: usa el mismo google_credentials.json que el pipeline (en la raíz del proyecto)
# Opción B: copia .streamlit/secrets.toml.example -> .streamlit/secrets.toml y rellénalo

streamlit run streamlit_app.py
```

Abre http://localhost:8501. Las decisiones se escriben directamente al Google
Sheet en las pestañas `Decisiones_Pricing` y `Decisiones_Surtido` (la app las
crea automáticamente la primera vez que tomes una decisión).

## Despliegue en Streamlit Community Cloud (gratis)

### 1. Sube el código a GitHub

Crea un repositorio privado (recomendado) con el contenido de la carpeta `app/`
y los ficheros del pipeline. **No subas** `google_credentials.json`, `.env`,
ni `.streamlit/secrets.toml`. El `.gitignore` ya los excluye.

```bash
cd "Farmapricing Agent"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/farmapricing.git
git push -u origin main
```

### 2. Da permiso de edición al service account sobre el sheet

Abre el Google Sheet, botón **Compartir**, añade
`agente-farmacia-bot@agente-farmacia-496411.iam.gserviceaccount.com` como
**Editor** (no como Lector — la app necesita escribir las pestañas de
decisiones).

### 3. Crea la app en Streamlit Cloud

1. Entra en https://share.streamlit.io con tu cuenta de GitHub.
2. **New app** → selecciona tu repo y la rama `main`.
3. **Main file path**: `app/streamlit_app.py`.
4. **Python version**: 3.11.
5. **Advanced settings** → **Secrets**: pega el contenido de
   `.streamlit/secrets.toml.example` ya relleno con los datos de tu
   `google_credentials.json` (campos `private_key`, `private_key_id`, etc.).
6. **Deploy**.

En 1-2 minutos tendrás la app desplegada en una URL del tipo
`https://farmapricing-XXXXX.streamlit.app`. Es accesible desde móvil, tablet,
o cualquier navegador.

### 4. Restringe el acceso (importante)

En la configuración de la app, sección **Sharing**, elige **Only specific
people** y añade tu correo. Cualquier otro usuario que intente entrar verá
una pantalla de login con Google.

## Alternativas de hosting

- **Render** (https://render.com) — Free tier, requiere un `render.yaml`.
- **Railway** (https://railway.app) — Tier de pago bajo.
- **Hugging Face Spaces** — Gratis, soporta Streamlit nativo.
- **Fly.io** — Para más control, con `fly.toml`.

En todos ellos el patrón es el mismo: contenedor Python con
`pip install -r requirements.txt` y `streamlit run streamlit_app.py --server.port $PORT`.

## Flujo de uso diario

1. **En el PC de la farmacia**: cada mañana (o cuando quieras refrescar) lanza
   `python run_all.py`. El pipeline extrae Farmatic, cruza con mercado y
   publica recomendaciones + huecos en el sheet.
2. **En cualquier dispositivo**: abre la URL de la app, revisa el Dashboard,
   ve al Centro de decisiones, aprueba/rechaza/pospone, busca productos
   específicos en la ficha. Todas las acciones quedan registradas.
3. **Cuando aplicas un cambio en Farmatic / etiquetas**: vuelves a la app y
   marcas esa decisión como "Aplicado". Esto cierra el ciclo y deja trazabilidad.

## Notas técnicas

- La app cachea las lecturas de Sheets 60 segundos para no saturar la API. El
  botón "Recargar datos del Sheet" del sidebar fuerza una lectura fresca.
- Las pestañas `Decisiones_*` se crean la primera vez que registras una decisión.
- Si la app no encuentra una pestaña con el nombre exacto, busca por
  case-insensitive y substring (tolerante a renombres).
