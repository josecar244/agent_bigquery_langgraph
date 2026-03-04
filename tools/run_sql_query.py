# tools/run_sql_query.py

import os
from sqlalchemy import create_engine, text
from google.cloud import bigquery
from google.cloud.bigquery import dbapi
import pandas as pd
import sys
from langchain_core.tools import tool

import tempfile
import json

# Reemplaza con tu propio ID de proyecto de Google Cloud o léelo del entorno
TU_PROYECTO_GCP_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyecto-ai-13-agent-bqjc244")
# URI de conexión que indica a SQLAlchemy usar BigQuery y la tabla pública de CitiBike
db_uri = "bigquery://bigquery-public-data/new_york_citibike"

# --- LÓGICA DE CREDENCIALES (PRODUCCIÓN) ---
def initialize_credentials():
    """Configura las credenciales de GCP usando un archivo temporal seguro."""
    json_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if not json_creds:
        return

    try:
        json_creds = json_creds.strip()
        # Crear archivo temporal para el SDK
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write(json_creds)
            temp_path = tmp.name
        
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_path
    except Exception as e:
        print(f"Error inicializando credenciales: {e}", file=sys.stderr)

# Inicialización automática
initialize_credentials()

# Variable global para el engine
_engine = None

def get_bigquery_connection():
    """Conecta a BigQuery usando las credenciales configuradas."""
    client = bigquery.Client(project=TU_PROYECTO_GCP_ID)
    return dbapi.connect(client=client)

def get_engine():
    """
    Obtiene el engine de SQLAlchemy, creándolo solo si es necesario (lazy loading).
    """
    global _engine
    if _engine is None:
        _engine = create_engine(db_uri, creator=get_bigquery_connection)
    return _engine
# -----------------------------------------------------------


# Tool para LangChain - Ejecuta consultas SQL en BigQuery
@tool
def run_sql_query_langchain(query: str) -> str:
    """
    Ejecuta una consulta SQL en una base de datos de BigQuery que contiene datos de viajes de CitiBike en Nueva York
    y devuelve el resultado como una tabla formateada. La consulta debe ser compatible
    con el dialecto SQL de Google BigQuery.

    Args:
        query: La consulta SQL completa a ejecutar en BigQuery.

    Returns:
        El resultado de la consulta como una tabla de texto (Markdown) o un mensaje de error.
    """
    try:
        # Ejecutar consulta a través del engine de SQLAlchemy
        engine = get_engine()
        with engine.connect() as connection:
            result_proxy = connection.execute(text(query))
            df = pd.DataFrame(result_proxy.fetchall(), columns=result_proxy.keys())
            
            if df.empty:
                return "La consulta se ejecutó correctamente, pero no devolvió resultados."
            
            return df.to_markdown(index=False)

    except Exception as e:
        return f"Error en la consulta de base de datos: {e}"