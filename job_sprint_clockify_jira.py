import requests
import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv
from jira import JIRA
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações da API do Clockify
CLOCKIFY_API_KEY = '65f486199c30924868182a19'
CLOCKIFY_WORKSPACE_ID = 'YTA4NjQyZjItNmRjOC00ODFkLWIwZmItNmY0ZmU2YjJhZjUz'
CLOCKIFY_BASE_URL = 'https://api.clockify.me/api/v1'
CLOCKIFY_HEADERS = {
    'X-Api-Key': CLOCKIFY_API_KEY
}

# Configurações da API do Jira
jira_url = os.getenv('JIRA_URL')
jira_username = os.getenv('JIRA_USERNAME')
jira_api_token = os.getenv('JIRA_API_TOKEN')
DISCORD_WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Função para obter usuários do workspace no Clockify
def get_users(workspace_id):
    url = f'{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}/users'
    response = requests.get(url, headers=CLOCKIFY_HEADERS)
    return response.json()

# Função para obter registros de tempo de um usuário no Clockify
def get_time_entries(workspace_id, user_id, start_date, end_date):
    url = f'{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries'
    params = {
        'start': start_date.isoformat() + 'Z',
        'end': end_date.isoformat() + 'Z'
    }
    response = requests.get(url, headers=CLOCKIFY_HEADERS, params=params)
    return response.json()

# Função para obter todos os projetos no Jira
def get_all_projects(jira):
    return jira.projects()

# Função para obter todos os boards no Jira
def get_all_boards(jira):
    start_at = 0
    max_results = 50
    boards = []
    while True:
        results = jira.boards(startAt=start_at, maxResults=max_results)
        boards.extend(results)
        if len(results) < max_results:
            break
        start_at += max_results
    return boards

# Função para obter o sprint ativo de um board no Jira
def get_active_sprint(jira, board_id):
    sprints = jira.sprints(board_id)
    for sprint in sprints:
        if sprint.state == 'active':
            return sprint
    return None

# Função para obter tarefas do sprint no Jira
def get_jira_issues(jira, sprint_id):
    jql = f'sprint = {sprint_id}'
    issues = jira.search_issues(jql)
    return issues

# Função para enviar mensagem ao Discord
def send_to_discord(message):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    embed = DiscordEmbed(title='Relatório de Horas Trabalhadas', description=message, color='03b2f8')
    webhook.add_embed(embed)
    webhook.execute()

# Função para converter duração (PTnHnMnS) em horas decimais
def parse_duration(duration):
    hours = 0
    minutes = 0
    if 'H' in duration:
        hours = int(duration.split('H')[0].replace('PT', ''))
        duration = duration.split('H')[1]
    if 'M' in duration:
        minutes = int(duration.split('M')[0])
    return hours + minutes / 60

# Função principal
def main():
    # Define o intervalo de datas (último dia)
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=1)

    
    # Autenticar no Jira
    jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})

    # Obtem a lista de projetos
    projects = get_all_projects(jira)

    # Obtem todos os boards
    boards = get_all_boards(jira)

    # String para armazenar a mensagem a ser enviada para o Discord
    discord_message = ''

    for project in projects:
        project_key = project.key
        project_name = project.name

        # Filtra boards do projeto atual
        project_boards = [board for board in boards if getattr(board.location, 'projectKey', '') == project_key]


        for board in project_boards:
            board_id = board.id
            board_name = board.name

            # Obtem o sprint ativo do board
            active_sprint = get_active_sprint(jira, board_id)
            if not active_sprint:
                continue
            sprint_id = active_sprint.id
            sprint_name = active_sprint.name

            # Obtem as tarefas do sprint ativo no Jira
            jira_issues = get_jira_issues(jira, sprint_id)

            # Dicionário para mapear tarefas do Jira por ID
            jira_issues_dict = {issue.key: issue for issue in jira_issues}

            # Obtem a lista de usuários
            users = get_users(CLOCKIFY_WORKSPACE_ID)

            # Para cada usuário, obtem os registros de tempo do último dia
            for user in users:
                if not isinstance(user, dict):
                    print("Formato inesperado para dados de usuário:", user)
                    continue
                user_id = user.get('id')
                user_name = user.get('name')
                if not user_id or not user_name:
                    print("Dados de usuário incompletos:", user)
                    continue
                time_entries = get_time_entries(CLOCKIFY_WORKSPACE_ID, user_id, start_date, end_date)

                # Agrupa e soma horas por tarefa do Jira
                task_hours = {}
                for entry in time_entries:
                    task_id = entry.get('description')
                    duration = entry.get('timeInterval', {}).get('duration', 'PT0H0M0S')
                    hours = parse_duration(duration)
                    if task_id not in task_hours:
                        task_hours[task_id] = 0
                    task_hours[task_id] += hours

                # Adiciona os resultados à mensagem do Discord
                discord_message += f'Projeto {project_name} - Board {board_name} - Sprint {sprint_name} - Horas de {user_name}:\n'
                for task_id, hours in task_hours.items():
                    task_info = jira_issues_dict.get(task_id, {})
                    task_summary = task_info.fields.summary if task_info else 'Tarefa desconhecida'
                    discord_message += f'  Tarefa {task_id} ({task_summary}): {hours:.2f} horas\n'
                discord_message += '\n'

    # Envia a mensagem para o Discord
    send_to_discord(discord_message)

if __name__ == '__main__':
    main()
