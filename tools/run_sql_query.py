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

# --- LÓGICA DE CREDENCIALES (UTS 2026 - DIAGNÓSTICO) ---
def initialize_credentials():
    json_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
    print(f"DEBUG: Verificando GOOGLE_CREDENTIALS_JSON... Presencia: {json_creds is not None}", file=sys.stderr, flush=True)
    
    if not json_creds:
        print("DEBUG: ADVERTENCIA - GOOGLE_CREDENTIALS_JSON está vacía o no existe.", file=sys.stderr, flush=True)
        return

    print(f"DEBUG: GOOGLE_CREDENTIALS_JSON detectada (Longitud: {len(json_creds)}). Cargando...", file=sys.stderr, flush=True)
    try:
        # Limpieza robusta
        json_creds = json_creds.strip()
        # Verificar integridad
        creds_dict = json.loads(json_creds) 
        print(f"DEBUG: JSON validado. Proyecto: {creds_dict.get('project_id')}. Email: {creds_dict.get('client_email')}", file=sys.stderr, flush=True)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write(json_creds)
            temp_path = tmp.name
        
        # Configurar variable crucial para el SDK
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_path
        print(f"DEBUG: Puente establecido: GOOGLE_APPLICATION_CREDENTIALS -> {temp_path}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"DEBUG: ERROR CRÍTICO configurando credenciales: {str(e)}", file=sys.stderr, flush=True)

# Ejecutar inmediatamente al importar el módulo
initialize_credentials()

# Variable global para el engine (lazy loading)
_engine = None

def get_bigquery_connection():
    """
    Inicializa el cliente de BigQuery con el proyecto correcto.
    Ya debería tener GOOGLE_APPLICATION_CREDENTIALS configurada.
    """
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