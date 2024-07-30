import requests
import datetime
from collections import defaultdict
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações da API do Clockify
CLOCKIFY_API_KEY = os.getenv('CLOCKIFY_API_KEY')
CLOCKIFY_WORKSPACE_ID = os.getenv('CLOCKIFY_WORKSPACE_ID')
CLOCKIFY_BASE_URL = 'https://api.clockify.me/api/v1'
CLOCKIFY_HEADERS = {
    'X-Api-Key': CLOCKIFY_API_KEY
}

# Configuração do Webhook do Discord
DISCORD_WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Função para converter duração (PTnHnMnS) em horas decimais
def parse_duration(duration):
    if duration is None:
        return 0
    hours = 0
    minutes = 0
    seconds = 0
    duration = duration.lstrip('PT')
    
    if 'H' in duration:
        parts = duration.split('H')
        hours = int(parts[0]) if parts[0] else 0
        duration = parts[1] if len(parts) > 1 else ''
    if 'M' in duration:
        parts = duration.split('M')
        minutes = int(parts[0]) if parts[0] else 0
        duration = parts[1] if len(parts) > 1 else ''
    if 'S' in duration:
        seconds = int(duration.split('S')[0]) if duration else 0
    
    return hours + minutes / 60 + seconds / 3600

# Função para obter registros de tempo de um usuário no Clockify
def get_time_entries(workspace_id, user_id, start_date, end_date):
    url = f'{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries'
    params = {
        'start': start_date.isoformat() + 'Z',
        'end': end_date.isoformat() + 'Z'
    }
    response = requests.get(url, headers=CLOCKIFY_HEADERS, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data if data is not None else []
    else:
        print(f"Erro ao obter registros de tempo: {response.status_code} - {response.json()}")
        return []

# Função para enviar mensagem para o Discord
def send_to_discord(content):
    payload = {'content': content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("Mensagem enviada para o Discord com sucesso.")
    else:
        print(f"Erro ao enviar mensagem para o Discord: {response.status_code} - {response.text}")

# Função principal
def main():
    # Define o intervalo de datas (última semana)
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=7)
    
    # Formata o intervalo de datas
    start_date_str = start_date.strftime('%d/%m/%Y')
    end_date_str = end_date.strftime('%d/%m/%Y')

    # Obtém a lista de usuários
    users_url = f'{CLOCKIFY_BASE_URL}/workspaces/{CLOCKIFY_WORKSPACE_ID}/users'
    users_response = requests.get(users_url, headers=CLOCKIFY_HEADERS)
    if users_response.status_code == 200:
        users = users_response.json()
        if users is None:
            print("Nenhum usuário retornado.")
            return
    else:
        print(f"Erro ao obter usuários: {users_response.status_code} - {users_response.json()}")
        return

    # Inicializa um dicionário para armazenar horas trabalhadas e gastos por tarefa
    user_hours = defaultdict(lambda: defaultdict(float))
    task_hours = defaultdict(lambda: defaultdict(float))

    for user in users:
        if not isinstance(user, dict):
            print("Formato inesperado para dados de usuário:", user)
            continue
        user_id = user.get('id')
        user_name = user.get('name')
        if not user_id or not user_name:
            print("Dados de usuário incompletos:", user)
            continue
        
        # Obtém registros de tempo do usuário
        time_entries = get_time_entries(CLOCKIFY_WORKSPACE_ID, user_id, start_date, end_date)
        for entry in time_entries:
            if not isinstance(entry, dict):
                print("Formato inesperado para dados de registro de tempo:", entry)
                continue

            # Imprime a estrutura dos dados para verificar
            print("Dados de entrada:", entry)
            
            start_time = entry.get('timeInterval', {}).get('start')
            duration = entry.get('timeInterval', {}).get('duration')
            project_name = entry.get('project', {}).get('name', 'Sem Projeto')
            task_name = entry.get('task', {}).get('name', 'Sem Tarefa')
            
            if not start_time:
                print("Registro de tempo sem data de início:", entry)
                continue
            if duration is None:
                duration = 'PT0H0M0S'
            start_time = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            hours = parse_duration(duration)
            # Adiciona as horas trabalhadas ao dia da semana
            day_of_week = start_time.strftime('%A')  # Ex.: Monday
            user_hours[user_name][day_of_week] += hours
            # Adiciona as horas trabalhadas por tarefa
            task_hours[user_name][f'{project_name} - {task_name}'] += hours

    # Ordena os usuários por ordem alfabética
    sorted_users = sorted(user_hours.keys())

    # Envia uma mensagem separada para cada pessoa
    for user_name in sorted_users:
        hours = user_hours[user_name]
        tasks = task_hours[user_name]
        markdown_content = f'# Relatório de Horas Trabalhadas por {user_name}\n'
        markdown_content += f'**Período:** {start_date_str} - {end_date_str}\n\n'
        
        # Adiciona horas por tarefa
        if tasks:
            markdown_content += '## Horas por Tarefa\n'
            for task, task_hours_value in tasks.items():
                markdown_content += f'- **{task}:** {task_hours_value:.2f} horas\n'
            markdown_content += '\n'
        
        # Adiciona horas por dia da semana
        markdown_content += '## Horas por Dia da Semana\n'
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        total_hours = 0
        for day in days_of_week:
            day_hours = hours.get(day, 0)
            total_hours += day_hours
            markdown_content += f'- {day}: {day_hours:.2f} horas\n'
        markdown_content += f'**Total:** {total_hours:.2f} horas\n'

        # Envia o relatório para o Discord
        send_to_discord(markdown_content)

if __name__ == '__main__':
    main()