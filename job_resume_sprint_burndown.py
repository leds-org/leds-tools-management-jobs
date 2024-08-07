from jira import JIRA
import os
from datetime import datetime, timedelta
import requests
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

jira_url = os.getenv('JIRA_URL')
jira_username = os.getenv('JIRA_USERNAME')
jira_api_token = os.getenv('JIRA_API_TOKEN')
webhook_url = os.getenv('WEBHOOK_URL')

# Autenticar no Jira
jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})

def format_date(date_str):
    """Formata a data no formato dd/mm/yyyy, retorna 'Data não disponível' se a data for inválida."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')
    except ValueError:
        return 'Data não disponível'

def generate_burndown_chart(dates, tasks_remaining, sprint_name):
    plt.figure(figsize=(10, 6))
    plt.plot(dates, tasks_remaining, label='Real', marker='o')
    
    # Linha ideal
    ideal_line = [tasks_remaining[0] - (tasks_remaining[0] / len(dates)) * i for i in range(len(dates))]
    plt.plot(dates, ideal_line, label='Ideal', linestyle='--', color='red')
    
    plt.xlabel('Data')
    plt.ylabel('Tarefas Restantes')
    plt.title(f'Gráfico de Burndown - {sprint_name}')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Salvar o gráfico como uma imagem
    plt.savefig('burndown_chart.png')
    plt.close()  # Fechar a figura para liberar memória

def process_board(board_id):
    try:
        # Obter os sprints do board específico
        sprints = jira.sprints(board_id)

        # Encontrar o sprint ativo
        sprint_id = None
        for sprint in sprints:
            if sprint.state == 'active':
                sprint_id = sprint.id
                sprint_name = sprint.name
                sprint_start_date = datetime.strptime(sprint.startDate, '%Y-%m-%dT%H:%M:%S.%f%z')
                sprint_end_date = datetime.strptime(sprint.endDate, '%Y-%m-%dT%H:%M:%S.%f%z')
                break

        if sprint_id:
            # Buscar todas as tarefas do sprint ativo
            jql_query = f'sprint = {sprint_id}'
            issues = jira.search_issues(jql_query)

            # Organizar tarefas por status e depois por pessoa atribuída
            tasks_by_status_and_assignee = {}
            total_tasks = len(issues)
            completed_tasks = 0

            dates = []
            tasks_remaining = []

            for issue in issues:
                status = issue.fields.status.name
                assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Não atribuído"
                created_date = datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')
                updated_date = datetime.strptime(issue.fields.updated, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')

                if status not in tasks_by_status_and_assignee:
                    tasks_by_status_and_assignee[status] = {}

                if assignee not in tasks_by_status_and_assignee[status]:
                    tasks_by_status_and_assignee[status][assignee] = []

                tasks_by_status_and_assignee[status][assignee].append(
                    f"- **{issue.key}**: {issue.fields.summary} (Criado em: {created_date}, Atualizado em: {updated_date})"
                )

                if status == 'Concluído':
                    completed_tasks += 1

            # Coletar dados para o gráfico de Burndown
            current_date = sprint_start_date
            while current_date <= sprint_end_date:
                dates.append(current_date.strftime('%d/%m/%Y'))
                tasks_remaining.append(total_tasks - completed_tasks)
                current_date += timedelta(days=1)

            # Gerar o gráfico de Burndown
            generate_burndown_chart(dates, tasks_remaining, sprint_name)

            # Enviar a imagem do gráfico de Burndown para o Discord
            with open('burndown_chart.png', 'rb') as file:
                image_data = {
                    'content': '# Gráfico de Burndown:'
                }
                image_files = {
                    'file': ('burndown_chart.png', file, 'image/png')
                }
                image_response = requests.post(webhook_url, data=image_data, files=image_files)
                print(f"Status Code da Imagem: {image_response.status_code}")
                print(f"Resposta do Discord da Imagem: {image_response.text}")

        else:
            print("Nenhum sprint ativo encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro ao processar o board {board_id}: {e}")

def main():
    try:
        # Obter todos os boards
        boards = jira.boards()

        # Processar cada board
        for board in boards:
            process_board(board.id)

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
