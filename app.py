import os
import json
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table
import dash_bootstrap_components as dbc

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Paleta de colores ─────────────────────────────────────────────────────────
C_PURPLE   = '#7c3aed'
C_BLUE     = '#0ea5e9'
C_PINK     = '#ec4899'
C_AMBER    = '#f59e0b'
C_RED      = '#ef4444'
C_EMERALD  = '#10b981'
C_SLATE    = '#64748b'

PIE_COLORS = [
    '#7c3aed','#0ea5e9','#10b981','#f59e0b','#ef4444',
    '#8b5cf6','#06b6d4','#84cc16','#f97316','#ec4899',
]

CHART_FONT = dict(family='system-ui, -apple-system, Segoe UI, sans-serif', color='#1e293b')

CHART_LAYOUT = dict(
    template='plotly_white',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=CHART_FONT,
    title_font=dict(size=14, color='#1e293b', family='system-ui, sans-serif'),
    hoverlabel=dict(bgcolor='white', font_size=13, font_family='system-ui, sans-serif'),
)
DEFAULT_MARGIN = dict(t=55, b=40, l=50, r=20)

CARD_STYLE = {
    'borderRadius': '14px',
    'boxShadow': '0 4px 24px rgba(124,58,237,0.08)',
    'border': 'none',
    'overflow': 'hidden',
}

# ── Constantes de dominio ─────────────────────────────────────────────────────
MONTH_NAMES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}
SEXO_MAP = {1: 'Hombre', 2: 'Mujer', 3: 'Indeterminado'}

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

# ── Carga y preprocesamiento ──────────────────────────────────────────────────
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

dep_map = divipola[['COD_DEPARTAMENTO', 'DEPARTAMENTO']].drop_duplicates()
mun_map = divipola[['COD_MUNICIPIO', 'COD_DEPARTAMENTO', 'MUNICIPIO']].drop_duplicates()
df = df.merge(dep_map, on='COD_DEPARTAMENTO', how='left')
df = df.merge(mun_map, on=['COD_MUNICIPIO', 'COD_DEPARTAMENTO'], how='left')

df['SEXO_NOMBRE'] = df['SEXO'].map(SEXO_MAP).fillna('Indeterminado')
df['MES_NOMBRE']  = df['MES'].map(MONTH_NAMES)


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

cod4 = (
    codigos_raw[['COD_4', 'DESC_4']].dropna()
    .drop_duplicates('COD_4').set_index('COD_4')['DESC_4']
)
cod3 = (
    codigos_raw[['COD_3', 'DESC_3']].dropna()
    .drop_duplicates('COD_3').set_index('COD_3')['DESC_3']
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

# ── ① Mapa: muertes por departamento ─────────────────────────────────────────
dep_deaths = (
    df.groupby(['COD_DEPARTAMENTO', 'DEPARTAMENTO'])
    .size().reset_index(name='MUERTES')
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
        color_continuous_scale=[
            [0.0, '#ede9fe'], [0.25, '#c4b5fd'],
            [0.5, '#8b5cf6'], [0.75, '#6d28d9'], [1.0, '#3b0764'],
        ],
        title='<b>Distribución Total de Muertes por Departamento</b>',
    )
    fig_map.update_geos(fitbounds='locations', visible=False)
    fig_map.update_layout(
        **CHART_LAYOUT,
        height=530,
        margin=dict(r=0, t=55, l=0, b=10),
        coloraxis_colorbar=dict(
            title=dict(text='Muertes', font=dict(color='#1e293b')),
            tickfont=dict(color='#1e293b'),
        ),
    )
else:
    dep_sorted = dep_deaths.sort_values('MUERTES')
    fig_map = px.bar(
        dep_sorted, x='MUERTES', y='DEPARTAMENTO', orientation='h',
        title='<b>Distribución Total de Muertes por Departamento</b>',
        color='MUERTES',
        color_continuous_scale=[[0,'#ede9fe'],[1,'#6d28d9']],
        labels={'MUERTES': 'Total Muertes', 'DEPARTAMENTO': 'Departamento'},
    )
    fig_map.update_layout(**CHART_LAYOUT, height=700, margin=DEFAULT_MARGIN)

# ── ② Líneas: muertes por mes ────────────────────────────────────────────────
monthly = df.groupby('MES').size().reset_index(name='MUERTES')
monthly['MES_NOMBRE'] = monthly['MES'].map(MONTH_NAMES)

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=monthly['MES_NOMBRE'],
    y=monthly['MUERTES'],
    mode='lines+markers',
    name='Muertes',
    line=dict(color=C_PURPLE, width=3, shape='spline'),
    marker=dict(size=9, color='white', line=dict(color=C_PURPLE, width=3)),
    fill='tozeroy',
    fillcolor='rgba(124,58,237,0.10)',
    hovertemplate='<b>%{x}</b><br>Muertes: %{y:,}<extra></extra>',
))
fig_line.update_layout(
    **CHART_LAYOUT,
    margin=DEFAULT_MARGIN,
    title='<b>Total de Muertes por Mes</b>',
    xaxis=dict(
        title='Mes', categoryorder='array',
        categoryarray=list(MONTH_NAMES.values()),
        showgrid=False,
    ),
    yaxis=dict(title='Total de Muertes', gridcolor='#f1f5f9'),
    showlegend=False,
)

