FROM python:3.10.15-slim

# Installation des dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Création d’un utilisateur sécurisé
RUN addgroup --system lafaom && adduser --system --ingroup lafaom lafaom

# Définition du dossier de travail
WORKDIR /app

# Copier le fichier requirements
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install -i https://test.pypi.org/simple/ cinetpay-sdk==0.1.1


# Copie des scripts d’entrée et de démarrage
COPY ./entrypoint /entrypoint
COPY ./start /start
RUN sed -i 's/\r$//g' /entrypoint /start && \
    chmod +x /entrypoint /start && \
    chown lafaom:lafaom /entrypoint /start

# Copie du code source
COPY . .

# Création des répertoires nécessaires avec les bonnes permissions
RUN mkdir -p /app/static/documents \
             /app/static/images \
             /app/static/audios \
             /app/static/videos \
             /app/logs \
             /app/upload && \
    chown -R lafaom:lafaom /app/static /app/logs /app/upload


# Attribution finale des droits sur /app
RUN chown -R lafaom:lafaom /app
RUN mkdir -p /app/upload && chmod -R 777 /app/upload


# Utilisation de l’utilisateur non-root
USER lafaom

# Exposition du port de l'application
EXPOSE 8000

# Point d’entrée
ENTRYPOINT ["/entrypoint"]