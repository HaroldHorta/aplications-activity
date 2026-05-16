import os
import json
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table
import dash_bootstrap_components as dbc

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Constants ────────────────────────────────────────────────────────────────
MONTH_NAMES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}
SEXO_MAP = {1: 'Hombre', 2: 'Mujer', 3: 'Indeterminado'}

# GRUPO_EDAD1 → category (ranges from activity table)
AGE_CATEGORIES = [
    (range(0, 5),   'Mortalidad neonatal (<1 mes)'),
    (range(5, 7),   'Mortalidad infantil (1-11 meses)'),
    (range(7, 9),   'Primera infancia (1-4 años)'),
    (range(9, 11),  'Niñez (5-14 años)'),
    (range(11, 12), 'Adolescencia (15-19 años)'),
    (range(12, 14), 'Juventud (20-29 años)'),
    (range(14, 17), 'Adultez temprana (30-44 años)'),
    (range(17, 20), 'Adultez intermedia (45-59 años)'),
    (range(20, 25), 'Vejez (60-84 años)'),
    (range(25, 29), 'Longevidad (85-100+ años)'),
    ([29],          'Edad desconocida'),
]
AGE_ORDER = [cat for _, cat in AGE_CATEGORIES]

GEOJSON_LOCAL = os.path.join(BASE, 'colombia_departments.geojson')
GEOJSON_URL = (
    'https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc'
    '/raw/be6a6e239cd5b5b803c6e7c2ec405b793a9064dd/Colombia.geo.json'
)

CARD_STYLE = {
    'borderRadius': '10px',
    'boxShadow': '0 2px 10px rgba(0,0,0,0.08)',
    'marginBottom': '0',
}

# ── Load & preprocess data ────────────────────────────────────────────────────
print("Loading data…")

df = pd.read_excel(os.path.join(BASE, 'Anexo1.NoFetal2019_CE_15-03-23.xlsx'))
df.columns = [
    'COD_DANE', 'COD_DEPARTAMENTO', 'COD_MUNICIPIO', 'AREA_DEFUNCION',
    'SITIO_DEFUNCION', 'ANO', 'MES', 'HORA', 'MINUTOS', 'SEXO',
    'ESTADO_CIVIL', 'GRUPO_EDAD1', 'NIVEL_EDUCATIVO', 'MANERA_MUERTE',
    'COD_MUERTE', 'IDPROFESIONAL',
]

codigos_raw = pd.read_excel(
    os.path.join(BASE, 'Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx'), header=8
)
codigos_raw.columns = ['CAPITULO', 'NOMBRE_CAP', 'COD_3', 'DESC_3', 'COD_4', 'DESC_4']

divipola = pd.read_excel(os.path.join(BASE, 'Divipola_CE_.xlsx'))

# Merge names
dep_map = divipola[['COD_DEPARTAMENTO', 'DEPARTAMENTO']].drop_duplicates()
mun_map = divipola[['COD_MUNICIPIO', 'COD_DEPARTAMENTO', 'MUNICIPIO']].drop_duplicates()
df = df.merge(dep_map, on='COD_DEPARTAMENTO', how='left')
df = df.merge(mun_map, on=['COD_MUNICIPIO', 'COD_DEPARTAMENTO'], how='left')

df['SEXO_NOMBRE'] = df['SEXO'].map(SEXO_MAP).fillna('Indeterminado')
df['MES_NOMBRE'] = df['MES'].map(MONTH_NAMES)


def get_age_category(code):
    try:
        code = int(code)
    except (ValueError, TypeError):
        return 'Edad desconocida'
    for rng, cat in AGE_CATEGORIES:
        if code in rng:
            return cat
    return 'Edad desconocida'


df['CATEGORIA_EDAD'] = df['GRUPO_EDAD1'].apply(get_age_category)

# Code → description lookup (4-char takes priority over 3-char)
cod4 = (
    codigos_raw[['COD_4', 'DESC_4']].dropna()
    .drop_duplicates('COD_4')
    .set_index('COD_4')['DESC_4']
)
cod3 = (
    codigos_raw[['COD_3', 'DESC_3']].dropna()
    .drop_duplicates('COD_3')
    .set_index('COD_3')['DESC_3']
)


def get_cause_name(code):
    code = str(code)
    if code in cod4.index:
        return cod4[code]
    if code[:3] in cod3.index:
        return cod3[code[:3]]
    return 'Sin descripción'


# ── GeoJSON ───────────────────────────────────────────────────────────────────
colombia_geo = None
if os.path.exists(GEOJSON_LOCAL):
    with open(GEOJSON_LOCAL, 'r', encoding='utf-8') as f:
        colombia_geo = json.load(f)
    print("GeoJSON loaded from local file.")
else:
    try:
        r = requests.get(GEOJSON_URL, timeout=20)
        if r.status_code == 200:
            colombia_geo = r.json()
            print("GeoJSON fetched from URL.")
    except Exception as exc:
        print(f"GeoJSON unavailable: {exc}")

