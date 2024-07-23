# Dockerfile

# Use uma imagem base com Python
FROM python:3.9-slim

# Defina o diretório de trabalho
WORKDIR /app

# Copie os arquivos do projeto para o diretório de trabalho
COPY . .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Instale o cron
RUN apt-get update && apt-get install -y cron

# Adicione o crontab
COPY crontab /etc/cron.d/crontab

# Dê permissão ao crontab
RUN chmod 0644 /etc/cron.d/crontab

# Aplique o crontab
RUN crontab /etc/cron.d/crontab

# Comando padrão para iniciar o cron
CMD ["cron", "-f"]
