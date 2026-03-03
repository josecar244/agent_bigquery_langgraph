# agent_langgraph.py
# 
# =========================================================================
# MANDATORY TECH-STACK METADATA (UTS)
# Core Tech: langchain-google-genai v4.2.0, langgraph v1.0.0
# Discovery Source: https://python.langchain.com/docs/integrations/chat/google_generative_ai/
# Legacy Filter: Replaced ChatOpenAI and langchain-openai with ChatGoogleGenerativeAI.
#                Unified SDK approach using langchain-google-genai 4.x.
# =========================================================================

from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
import os

# Cargar variables de entorno desde el archivo .env
from dotenv import load_dotenv
load_dotenv()  # Carga las variables del archivo .env automáticamente

# ============================================
# 1. IMPORTAR EL TOOL DESDE LA CARPETA TOOLS
# ============================================

# Importamos el tool de SQL desde la carpeta tools
# Esta versión ya viene decorada con @tool de LangChain
from tools.run_sql_query import run_sql_query_langchain as run_sql_query

# ============================================
# 2. ESQUEMA DE LA TABLA
# ============================================

TABLE_SCHEMA = """
CREATE TABLE `bigquery-public-data.new_york_citibike.citibike_trips` (
    tripduration INTEGER,
    starttime TIMESTAMP,
    stoptime TIMESTAMP,
    start_station_id INTEGER,
    start_station_name STRING,
    start_station_latitude FLOAT64,
    start_station_longitude FLOAT64,
    end_station_id INTEGER,
    end_station_name STRING,
    end_station_latitude FLOAT64,
    end_station_longitude FLOAT64,
    bikeid INTEGER,
    usertype STRING,
    birth_year INTEGER,
    gender STRING,
    customer_plan STRING
)
"""

# ============================================
# 3. INSTRUCCIONES DEL AGENTE
# ============================================

SYSTEM_INSTRUCTION = f"""
# 🧠 Agente Analista de Datos SQL

Eres un analista de datos experto que se especializa en escribir consultas SQL para Google BigQuery.
Tu única tarea es convertir las preguntas de los usuarios, hechas en lenguaje natural, en consultas SQL funcionales y precisas.

## El Contexto de los Datos

Tienes acceso a una sola tabla llamada `bigquery-public-data.new_york_citibike.citibike_trips`.
Este es el esquema de la tabla:

{TABLE_SCHEMA}

## Tu Proceso de Pensamiento

1. **Analiza la Pregunta del Usuario**: Comprende profundamente qué métricas, agregaciones, filtros y ordenamientos está pidiendo el usuario.
2. **Construye la Consulta SQL**: Escribe una consulta SQL para BigQuery que responda a la pregunta.
   - **SIEMPRE** usa el nombre completo de la tabla: `bigquery-public-data.new_york_citibike.citibike_trips`.
   - Presta atención a los tipos de datos. Por ejemplo, `tripduration` está en segundos.
   - No hagas suposiciones. Si la pregunta es ambigua, es mejor que la consulta falle a que devuelva datos incorrectos.
3. **Ejecuta la Consulta**: Usa la herramienta `run_sql_query` para ejecutar el SQL que has escrito.
4. **Interpreta los Resultados**: La herramienta te devolverá los datos en formato de texto (Markdown) o un mensaje de error.
   - Si obtienes datos, preséntalos al usuario de forma clara y responde a su pregunta original en un lenguaje natural y amigable.
   - Si obtienes un error, analiza el error, corrige tu consulta SQL y vuelve a intentarlo. No le muestres el error de SQL al usuario directamente a menos que no puedas solucionarlo. Explícale el problema en términos sencillos.

## Guía de Comunicación

- Tu respuesta final debe ser en español.
- No le digas al usuario que estás escribiendo SQL. Actúa como un analista que simplemente "encuentra" la respuesta.
- Si una consulta no devuelve resultados, dilo claramente. Por ejemplo: "No encontré viajes que cumplan con esos criterios".
- Si la pregunta es sobre la "ruta más popular", asume que se refiere a la combinación de `start_station_name` y `end_station_name`.

Empieza ahora.
"""