# ── ③ Barras: top 5 ciudades violentas ───────────────────────────────────────
homicidios = df[df['COD_MUERTE'].astype(str).str.startswith('X95')]
violentas = (
    homicidios.groupby('MUNICIPIO').size()
    .reset_index(name='HOMICIDIOS').nlargest(5, 'HOMICIDIOS')
)

fig_bar_violentas = px.bar(
    violentas, x='MUNICIPIO', y='HOMICIDIOS',
    title='<b>Top 5 Ciudades más Violentas — Homicidios por Arma de Fuego (X95)</b>',
    labels={'MUNICIPIO': 'Ciudad', 'HOMICIDIOS': 'Homicidios'},
    color='HOMICIDIOS',
    color_continuous_scale=[[0, '#fde68a'], [0.5, '#f97316'], [1, '#7f1d1d']],
    text='HOMICIDIOS',
)
fig_bar_violentas.update_traces(
    textposition='outside',
    texttemplate='%{text:,}',
    marker_line_width=0,
    textfont=dict(color='#1e293b', size=12),
)
fig_bar_violentas.update_layout(
    **CHART_LAYOUT,
    margin=DEFAULT_MARGIN,
    yaxis=dict(title='Homicidios', gridcolor='#f1f5f9'),
    xaxis=dict(title='Ciudad'),
    coloraxis_showscale=False,
)

# ── ④ Pie: 10 ciudades menor mortalidad ──────────────────────────────────────
city_deaths = df.groupby('MUNICIPIO').size().reset_index(name='MUERTES')
city_deaths = city_deaths[city_deaths['MUERTES'] > 0].nsmallest(10, 'MUERTES')

fig_pie = px.pie(
    city_deaths, names='MUNICIPIO', values='MUERTES',
    title='<b>10 Ciudades con Menor Índice de Mortalidad</b>',
    color_discrete_sequence=PIE_COLORS,
    hole=0.42,
)
fig_pie.update_traces(
    textposition='inside',
    textinfo='percent+label',
    hovertemplate='<b>%{label}</b><br>Muertes: %{value}<br>%{percent}<extra></extra>',
    marker=dict(line=dict(color='white', width=2)),
)
fig_pie.update_layout(**CHART_LAYOUT, margin=DEFAULT_MARGIN)

# ── ⑤ Tabla: top 10 causas de muerte ─────────────────────────────────────────
cause_counts = (
    df.groupby('COD_MUERTE').size()
    .reset_index(name='TOTAL').nlargest(10, 'TOTAL')
)
cause_counts['CAUSA'] = cause_counts['COD_MUERTE'].apply(get_cause_name)
table_data = cause_counts[['COD_MUERTE', 'CAUSA', 'TOTAL']].copy()
table_data.columns = ['Código', 'Causa de Muerte', 'Total de Casos']
table_data['Total de Casos'] = table_data['Total de Casos'].apply(lambda x: f'{x:,}')

# ── ⑥ Barras apiladas: muertes por sexo y departamento ───────────────────────
sex_dep = df.groupby(['DEPARTAMENTO', 'SEXO_NOMBRE']).size().reset_index(name='MUERTES')

