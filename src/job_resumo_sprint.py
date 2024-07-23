from jira import JIRA
import os
from datetime import datetime
import requests
import matplotlib.pyplot as plt

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
                sprint_start_date = datetime.strptime(sprint.startDate, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')
                sprint_end_date = datetime.strptime(sprint.endDate, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')
                break

        if sprint_id:
            # Buscar todas as tarefas do sprint ativo
            jql_query = f'sprint = {sprint_id}'
            issues = jira.search_issues(jql_query)

            # Organizar tarefas por status e depois por pessoa atribuída
            tasks_by_status_and_assignee = {}
            total_tasks = len(issues)
            completed_tasks = 0

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

                if status == 'Concluído':  # Verifique o status que indica conclusão
                    completed_tasks += 1

            # Calcular o percentual concluído
            completion_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            remaining_tasks = total_tasks - completed_tasks

            # Gerar e salvar o gráfico
            statuses = list(tasks_by_status_and_assignee.keys())
            task_counts = [len(tasks) for tasks in tasks_by_status_and_assignee.values()]

            plt.figure(figsize=(10, 6))
            plt.bar(statuses, task_counts, color=['blue', 'orange', 'green'])
            plt.xlabel('Status')
            plt.ylabel('Número de Tarefas')
            plt.title('Quantidade de Tarefas por Status')
            plt.grid(axis='y')

            # Salvar o gráfico como uma imagem
            plt.savefig('task_counts.png')
            plt.close()  # Fechar a figura para liberar memória

            # Construir o conteúdo da mensagem
            content = (
                f"**Relatório Diário: Sprint {sprint_name} ({sprint_start_date} - {sprint_end_date})**\n\n"
                f"**Total de Tarefas:** {total_tasks}\n"
                f"**Tarefas Concluídas:** {completed_tasks}\n"
                f"**Percentual Concluído:** {completion_percentage:.2f}%\n"
                f"**Tarefas Restantes:** {remaining_tasks}\n\n"
                "## Tarefas por Status e Pessoa:\n"
            )

            for status, assignees in tasks_by_status_and_assignee.items():
                content += f"\n**{status}:**\n"
                for assignee, tasks in assignees.items():
                    content += f"\n**{assignee}:**\n"
                    content += "\n".join(tasks)
                    content += "\n"

            # Enviar a mensagem de texto para o Discord
            text_data = {'content': content}
            text_response = requests.post(webhook_url, json=text_data)
            print(f"Status Code do Texto: {text_response.status_code}")
            print(f"Resposta do Discord do Texto: {text_response.text}")

            # Enviar a imagem para o Discord
            with open('task_counts.png', 'rb') as file:
                image_data = {
                    'content': 'Aqui está o gráfico das tarefas por status:'
                }
                image_files = {
                    'file': ('task_counts.png', file, 'image/png')
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