# ============================================
# 4. DEFINICIÓN DEL ESTADO DEL GRAFO
# ============================================

class AgentState(TypedDict):
    """Estado que se pasa entre los nodos del grafo"""
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ============================================
# 5. INICIALIZACIÓN DEL MODELO Y TOOLS
# ============================================

# Inicializar el modelo con el orquestador universal init_chat_model (Patrón 2026)
# Usando el modelo frontera más reciente: Gemini 3 Pro.
llm = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai",
    temperature=0
)

# Lista de herramientas disponibles
tools = [run_sql_query]

# Bind tools al modelo
llm_with_tools = llm.bind_tools(tools)

# ============================================
# 6. FUNCIONES DE LOS NODOS DEL GRAFO
# ============================================

# No es necesario definir should_continue manualmente en 2026 si usamos tools_condition

def call_model(state: AgentState):
    """Nodo principal del agente"""
    messages = state["messages"]
    
    # En 2026, Gemini maneja SystemMessage como system_instruction nativo.
    if not messages or not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [SystemMessage(content=SYSTEM_INSTRUCTION)] + list(messages)
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# ============================================
# 7. CONSTRUCCIÓN DEL GRAFO DE LANGGRAPH
# ============================================

# ============================================
# 7. CONSTRUCCIÓN DEL GRAFO DE LANGGRAPH
# ============================================

# Crear el grafo con el estado definido
workflow = StateGraph(AgentState)

# Crear el nodo de tools
tool_node = ToolNode(tools)

# Agregar nodos al grafo
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Punto de entrada moderno con START
workflow.add_edge(START, "agent")

# Usamos tools_condition, el estándar de LangGraph para flujos de herramientas
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)

# Después de ejecutar tools, volver al agente
workflow.add_edge("tools", "agent")

# Compilar el grafo - EXPORTADO PARA LANGGRAPH STUDIO
app = workflow.compile()

# ============================================
# 8. FUNCIÓN PRINCIPAL PARA EJECUTAR EL AGENTE
# ============================================

def run_agent(query: str):
    """
    Ejecuta el agente con una consulta del usuario
    
    Args:
        query: Pregunta del usuario en lenguaje natural
        
    Returns:
        La respuesta final del agente
    """
    
    # Crear el mensaje inicial con el system instruction y la pregunta del usuario
    # Gemini soporta SystemMessage
    initial_messages = [
        SystemMessage(content=SYSTEM_INSTRUCTION),
        HumanMessage(content=query)
    ]
    
    # Ejecutar el grafo (usa la variable global 'app')
    result = app.invoke({"messages": initial_messages})
    
    # Obtener la respuesta final
    final_message = result["messages"][-1]
    content = final_message.content
    
    # UTS 2026: Manejo de respuestas estructuradas de Gemini 3/2.5
    # El modelo puede devolver una lista de bloques con metadatos y firmas de pensamiento ('extras' con 'signature').
    if isinstance(content, list):
        text_blocks = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text_blocks.append(block["text"])
            elif isinstance(block, str):
                text_blocks.append(block)
        return "".join(text_blocks)
    
    return content

# ============================================
# 9. EJEMPLO DE USO
# ============================================

if __name__ == "__main__":
    # Verificar que las variables de entorno estén configuradas
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  ERROR: La variable de entorno GOOGLE_API_KEY no está configurada.")
        print("Obtén tu API key en: https://aistudio.google.com/app/apikey")
        exit(1)
    
    # Ejemplo de preguntas
    preguntas = [
        "¿Cuántos viajes en total hay en la base de datos?",
        "¿Cuál es la ruta más popular?",
        "¿Cuál es la duración promedio de los viajes en minutos?"
    ]
    
    print("=" * 80)
    print("🚴 AGENTE ANALISTA DE CITIBIKE CON LANGGRAPH + GEMINI")
    print("=" * 80)
    
    for i, pregunta in enumerate(preguntas, 1):
        print(f"\n{'=' * 80}")
        print(f"Pregunta {i}: {pregunta}")
        print(f"{'=' * 80}\n")
        
        try:
            respuesta = run_agent(pregunta)
            print(f"Respuesta: {respuesta}")
        except Exception as e:
            print(f"Error: {e}")
        
        print()