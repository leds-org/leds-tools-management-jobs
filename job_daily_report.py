import requests
from jira import JIRA
from datetime import datetime
import nltk
import re
from dotenv import load_dotenv
import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("tracking.log"),
        logging.StreamHandler()
    ]
)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Baixar o recurso necessário do NLTK
nltk.download('punkt')
nltk.download('stopwords')

jira_url = os.getenv('JIRA_URL')
jira_username = os.getenv('JIRA_USERNAME')
jira_api_token = os.getenv('JIRA_API_TOKEN')
webhook_url = os.getenv('WEBHOOK_URL')

# Autenticar no Jira
jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})
logging.info("Autenticado no Jira.")

def summarize_text(text, max_chars=500):
    """Resume o texto para que não exceda o limite de caracteres."""
    logging.debug(f"Resumindo texto com limite de {max_chars} caracteres.")
    sentences = nltk.sent_tokenize(text, language='portuguese')
    filtered_sentences = [sentence for sentence in sentences if sentence.strip()]
    summary = ' '.join(filtered_sentences[:5]) 

    if len(summary) > max_chars:
        logging.debug("Resumo de texto cortado para caber no limite de caracteres.")
        return summary[:max_chars] 
    return summary

def split_message(message, max_chars=2000):
    """Divide a mensagem em partes menores que respeitam o limite de caracteres."""
    logging.debug(f"Dividindo mensagem em partes de até {max_chars} caracteres.")
    return [message[i:i+max_chars] for i in range(0, len(message), max_chars)]

def clean_comment(comment):
    """Remove o nome da pessoa dos comentários."""
    logging.debug("Limpando comentário para remover nomes.")
    clean_comment = re.sub(r'\[.*?\|', '', comment)
    clean_comment = re.sub(r'\]', '', clean_comment)
    return clean_comment.strip()

def format_date(date_str):
    """Formata a data no formato dd/mm/yyyy, retorna 'Data não disponível' se a data for inválida."""
    try:
        formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
        logging.debug(f"Data formatada: {formatted_date}")
        return formatted_date
    except ValueError:
        logging.warning(f"Data inválida encontrada: {date_str}")
        return 'Data não disponível'

def is_overdue(due_date):
    """Verifica se a tarefa está em atraso."""
    try:
        today = datetime.now().date()
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
        overdue = today > due_date_obj
        logging.debug(f"Verificando se a tarefa está em atraso: {overdue}")
        return overdue
    except ValueError:
        logging.warning(f"Data de vencimento inválida encontrada: {due_date}")
        return False

