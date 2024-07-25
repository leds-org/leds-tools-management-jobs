from jira import JIRA
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import os
# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


jira_url = os.getenv('JIRA_URL')
jira_username = os.getenv('JIRA_USERNAME')
jira_api_token = os.getenv('JIRA_API_TOKEN')
webhook_url = os.getenv('WEBHOOK_URL')

# Conectar ao Jira
jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})

def get_all_projects():
    return jira.projects()

def analyze_performance_for_project(project_key):
    jql_query = f'project = {project_key} AND (status = "Done" OR status = "In Progress")'
    
    issues = jira.search_issues(jql_query, maxResults=1000)
    
    tasks_by_developer = defaultdict(lambda: defaultdict(list))
    total_tasks = 0
    completed_tasks = 0
    total_time = 0
    
    for issue in issues:
        fields = issue.fields
        sprint_name = fields.customfield_10007[0].name if fields.customfield_10007 else 'No Sprint'
        assignee = fields.assignee.displayName if fields.assignee else 'Unassigned'
        
        tasks_by_developer[assignee][sprint_name].append(issue)
        
        total_tasks += 1
        
        if fields.status.name == 'Done':
            completed_tasks += 1
            if fields.resolutiondate and fields.created:
                created_date = datetime.strptime(fields.created[:10], '%Y-%m-%d')
                resolved_date = datetime.strptime(fields.resolutiondate[:10], '%Y-%m-%d')
                total_time += (resolved_date - created_date).days
    
    avg_completion_time = total_time / completed_tasks if completed_tasks else 0
    
    print(f"\nAnálise do Projeto: {project_key}")
    print(f"Total de Tarefas: {total_tasks}")
    print(f"Tarefas Concluídas: {completed_tasks}")
    print(f"Tempo Médio para Concluir Tarefas: {avg_completion_time:.2f} dias")
    
    print("\nPerformance por Desenvolvedor:")
    for developer, sprints in tasks_by_developer.items():
        print(f"\nDesenvolvedor: {developer}")
        for sprint, tasks in sprints.items():
            print(f"{sprint}: {len(tasks)} tarefas")

def main():
    projects = get_all_projects()
    
    for project in projects:
        project_key = project.key
        analyze_performance_for_project(project_key)

if __name__ == "__main__":
    main()
