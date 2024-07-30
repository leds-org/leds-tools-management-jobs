from jira import JIRA
import requests
import json
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Jira
# Configurações do Jira e Discord a partir das variáveis de ambiente
jira_url = os.getenv('JIRA_URL')
jira_username = os.getenv('JIRA_USERNAME')
jira_api_token = os.getenv('JIRA_API_TOKEN')

# Configurações do Clockify
CLOCKIFY_API_KEY = os.getenv('CLOCKIFY_API_KEY')
CLOCKIFY_WORKSPACE_ID = os.getenv('CLOCKIFY_WORKSPACE_ID')
CLOCKIFY_BASE_URL = 'https://api.clockify.me/api/v1'
CLOCKIFY_HEADERS = {
    'X-Api-Key': CLOCKIFY_API_KEY
}

# Configuração do Webhook do Discord
DISCORD_WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Autenticação e conexão com o Jira
jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})

# Obter o primeiro board disponível
def obter_primeiro_board():
    boards = jira.boards()
    if boards:
        return boards[0]
    return None

# Obter sprint ativo
def obter_sprint_ativo(board_id):
    sprints = jira.sprints(board_id)
    for sprint in sprints:
        if sprint.state == 'active':
            return sprint
    return None

# Obter tarefas do sprint ativo
def obter_tarefas_do_sprint(sprint_id):
    jql = f'sprint={sprint_id}'
    issues = jira.search_issues(jql)
    return issues

# Listar projetos do Clockify
def listar_projetos_clockify():
    url = f'https://api.clockify.me/api/v1/workspaces/{CLOCKIFY_WORKSPACE_ID}/projects'
    headers = {'X-Api-Key': CLOCKIFY_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        projects = json.loads(response.text)
        return projects
    else:
        print(f'Erro ao buscar projetos no Clockify: {response.status_code} - {response.text}')
        return []

# Selecionar o primeiro projeto do Clockify
def selecionar_primeiro_projeto_clockify():
    projetos = listar_projetos_clockify()
    if projetos:
        return projetos[0]['id']
    else:
        return None

# Obter horas trabalhadas por pessoa em uma tarefa do Clockify
def obter_horas_trabalhadas_por_tarefa(task_id, project_id):
    url = f'https://api.clockify.me/api/v1/workspaces/{CLOCKIFY_WORKSPACE_ID}/projects/{project_id}/tasks/{task_id}/time-entries'
    headers = {'X-Api-Key': CLOCKIFY_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        time_entries = json.loads(response.text)
    else:
        print(f'Erro ao buscar entradas de tempo no Clockify: {response.status_code} - {response.text}')
        return {}

    horas_por_pessoa = {}
    for entry in time_entries:
        user_id = entry['userId']
        duration = entry['timeInterval']['duration']  # Em ISO 8601 duration format
        hours = parse_iso8601_duration(duration)
        if user_id in horas_por_pessoa:
            horas_por_pessoa[user_id] += hours
        else:
            horas_por_pessoa[user_id] = hours
    return horas_por_pessoa

# Função para converter duração ISO 8601 para horas
def parse_iso8601_duration(duration):
    # Assumindo que a duração está no formato PTnHnMnS (apenas horas, minutos e segundos)
    hours = 0
    minutes = 0
    seconds = 0
    if 'H' in duration:
        hours = int(duration.split('H')[0].replace('PT', ''))
        duration = duration.split('H')[1]
    if 'M' in duration:
        minutes = int(duration.split('M')[0])
        duration = duration.split('M')[1]
    if 'S' in duration:
        seconds = int(duration.replace('S', ''))
    return hours + minutes / 60 + seconds / 3600

# Obter primeiro board disponível
board = obter_primeiro_board()
if not board:
    print('Nenhum board encontrado.')
else:
    print(f'Board encontrado: {board.name} (ID: {board.id})')

    # Obter sprint ativo
    sprint_ativo = obter_sprint_ativo(board.id)
    if sprint_ativo:
        print(f'Sprint ativo: {sprint_ativo.name}')

        # Obter tarefas do sprint ativo
        tarefas = obter_tarefas_do_sprint(sprint_ativo.id)
        
        # Selecionar primeiro projeto do Clockify
        project_id = selecionar_primeiro_projeto_clockify()
        if not project_id:
            print('Nenhum projeto encontrado no Clockify.')
        else:
            for tarefa in tarefas:
                task_id = tarefa.key
                horas_por_pessoa = obter_horas_trabalhadas_por_tarefa(task_id, project_id)
                
                print(f'Tarefa: {task_id}')
                for user_id, horas in horas_por_pessoa.items():
                    print(f'  Usuário: {user_id}, Horas trabalhadas: {horas:.2f}')
    else:
        print('Nenhum sprint ativo encontrado.')