def process_board(board_id):
    try:
        logging.info(f"Processando board {board_id}")
        sprints = jira.sprints(board_id)

        sprint_id = None
        for sprint in sprints:
            if sprint.state == 'active':
                sprint_id = sprint.id
                sprint_name = sprint.name
                sprint_start_date = datetime.strptime(sprint.startDate, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')
                sprint_end_date = datetime.strptime(sprint.endDate, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d/%m/%Y')
                logging.info(f"Sprint ativo encontrado: {sprint_name}")
                break

        if sprint_id:
            jql_query = (f'sprint = {sprint_id} AND (status = "In Progress" OR (status = "Done"'
                         f'AND  updated >= startOfDay()))')
            issues = jira.search_issues(jql_query)
            logging.debug(f"{len(issues)} tarefas encontradas no sprint ativo.")

            tasks_by_person = {}
            for issue in issues:
                assignee = issue.fields.assignee.displayName if issue.fields.assignee else 'Não Atribuído'
                issue_key = issue.key
                issue_summary = issue.fields.summary
                status = issue.fields.status.name
                start_date = issue.fields.created[:10] 
                due_date = issue.fields.duedate if issue.fields.duedate else 'Sem data de conclusão'

                task_details = {
                    'key': issue_key,
                    'summary': issue_summary,
                    'status': status,
                    'start_date': format_date(start_date),
                    'due_date': format_date(due_date),
                    'overdue': is_overdue(due_date),
                    'comments': [],
                    'impediments': []
                }

                logging.debug(f"Processando tarefa {issue_key} para {assignee}.")

                comments = jira.comments(issue)
                for comment in comments:
                    comment_body = clean_comment(comment.body)
                    if "impedimento" in comment_body.lower():
                        task_details['impediments'].append(comment_body)
                    else:
                        task_details['comments'].append(comment_body)

                if assignee not in tasks_by_person:
                    tasks_by_person[assignee] = {'completed': [], 'in_progress': [], 'next_tasks': []}

                if status.lower() in ['done', 'concluído']:  
                    tasks_by_person[assignee]['completed'].append(task_details)
                elif status.lower() in ['in progress', 'em andamento']:  
                    tasks_by_person[assignee]['in_progress'].append(task_details)
                else:
                    tasks_by_person[assignee]['next_tasks'].append(task_details)

            header_content = (
                f"# Relatório Diário: {sprint_name} ({sprint_start_date} - {sprint_end_date})\n"
            )
            header_messages = split_message(header_content)
            for msg in header_messages:
                data = {'content': msg}
                response = requests.post(webhook_url, json=data)
                logging.info(f"Mensagem de cabeçalho enviada. Status Code: {response.status_code}")

            for person, task_info in tasks_by_person.items():
                base_content = (
                    f"# Nome: {person}\n\n"
                    f"## Tarefas Em Andamento:\n"
                )

                if task_info['in_progress']:
                    for task in task_info['in_progress']:
                        comments_summary = summarize_text('\n'.join(task['comments']))
                        impediments_summary = summarize_text('\n'.join(task['impediments']))
                        overdue_status = "Sim" if task['overdue'] else "Não"
                        base_content += (
                            f"* {task['key']}: {task['summary']}\n"
                            f"  * Data de Início: {task['start_date']}\n"
                            f"  * Data de Conclusão: {task['due_date']}\n"
                            f"  * Atrasado: {overdue_status}\n"
                            f"  * Comentários: {comments_summary if comments_summary else 'Nenhum comentário.'}\n"
                            f"  * Impedimentos: {impediments_summary if impediments_summary else 'Nenhum impedimento.'}\n\n"
                        )
                else:
                    base_content += "  - Nenhuma tarefa em andamento.\n\n"

                base_content += "## Tarefas Concluídas Hoje:\n"
                if task_info['completed']:
                    for task in task_info['completed']:
                        comments_summary = summarize_text('\n'.join(task['comments']))
                        impediments_summary = summarize_text('\n'.join(task['impediments']))
                        overdue_status = "Sim" if task['overdue'] else "Não"
                        base_content += (
                            f"* {task['key']}: {task['summary']}\n"
                            f"  * Data de Início: {task['start_date']}\n"
                            f"  * Data de Conclusão: {task['due_date']}\n"
                            f"  * Atrasado: {overdue_status}\n"
                            f"  * Comentários: {comments_summary if comments_summary else 'Nenhum comentário.'}\n"
                            f"  * Impedimentos: {impediments_summary if impediments_summary else 'Nenhum impedimento.'}\n\n"
                        )
                else:
                    base_content += "  - Nenhuma tarefa concluída hoje.\n"

                base_content += "## Próximas Tarefas:\n"
                if task_info['next_tasks']:
                    for task in task_info['next_tasks']:
                        base_content += f"* {task['key']}: {task['summary']}\n"
                else:
                    base_content += "  - Nenhuma próxima tarefa identificada.\n"

                messages = split_message(base_content)

                for msg in messages:
                    data = {'content': msg}
                    response = requests.post(webhook_url, json=data)
                    logging.info(f"Mensagem enviada para {person}. Status Code: {response.status_code}")

                logging.debug(f"Relatório de {person} processado.\n" + "-"*50)

    except Exception as e:
        logging.error(f"Ocorreu um erro ao processar o board {board_id}: {e}")

def main():
    try:
        logging.info("Iniciando processo principal.")
        boards = jira.boards()
        logging.info(f"{len(boards)} boards encontrados.")

        for board in boards:
            process_board(board.id)

    except Exception as e:
        logging.error(f"Ocorreu um erro ao buscar boards: {e}")

if __name__ == "__main__":
    main()
