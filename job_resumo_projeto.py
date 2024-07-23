import os
import numpy as np
import matplotlib.pyplot as plt
import requests
from jira import JIRA
from datetime import datetime, timedelta
import io
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Jira e Discord a partir das variáveis de ambiente
jira_url = os.getenv('JIRA_URL')
jira_username = os.getenv('JIRA_USERNAME')
jira_api_token = os.getenv('JIRA_API_TOKEN')
webhook_url = os.getenv('WEBHOOK_URL')

# Conectar ao Jira
jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})

# Função para listar todos os status disponíveis no Jira
def list_statuses():
    statuses = jira.statuses()
    for status in statuses:
        print(f"Status: {status.name}")

def get_velocity(sprints):
    total_completed_tasks = 0
    total_sprints = len(sprints)
    for sprint in sprints:
        if sprint.state == 'closed':
            jql_query = f'sprint = {sprint.id} AND status = "Done"'  # Ajustar o status aqui se necessário
            issues = jira.search_issues(jql_query, maxResults=False)
            total_completed_tasks += len(issues)
    return total_completed_tasks / total_sprints if total_sprints > 0 else 0

def get_remaining_work(project_key):
    jql_query = f'project = {project_key} AND status != "Done"'  # Ajustar o status aqui se necessário
    issues = jira.search_issues(jql_query, maxResults=False)
    remaining_work = len(issues)
    return remaining_work

def get_project_statistics(board_id, completed_status, in_progress_status):
    sprints = jira.sprints(board_id)
    total_issues = 0
    completed_issues = 0
    pending_issues = 0

    for sprint in sprints:
        if sprint.state in ['active', 'closed']:
            jql_query = f'sprint = {sprint.id}'
            issues = jira.search_issues(jql_query, maxResults=False)
            total_issues += len(issues)
            completed_issues += sum(1 for issue in issues if issue.fields.status.name == completed_status)
            pending_issues += sum(1 for issue in issues if issue.fields.status.name == in_progress_status)

    not_started_issues = total_issues - completed_issues - pending_issues
    completed_percentage = (completed_issues / total_issues) * 100 if total_issues > 0 else 0
    return completed_issues, pending_issues, not_started_issues, completed_percentage

def estimate_completion_date(velocity, remaining_work):
    if velocity <= 0:
        return "Velocidade é zero ou negativa, não é possível estimar a conclusão."
    
    estimated_sprints = remaining_work / velocity
    today = datetime.now()
    estimated_completion_date = today + timedelta(weeks=int(estimated_sprints * 2))  # Supondo sprints de 2 semanas
    return estimated_completion_date.strftime('%d/%m/%Y')

def send_report_to_discord(project_key, velocity, remaining_work, completion_date, completed_issues, pending_issues, not_started_issues, completed_percentage):
    if webhook_url is None:
        print(f"Erro: URL do webhook do Discord não está configurada.")
        return None

    content = (
        f"**Relatório de Projeção de Conclusão do Projeto: {project_key}**\n\n"
        f"**Velocidade da Equipe:** {velocity:.2f} tarefas por sprint\n"
        f"**Trabalho Restante:** {remaining_work} tarefas\n"
        f"**Data Estimada de Conclusão:** {completion_date}\n"
        f"**Número de Tarefas Concluídas:** {completed_issues}\n"
        f"**Número de Tarefas Pendentes:** {pending_issues}\n"
        f"**Número de Tarefas Não Realizadas:** {not_started_issues}\n"
        f"**Percentual Concluído:** {completed_percentage:.2f}%\n"
    )

    data = {
        'content': content
    }
    try:
        response = requests.post(webhook_url, data=data)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Erro ao enviar relatório para o Discord: {e}")
        return None

def get_board_id_for_project(project_key):
    boards = jira.boards()
    for board in boards:
        if board.location.projectKey == project_key:
            return board.id
    return None

def main():
    projects = jira.projects()
    
    # Listar todos os status disponíveis no Jira para ajustar o status correto
    list_statuses()

    # Ajuste os nomes dos status conforme necessário
    completed_status = "Done"  # Exemplo de status concluído
    in_progress_status = "In Progress"  # Exemplo de status em andamento

    for project in projects:
        project_key = project.key
        board_id = get_board_id_for_project(project_key)
        
        if not board_id:
            print(f"Nenhum board encontrado para o projeto {project_key}")
            continue

        sprints = jira.sprints(board_id)

        velocity = get_velocity(sprints)
        remaining_work = get_remaining_work(project_key)
        completed_issues, pending_issues, not_started_issues, completed_percentage = get_project_statistics(board_id, completed_status, in_progress_status)
        completion_date = estimate_completion_date(velocity, remaining_work)

        # Enviar o relatório para o Discord
        response = send_report_to_discord(project_key, velocity, remaining_work, completion_date, completed_issues, pending_issues, not_started_issues, completed_percentage)
        if response:
            print(f"Status Code: {response.status_code}")
            print(f"Resposta do Discord: {response.text}")

if __name__ == "__main__":
    main()