fig_stacked = px.bar(
    sex_dep, x='DEPARTAMENTO', y='MUERTES', color='SEXO_NOMBRE',
    barmode='stack',
    title='<b>Muertes por Sexo en cada Departamento</b>',
    labels={
        'DEPARTAMENTO': 'Departamento',
        'MUERTES': 'Total Muertes',
        'SEXO_NOMBRE': 'Sexo',
    },
    color_discrete_map={
        'Hombre': '#3b82f6',
        'Mujer': '#ec4899',
        'Indeterminado': '#94a3b8',
    },
)
fig_stacked.update_layout(
    **CHART_LAYOUT,
    margin=dict(t=55, b=100, l=50, r=20),
    xaxis=dict(tickangle=-45, title='Departamento'),
    yaxis=dict(title='Total Muertes', gridcolor='#f1f5f9'),
    legend=dict(
        title='Sexo', orientation='h',
        yanchor='bottom', y=1.02, xanchor='right', x=1,
    ),
    height=560,
    bargap=0.15,
)
fig_stacked.update_traces(marker_line_width=0)

# ── ⑦ Histograma: muertes por grupo de edad ──────────────────────────────────
age_counts = df.groupby('CATEGORIA_EDAD').size().reset_index(name='MUERTES')
age_counts['CATEGORIA_EDAD'] = pd.Categorical(
    age_counts['CATEGORIA_EDAD'], categories=AGE_ORDER, ordered=True
)
age_counts = age_counts.sort_values('CATEGORIA_EDAD')

fig_hist = px.bar(
    age_counts, x='CATEGORIA_EDAD', y='MUERTES',
    title='<b>Distribución de Muertes por Grupo de Edad (GRUPO_EDAD1)</b>',
    labels={'CATEGORIA_EDAD': 'Grupo de Edad', 'MUERTES': 'Total Muertes'},
    color='MUERTES',
    color_continuous_scale=[
        [0.0, '#ddd6fe'], [0.4, '#8b5cf6'],
        [0.7, '#6d28d9'], [1.0, '#2e1065'],
    ],
    text='MUERTES',
)
fig_hist.update_traces(
    textposition='outside',
    texttemplate='%{text:,}',
    marker_line_width=0,
)
fig_hist.update_layout(
    **CHART_LAYOUT,
    margin=dict(t=55, b=100, l=50, r=20),
    xaxis=dict(tickangle=-30, title='Grupo de Edad'),
    yaxis=dict(title='Total Muertes', gridcolor='#f1f5f9'),
    coloraxis_showscale=False,
    height=530,
)

# ── Layout ────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
    ],
)
server = app.server


def section_label(icon, text):
    return html.Div(
        [html.Span(icon, style={'marginRight': '6px'}), text],
        style={
            'display': 'inline-flex',
            'alignItems': 'center',
            'background': 'linear-gradient(135deg, #7c3aed, #0ea5e9)',
            'color': 'white',
            'fontSize': '0.78rem',
            'fontWeight': '600',
            'letterSpacing': '0.05em',
            'textTransform': 'uppercase',
            'padding': '4px 12px',
            'borderRadius': '20px',
            'marginBottom': '10px',
        },
    )