# ── Figure 1 — MAP: deaths by department ──────────────────────────────────────
dep_deaths = (
    df.groupby(['COD_DEPARTAMENTO', 'DEPARTAMENTO'])
    .size()
    .reset_index(name='MUERTES')
)
dep_deaths['DPTO'] = dep_deaths['COD_DEPARTAMENTO'].apply(
    lambda x: str(int(x)).zfill(2)
)

if colombia_geo:
    fig_map = px.choropleth(
        dep_deaths,
        geojson=colombia_geo,
        locations='DPTO',
        featureidkey='properties.DPTO',
        color='MUERTES',
        hover_name='DEPARTAMENTO',
        hover_data={'DPTO': False, 'MUERTES': ':,'},
        color_continuous_scale='Reds',
        title='<b>Distribución Total de Muertes por Departamento — Colombia 2019</b>',
    )
    fig_map.update_geos(fitbounds='locations', visible=False)
    fig_map.update_layout(margin={'r': 0, 't': 60, 'l': 0, 'b': 0}, height=520)
else:
    dep_sorted = dep_deaths.sort_values('MUERTES')
    fig_map = px.bar(
        dep_sorted, x='MUERTES', y='DEPARTAMENTO', orientation='h',
        title='<b>Distribución Total de Muertes por Departamento — Colombia 2019</b>',
        color='MUERTES', color_continuous_scale='Reds',
        labels={'MUERTES': 'Total Muertes', 'DEPARTAMENTO': 'Departamento'},
    )
    fig_map.update_layout(height=700)

# ── Figure 2 — LINE: deaths by month ──────────────────────────────────────────
monthly = df.groupby('MES').size().reset_index(name='MUERTES')
monthly['MES_NOMBRE'] = monthly['MES'].map(MONTH_NAMES)

fig_line = px.line(
    monthly, x='MES_NOMBRE', y='MUERTES',
    markers=True,
    title='<b>Total de Muertes por Mes — Colombia 2019</b>',
    labels={'MES_NOMBRE': 'Mes', 'MUERTES': 'Total de Muertes'},
    color_discrete_sequence=['#e74c3c'],
)
fig_line.update_traces(line_width=3, marker_size=9)
fig_line.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': list(MONTH_NAMES.values())})

# ── Figure 3 — BAR: top 5 violent cities (X95 homicides) ──────────────────────
homicidios = df[df['COD_MUERTE'].astype(str).str.startswith('X95')]
violentas = (
    homicidios.groupby('MUNICIPIO').size()
    .reset_index(name='HOMICIDIOS')
    .nlargest(5, 'HOMICIDIOS')
)

fig_bar_violentas = px.bar(
    violentas, x='MUNICIPIO', y='HOMICIDIOS',
    title='<b>Top 5 Ciudades más Violentas — Homicidios por Arma de Fuego (X95) 2019</b>',
    labels={'MUNICIPIO': 'Ciudad', 'HOMICIDIOS': 'Número de Homicidios'},
    color='HOMICIDIOS',
    color_continuous_scale='OrRd',
    text='HOMICIDIOS',
)
fig_bar_violentas.update_traces(textposition='outside')
fig_bar_violentas.update_layout(showlegend=False, coloraxis_showscale=False)

# ── Figure 4 — PIE: 10 cities with lowest mortality ───────────────────────────
city_deaths = df.groupby('MUNICIPIO').size().reset_index(name='MUERTES')
city_deaths = city_deaths[city_deaths['MUERTES'] > 0].nsmallest(10, 'MUERTES')

fig_pie = px.pie(
    city_deaths, names='MUNICIPIO', values='MUERTES',
    title='<b>10 Ciudades con Menor Índice de Mortalidad — Colombia 2019</b>',
    color_discrete_sequence=px.colors.qualitative.Pastel,
    hole=0.35,
)
fig_pie.update_traces(textposition='inside', textinfo='percent+label')

# ── Figure 5 — TABLE: top 10 causes of death ──────────────────────────────────
cause_counts = (
    df.groupby('COD_MUERTE').size()
    .reset_index(name='TOTAL')
    .nlargest(10, 'TOTAL')
)
cause_counts['CAUSA'] = cause_counts['COD_MUERTE'].apply(get_cause_name)
table_data = cause_counts[['COD_MUERTE', 'CAUSA', 'TOTAL']].copy()
table_data.columns = ['Código', 'Causa de Muerte', 'Total de Casos']
table_data['Total de Casos'] = table_data['Total de Casos'].apply(lambda x: f'{x:,}')

# ── Figure 6 — STACKED BAR: deaths by sex per department ──────────────────────
sex_dep = (
    df.groupby(['DEPARTAMENTO', 'SEXO_NOMBRE'])
    .size()
    .reset_index(name='MUERTES')
)

fig_stacked = px.bar(
    sex_dep, x='DEPARTAMENTO', y='MUERTES', color='SEXO_NOMBRE',
    barmode='stack',
    title='<b>Total de Muertes por Sexo en cada Departamento — Colombia 2019</b>',
    labels={
        'DEPARTAMENTO': 'Departamento',
        'MUERTES': 'Total Muertes',
        'SEXO_NOMBRE': 'Sexo',
    },
    color_discrete_map={
        'Hombre': '#3498db',
        'Mujer': '#e91e63',
        'Indeterminado': '#95a5a6',
    },
)
fig_stacked.update_layout(xaxis_tickangle=-45, height=560, legend_title_text='Sexo')

