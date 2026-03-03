#!/usr/bin/env python3
# main.py - Interfaz web con Streamlit para el agente LangGraph

import streamlit as st
import os
from dotenv import load_dotenv
from agent_langgraph import run_agent

# Cargar variables de entorno
load_dotenv()

# ============================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================

st.set_page_config(
    page_title="Agente SQL CitiBike - Kevin Inofuente",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# ESTILOS PERSONALIZADOS
# ============================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR - INFORMACIÓN Y EJEMPLOS
# ============================================

with st.sidebar:
    # Mostrar logo si existe
    if os.path.exists("images/datapath-logo.png"):
        st.image("images/datapath-logo.png", width=200)
    
    st.markdown("## 🚴 Agente SQL CitiBike")
    st.markdown("---")
    
    st.markdown("### 📊 Sobre este proyecto")
    st.info("""
    Este agente inteligente utiliza **LangGraph** y **Google Gemini** para responder 
    preguntas en lenguaje natural sobre los datos de CitiBike NYC almacenados en BigQuery.
    """)
    
    st.markdown("### 💡 Ejemplos de preguntas:")
    ejemplos = [
        "¿Cuántos viajes en total hay?",
        "¿Cuál es la ruta más popular?",
        "¿Cuál es la duración promedio?",
        "¿Cuántos usuarios son subscribers?",
        "Dame las 5 estaciones más usadas",
        "¿En qué año hay más viajes?"
    ]
    
    for ejemplo in ejemplos:
        if st.button(f"📝 {ejemplo}", key=ejemplo, use_container_width=True):
            st.session_state.ejemplo_seleccionado = ejemplo
    
    st.markdown("---")
    st.markdown("### 🛠️ Tecnologías")
    st.markdown("""
    - **LangGraph 1.0** - Orquestación de agentes
    - **Google Gemini 2.5 Pro** - Modelo de lenguaje
    - **BigQuery** - Base de datos
    - **Streamlit** - Interface web
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Estado del sistema")
    
    # Verificar configuración
    gemini_ok = bool(os.getenv("GOOGLE_API_KEY"))
    bigquery_ok = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    
    st.markdown(f"**Gemini:** {'✅' if gemini_ok else '❌'}")
    st.markdown(f"**BigQuery:** {'✅' if bigquery_ok else '❌'}")
    
    if not gemini_ok or not bigquery_ok:
        st.error("⚠️ Faltan configuraciones. Revisa el archivo .env")

# ============================================
# HEADER PRINCIPAL
# ============================================

st.markdown('<p class="main-header">🚴 Agente Analista de CitiBike NYC</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Pregúntame cualquier cosa sobre los datos de viajes de CitiBike</p>', unsafe_allow_html=True)

# ============================================
# INICIALIZAR SESSION STATE
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []
    # Mensaje de bienvenida
    st.session_state.messages.append({
        "role": "assistant",
        "content": """¡Hola! 👋 Soy tu asistente para analizar datos de CitiBike NYC. 

Puedo responder preguntas sobre:
- 📊 Estadísticas de viajes
- 🗺️ Rutas y estaciones populares
- ⏱️ Duraciones y patrones temporales
- 👥 Tipos de usuarios

**¿Qué te gustaría saber?**"""
    })

if "ejemplo_seleccionado" not in st.session_state:
    st.session_state.ejemplo_seleccionado = None

# ============================================
# MOSTRAR HISTORIAL DE CHAT
# ============================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================
# INPUT DEL USUARIO
# ============================================

# Si se seleccionó un ejemplo desde el sidebar
if st.session_state.ejemplo_seleccionado:
    prompt = st.session_state.ejemplo_seleccionado
    st.session_state.ejemplo_seleccionado = None
else:
    # Input normal del chat
    prompt = st.chat_input("Escribe tu pregunta aquí...")

# ============================================
# PROCESAR PREGUNTA
# ============================================

if prompt:
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Mostrar indicador de que está pensando
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analizando tu pregunta y consultando BigQuery..."):
            try:
                # Llamar al agente
                respuesta = run_agent(prompt)
                
                # Mostrar respuesta
                st.markdown(respuesta)
                
                # Agregar al historial
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": respuesta
                })
                
            except Exception as e:
                error_msg = f"❌ **Error:** {str(e)}\n\nPor favor, intenta reformular tu pregunta o contacta al administrador."
                st.error(error_msg)
                
                # Agregar error al historial
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# ============================================
# BOTÓN PARA LIMPIAR CONVERSACIÓN
# ============================================

col1, col2, col3 = st.columns([1, 1, 1])

with col2:
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": """¡Conversación reiniciada! 🔄

¿Qué te gustaría saber sobre los datos de CitiBike?"""
        })
        st.rerun()

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>Desarrollado con ❤️ usando LangGraph 1.0 + Google Gemini + BigQuery</p>
    <p>📚 Proyecto educativo para enseñanza de agentes con LangGraph</p>
</div>
""", unsafe_allow_html=True)

