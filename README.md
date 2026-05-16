# Análisis de Mortalidad en Colombia 2019

## Introducción del proyecto

Dashboard web interactivo que analiza los datos de mortalidad no fetal en Colombia para el año 2019, basado en microdatos del DANE (Estadísticas Vitales — EEVV 2019). Permite explorar patrones demográficos, regionales y causales de las defunciones registradas ese año.

## Objetivo

Transformar los microdatos de mortalidad del DANE en visualizaciones interactivas que permitan identificar tendencias, patrones por sexo, edad, región y causa de muerte, facilitando el análisis epidemiológico y demográfico de Colombia en 2019.

## Estructura del proyecto

```
activida_cuatro/
├── app.py                                      # Aplicación principal Dash
├── requirements.txt                            # Dependencias Python
├── Procfile                                    # Comando de inicio para Render/Heroku
├── render.yaml                                 # Configuración de despliegue en Render
├── colombia_departments.geojson                # GeoJSON departamentos Colombia (cacheado)
├── Anexo1.NoFetal2019_CE_15-03-23.xlsx        # Datos de mortalidad 2019 (244 355 registros)
├── Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx    # Catálogo CIE-10 causas de muerte
└── Divipola_CE_.xlsx                           # División político-administrativa Colombia
```

## Requisitos

| Librería                  | Versión mínima |
|---------------------------|----------------|
| dash                      | 2.14.0         |
| dash-bootstrap-components | 1.5.0          |
| plotly                    | 5.17.0         |
| pandas                    | 2.0.0          |
| openpyxl                  | 3.1.0          |
| requests                  | 2.31.0         |
| gunicorn                  | 21.2.2         |

## Instalación

```bash
# 1. Clonar el repositorio
git clone <URL_DEL_REPO>
cd activida_cuatro

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar localmente
python app.py
# Abrir http://127.0.0.1:8050
```

## Despliegue en Render

1. Crear cuenta en [render.com](https://render.com) y conectar el repositorio de GitHub.
2. En Render → **New Web Service** → seleccionar el repositorio.
3. Configurar:
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:server`
4. Deployar. La URL pública queda disponible en el dashboard de Render.

> Alternativa: el archivo `render.yaml` en la raíz del repositorio permite el despliegue automático con un clic ("Blueprint").

## Software utilizado

- **Python 3.11** — lenguaje principal
- **Dash 2.x** — framework para aplicaciones web analíticas
- **Plotly** — visualizaciones interactivas
- **Dash Bootstrap Components** — layout responsivo con Bootstrap 5
- **Pandas** — procesamiento y análisis de datos
- **Gunicorn** — servidor WSGI para producción

## Visualizaciones e interpretación de resultados

### 1. Mapa coroplético — Distribución de muertes por departamento

Mapa de Colombia coloreado según el total de defunciones por departamento. Permite identificar de inmediato las regiones con mayor carga de mortalidad. Los departamentos con mayor concentración poblacional (Antioquia, Valle del Cauca, Cundinamarca, Bogotá) concentran también el mayor número de muertes absolutas, lo que es consistente con su densidad demográfica.

### 2. Gráfico de líneas — Total de muertes por mes

Muestra la variación mensual de defunciones a lo largo de 2019. Se observan picos en los meses de enero y diciembre, asociados a enfermedades respiratorias estacionales, así como períodos de relativa estabilidad durante el segundo semestre.

### 3. Gráfico de barras — Top 5 ciudades más violentas (X95)

Ciudades con mayor número de homicidios por arma de fuego (códigos CIE-10 X950–X959). Evidencia la concentración de la violencia armada en ciudades específicas y permite focalizar políticas de seguridad pública.

### 4. Gráfico circular — 10 ciudades con menor mortalidad

Municipios con el menor número de defunciones registradas en 2019. Refleja tanto el pequeño tamaño poblacional de estos municipios como posibles subregistros en áreas de difícil acceso.

### 5. Tabla — Top 10 causas de muerte

Listado de los 10 códigos CIE-10 con mayor frecuencia, ordenados de mayor a menor. Las enfermedades cardiovasculares, respiratorias crónicas y los eventos de causa externa lideran la mortalidad en Colombia, en línea con el perfil epidemiológico de un país de ingresos medios en transición demográfica.

### 6. Gráfico de barras apiladas — Muertes por sexo y departamento

Comparación por departamento de las defunciones según sexo. En todos los departamentos se observa mayor mortalidad masculina, diferencia que se acentúa en departamentos con alta violencia (homicidios, accidentes de tránsito) donde el perfil de víctimas es predominantemente masculino.

### 7. Histograma — Distribución por grupo de edad (GRUPO_EDAD1)

Distribución de defunciones según los rangos etarios definidos por el DANE. La curva muestra dos concentraciones: mortalidad neonatal/infantil en los primeros grupos, y un pico pronunciado en la vejez (60–84 años) y longevidad (85+), reflejando las causas degenerativas propias del envejecimiento poblacional.