# ── Figure 7 — HISTOGRAM: deaths by age group ──────────────────────────────────
age_counts = df.groupby('CATEGORIA_EDAD').size().reset_index(name='MUERTES')
age_counts['CATEGORIA_EDAD'] = pd.Categorical(
    age_counts['CATEGORIA_EDAD'], categories=AGE_ORDER, ordered=True
)
age_counts = age_counts.sort_values('CATEGORIA_EDAD')

fig_hist = px.bar(
    age_counts, x='CATEGORIA_EDAD', y='MUERTES',
    title='<b>Distribución de Muertes por Grupo de Edad (GRUPO_EDAD1) — Colombia 2019</b>',
    labels={'CATEGORIA_EDAD': 'Grupo de Edad', 'MUERTES': 'Total Muertes'},
    color='MUERTES',
    color_continuous_scale='Blues',
    text='MUERTES',
)
fig_hist.update_traces(textposition='outside', texttemplate='%{text:,}')
fig_hist.update_layout(xaxis_tickangle=-30, height=520, coloraxis_showscale=False)

# ── App layout ────────────────────────────────────────────────────────────────
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # exposed for Gunicorn

app.layout = dbc.Container(
    [
        # Header
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H1(
                            'Análisis de Mortalidad en Colombia 2019',
                            className='text-white text-center mb-1 fw-bold',
                        ),
                        html.P(
                            'Dashboard interactivo — Fuente: DANE · Estadísticas Vitales EEVV 2019',
                            className='text-center mb-0',
                            style={'color': 'rgba(255,255,255,0.75)', 'fontSize': '0.95rem'},
                        ),
                    ],
                    style={
                        'background': 'linear-gradient(135deg, #2c3e50 0%, #3498db 100%)',
                        'padding': '2rem 1rem',
                        'borderRadius': '0 0 14px 14px',
                        'marginBottom': '1.5rem',
                    },
                )
            )
        ),

        # ① Mapa
        dbc.Row(
            dbc.Col(dbc.Card(dcc.Graph(figure=fig_map), style=CARD_STYLE)),
            className='mb-4',
        ),

        # ② Líneas + ③ Barras violentas
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(dcc.Graph(figure=fig_line), style=CARD_STYLE),
                    width=12, lg=6,
                ),
                dbc.Col(
                    dbc.Card(dcc.Graph(figure=fig_bar_violentas), style=CARD_STYLE),
                    width=12, lg=6,
                ),
            ],
            className='mb-4',
        ),

        # ④ Pie + ⑤ Tabla
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(dcc.Graph(figure=fig_pie), style=CARD_STYLE),
                    width=12, lg=5,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H5(
                                    'Top 10 Causas de Muerte — Colombia 2019',
                                    className='mb-0 text-primary fw-semibold',
                                )
                            ),
                            dbc.CardBody(
                                dash_table.DataTable(
                                    data=table_data.to_dict('records'),
                                    columns=[
                                        {'name': c, 'id': c} for c in table_data.columns
                                    ],
                                    style_table={'overflowX': 'auto'},
                                    style_cell={
                                        'textAlign': 'left',
                                        'padding': '8px 14px',
                                        'fontFamily': 'inherit',
                                        'fontSize': '13px',
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                    },
                                    style_header={
                                        'backgroundColor': '#2c3e50',
                                        'color': 'white',
                                        'fontWeight': 'bold',
                                        'textAlign': 'left',
                                    },
                                    style_data_conditional=[
                                        {
                                            'if': {'row_index': 'odd'},
                                            'backgroundColor': '#f8f9fa',
                                        },
                                        {
                                            'if': {'column_id': 'Total de Casos'},
                                            'textAlign': 'right',
                                            'fontWeight': 'bold',
                                            'color': '#e74c3c',
                                        },
                                    ],
                                    style_data={'border': '1px solid #dee2e6'},
                                    page_size=10,
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12, lg=7,
                ),
            ],
            className='mb-4',
        ),

        # ⑥ Barras apiladas por sexo/departamento
        dbc.Row(
            dbc.Col(dbc.Card(dcc.Graph(figure=fig_stacked), style=CARD_STYLE)),
            className='mb-4',
        ),

        # ⑦ Histograma por grupo de edad
        dbc.Row(
            dbc.Col(dbc.Card(dcc.Graph(figure=fig_hist), style=CARD_STYLE)),
            className='mb-4',
        ),

        # Footer
        dbc.Row(
            dbc.Col(
                html.P(
                    'Fuente: DANE — Estadísticas Vitales 2019 · '
                    'Desarrollado con Python, Dash y Plotly',
                    className='text-center text-muted small my-2',
                )
            )
        ),
    ],
    fluid=True,
    style={'backgroundColor': '#f0f2f5', 'minHeight': '100vh'},
)

if __name__ == '__main__':
    app.run(
        debug=False,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8050)),
    )
