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
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

# 5. Script de inicio simplificado
RUN echo '#!/bin/bash\nexec streamlit run main.py' > /app/start.sh && chmod +x /app/start.sh

# 6. Ejecutar el script
ENTRYPOINT ["/app/start.sh"]