app.layout = html.Div(
    style={
        'background': 'linear-gradient(160deg, #f5f3ff 0%, #eff6ff 50%, #f0fdf4 100%)',
        'minHeight': '100vh',
        'fontFamily': "'Inter', system-ui, sans-serif",
    },
    children=[
        # ── Header ──────────────────────────────────────────────────────────
        html.Div(
            style={
                'background': 'linear-gradient(135deg, #1e1b4b 0%, #5b21b6 55%, #0369a1 100%)',
                'padding': '2.5rem 2rem 2rem',
                'borderRadius': '0 0 24px 24px',
                'marginBottom': '2rem',
                'boxShadow': '0 8px 32px rgba(91,33,182,0.3)',
            },
            children=[
                html.Div(
                    '🇨🇴  COLOMBIA · 2019',
                    style={
                        'color': 'rgba(199,210,254,0.9)',
                        'fontSize': '0.75rem',
                        'fontWeight': '600',
                        'letterSpacing': '0.15em',
                        'textAlign': 'center',
                        'marginBottom': '0.5rem',
                    },
                ),
                html.H1(
                    'Análisis de Mortalidad en Colombia 2019',
                    style={
                        'color': 'white',
                        'textAlign': 'center',
                        'fontWeight': '700',
                        'fontSize': '2rem',
                        'marginBottom': '0.5rem',
                        'textShadow': '0 2px 12px rgba(0,0,0,0.3)',
                    },
                ),
                html.P(
                    'Dashboard interactivo — Fuente: DANE · Estadísticas Vitales EEVV 2019',
                    style={
                        'color': 'rgba(196,181,253,0.85)',
                        'textAlign': 'center',
                        'fontSize': '0.9rem',
                        'margin': '0',
                    },
                ),
            ],
        ),

        # ── Contenido ────────────────────────────────────────────────────────
        dbc.Container(fluid=True, style={'padding': '0 1.5rem'}, children=[

            # ① Mapa
            dbc.Row(className='mb-2', children=[
                dbc.Col(section_label('🗺️', 'Distribución Geográfica'))
            ]),
            dbc.Row(className='mb-4', children=[
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_map), style=CARD_STYLE))
            ]),

            # ② + ③ Líneas y Barras violentas
            dbc.Row(className='mb-2', children=[
                dbc.Col(section_label('📅', 'Tendencia Mensual'), width=12, lg=6),
                dbc.Col(section_label('🔫', 'Ciudades más Violentas'), width=12, lg=6),
            ]),
            dbc.Row(className='mb-4', children=[
                dbc.Col(
                    dbc.Card(dcc.Graph(figure=fig_line), style=CARD_STYLE),
                    width=12, lg=6,
                ),
                dbc.Col(
                    dbc.Card(dcc.Graph(figure=fig_bar_violentas), style=CARD_STYLE),
                    width=12, lg=6,
                ),
            ]),

            # ④ Pie + ⑤ Tabla
            dbc.Row(className='mb-2', children=[
                dbc.Col(section_label('🟢', 'Menor Mortalidad'), width=12, lg=5),
                dbc.Col(section_label('📋', 'Principales Causas de Muerte'), width=12, lg=7),
            ]),
            dbc.Row(className='mb-4', children=[
                dbc.Col(
                    dbc.Card(dcc.Graph(figure=fig_pie), style=CARD_STYLE),
                    width=12, lg=5,
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(
                            html.H6(
                                'Top 10 Causas de Muerte — Colombia 2019',
                                className='mb-0',
                                style={'color': C_PURPLE, 'fontWeight': '600'},
                            ),
                            style={'background': '#faf5ff', 'borderBottom': f'2px solid {C_PURPLE}'},
                        ),
                        dbc.CardBody(
                            dash_table.DataTable(
                                data=table_data.to_dict('records'),
                                columns=[{'name': c, 'id': c} for c in table_data.columns],
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '10px 14px',
                                    'fontFamily': 'Inter, system-ui, sans-serif',
                                    'fontSize': '13px',
                                    'whiteSpace': 'normal',
                                    'height': 'auto',
                                    'color': '#1e293b',
                                },
                                style_header={
                                    'background': 'linear-gradient(135deg, #5b21b6, #0369a1)',
                                    'color': 'white',
                                    'fontWeight': '600',
                                    'textAlign': 'left',
                                    'border': 'none',
                                    'padding': '12px 14px',
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': '#faf5ff',
                                    },
                                    {
                                        'if': {'column_id': 'Total de Casos'},
                                        'textAlign': 'right',
                                        'fontWeight': '700',
                                        'color': C_PURPLE,
                                    },
                                ],
                                style_data={'border': '1px solid #ede9fe'},
                                page_size=10,
                            )
                        ),
                    ], style=CARD_STYLE),
                    width=12, lg=7,
                ),
            ]),

            # ⑥ Barras apiladas
            dbc.Row(className='mb-2', children=[
                dbc.Col(section_label('⚥', 'Mortalidad por Sexo y Departamento'))
            ]),
            dbc.Row(className='mb-4', children=[
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_stacked), style=CARD_STYLE))
            ]),

            # ⑦ Histograma
            dbc.Row(className='mb-2', children=[
                dbc.Col(section_label('📊', 'Distribución por Grupo de Edad'))
            ]),
            dbc.Row(className='mb-4', children=[
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_hist), style=CARD_STYLE))
            ]),

            # Footer
            dbc.Row(dbc.Col(
                html.P(
                    'Fuente: DANE — Estadísticas Vitales 2019 · Desarrollado con Python, Dash y Plotly',
                    style={
                        'textAlign': 'center',
                        'color': '#94a3b8',
                        'fontSize': '0.82rem',
                        'padding': '1rem 0 2rem',
                    },
                )
            )),
        ]),
    ],
)

if __name__ == '__main__':
    app.run(
        debug=False,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8050)),
    )
