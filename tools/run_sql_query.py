# tools/run_sql_query.py

import os
from sqlalchemy import create_engine, text
from google.cloud import bigquery
from google.cloud.bigquery import dbapi
import pandas as pd
import sys
from langchain_core.tools import tool

# Reemplaza con tu propio ID de proyecto de Google Cloud o léelo del entorno
TU_PROYECTO_GCP_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyecto-ai-13-agent-bqjc244")
# URI de conexión que indica a SQLAlchemy usar BigQuery y la tabla pública de CitiBike
db_uri = "bigquery://bigquery-public-data/new_york_citibike"

# Variable global para el engine (lazy loading)
_engine = None

def get_bigquery_connection():
    """
    Inicializa el cliente de BigQuery de forma robusta.
    Prioriza:
    1. Variable GOOGLE_CREDENTIALS_JSON (contenido directo)
    2. Variable GOOGLE_APPLICATION_CREDENTIALS (ruta a archivo)
    """
    import os
    import json
    from google.oauth2 import service_account
    
    json_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if json_creds:
        print("DEBUG: Usando credenciales desde GOOGLE_CREDENTIALS_JSON directamente.", flush=True)
        try:
            # Limpiar posibles carácteres invisibles
            json_creds = json_creds.strip()
            info = json.loads(json_creds)
            print(f"DEBUG: JSON cargado correctamente. Email: {info.get('client_email')}", flush=True)
            credentials = service_account.Credentials.from_service_account_info(info)
            client = bigquery.Client(project=TU_PROYECTO_GCP_ID, credentials=credentials)
        except Exception as e:
            print(f"DEBUG: Error al procesar GOOGLE_CREDENTIALS_JSON: {e}", file=sys.stderr, flush=True)
            client = bigquery.Client(project=TU_PROYECTO_GCP_ID)
    else:
        print("DEBUG: Usando credenciales desde archivo (vía env var).", flush=True)
        client = bigquery.Client(project=TU_PROYECTO_GCP_ID)
    
    # Creamos y devolvemos la conexión DB-API compatible con SQLAlchemy
    connection = dbapi.connect(client=client)
    return connection

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
        print(f"DEBUG: Ejecutando consulta SQL: {query}", flush=True)
        # Obtener el engine (lazy loading)
        engine = get_engine()
        with engine.connect() as connection:
            # Usamos text() para asegurar que SQLAlchemy trate el string como SQL literal
            result_proxy = connection.execute(text(query))
            
            # Convertimos el resultado a un DataFrame de Pandas para un formato bonito
            df = pd.DataFrame(result_proxy.fetchall(), columns=result_proxy.keys())
            
            print(f"DEBUG: Consulta exitosa. Filas obtenidas: {len(df)}", flush=True)
            
            # Si el DataFrame está vacío, devuelve un mensaje
            if df.empty:
                return "La consulta se ejecutó correctamente, pero no devolvió resultados."
            
            # Convertimos el DataFrame a un string (Markdown) para que el LLM lo pueda leer
            return df.to_markdown(index=False)

    except Exception as e:
        print(f"DEBUG: ERROR en BigQuery: {str(e)}", file=sys.stderr, flush=True)
        # Si hay un error de SQL, devuélvelo para que el agente pueda intentar corregirlo.
        return f"Error al ejecutar la consulta: {e}"