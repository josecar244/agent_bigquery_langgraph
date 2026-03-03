# ==========================================
# DOCKERFILE OPTIMIZADO PARA PRODUCCIÓN (RENDER)
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# 1. Copiar requirements.txt para instalar dependencias primero
COPY requirements.txt .

# 2. Instalar dependencias con uv
RUN uv pip install --system --no-cache -r requirements.txt

# 3. Copiar el resto del código
COPY . /app

# 4. Configurar variables de entorno para Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501

# 5. Script de inicio para manejar credenciales de Google en plataformas PaaS como Render
# Genera el archivo .json a partir de una variable de entorno inyectada desde el panel
RUN echo '#!/bin/bash\n\
    if [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then\n\
    echo "$GOOGLE_CREDENTIALS_JSON" > /app/google_credentials.json\n\
    export GOOGLE_APPLICATION_CREDENTIALS="/app/google_credentials.json"\n\
    else\n\
    echo "⚠️ Advertencia: GOOGLE_CREDENTIALS_JSON no está definida en el entorno."\n\
    fi\n\
    exec streamlit run main.py\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# 6. Ejecutar el script
ENTRYPOINT ["/app/start.sh"]