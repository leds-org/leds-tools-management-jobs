import pandas as pd
import matplotlib.pyplot as plt
from jira import JIRA
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io
import base64
import logging
import os
from pprint import pprint
# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para buscar todos os sprints de um board
def get_board_sprints(jira, board_id):
    logging.info(f"Buscando sprints para o board {board_id}...")
    sprints = jira.sprints(board_id, state='active,future,closed')
    logging.info(f"Encontrados {len(sprints)} sprints para o board {board_id}.")
    return sprints

# Função para buscar todos os boards e sprints
def get_all_sprints(jira):
    logging.info("Buscando todos os boards no Jira...")
    boards = jira.boards()
    all_sprints = []
    
    for board in boards:
        sprints = get_board_sprints(jira, board.id)
        for sprint in sprints:
            all_sprints.append({
                'board': board,
                'sprint': sprint
            })
    
    logging.info(f"Total de sprints encontrados: {len(all_sprints)}.")
    return all_sprints

# Função para buscar a performance de um sprint específico
def get_sprint_performance(jira, sprint_id):
    logging.info(f"Buscando performance para o sprint {sprint_id}...")
    issues = jira.search_issues(f'sprint = {sprint_id}', maxResults=False)
    completed = sum(1 for issue in issues if issue.fields.status.name == 'Done')
    total = len(issues)
    logging.info(f"Performance do sprint {sprint_id}: {completed}/{total} tarefas concluídas.")
    return completed, total

# Função para obter os e-mails dos desenvolvedores a partir das issues
def get_developer_emails(jira, issues):
    logging.info("Extraindo e-mails dos desenvolvedores das issues...")
    emails = {}
    for issue in issues:
        assignee = issue.fields.assignee
        if assignee:
            user_key = assignee.accountId            
            try:
                email = user_key+'@gmail.com'
                user = jira.user(user_key)
                pprint (user.__dict__)
#                email = user.emailAddress if hasattr(user, 'emailAddress') else None
                if email:
                    if email not in emails:
                        emails[email] = []
                    emails[email].append(issue)
            except Exception as e:
                logging.error(f"Erro ao buscar informações do usuário {user_key}: {e}")
    logging.info(f"E-mails extraídos: {list(emails.keys())}")
    return emails

# Função para criar uma mensagem personalizada com base na evolução
def create_personalized_message(df):
    last_two_sprints = df.tail(2)
    if len(last_two_sprints) < 2:
        return "Mantenha o bom trabalho e continue evoluindo!"
    
    previous_percent = last_two_sprints.iloc[0]['Percentual']
    current_percent = last_two_sprints.iloc[1]['Percentual']

    if current_percent > previous_percent:
        return "Parabéns pela evolução! Continue assim!"
    else:
        return "Notei que a sua performance não evoluiu neste sprint. Vamos conversar com a equipe para entender melhor e ajudar você a melhorar."

# Função para enviar e-mails individualmente
def send_email(from_email, to_email, subject, html_body):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    logging.info(f"Enviando e-mail para {to_email}...")
    server = smtplib.SMTP('smtp.seu_provedor.com', 587)
    server.starttls()
    server.login(from_email, 'sua_senha_de_email')
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()
    logging.info(f"E-mail enviado para {to_email} com sucesso.")

# Função principal
def main():
    # Configurações do Jira
    jira_url = os.getenv('JIRA_URL')
    jira_username = os.getenv('JIRA_USERNAME')
    jira_api_token = os.getenv('JIRA_API_TOKEN')
    logging.info("Conectando ao Jira...")
    jira = JIRA(basic_auth=(jira_username, jira_api_token), options={'server': jira_url})
    logging.info("Conexão com Jira estabelecida.")

    # Buscar todos os sprints
    all_sprints = get_all_sprints(jira)
    performance_data = []
    all_emails = {}

    for item in all_sprints:
        board = item['board']
        sprint = item['sprint']
        completed, total = get_sprint_performance(jira, sprint.id)
        performance_data.append((board.name, sprint.name, completed, total))
        issues = jira.search_issues(f'sprint = {sprint.id}', maxResults=False)
        sprint_emails = get_developer_emails(jira, issues)
        for email, user_issues in sprint_emails.items():
            if email not in all_emails:
                all_emails[email] = []
            all_emails[email].extend(user_issues)

    # Criando um DataFrame com os dados
    logging.info("Criando DataFrame com os dados coletados...")
    df = pd.DataFrame(performance_data, columns=["Board", "Sprint", "Concluídas", "Total"])
    df["Percentual"] = (df["Concluídas"] / df["Total"]) * 100

    # Gerando o gráfico de linha
    logging.info("Gerando gráfico de linha da performance...")
    plt.figure(figsize=(10, 6))
    for board_name in df['Board'].unique():
        board_data = df[df['Board'] == board_name]
        plt.plot(board_data['Sprint'], board_data['Percentual'], marker='o', linestyle='-', label=board_name)

    plt.title('Evolução da Performance por Board')
    plt.xlabel('Sprint')
    plt.ylabel('Percentual de Conclusão (%)')
    plt.ylim(0, 100)
    plt.legend(title='Board')

    # Salvar o gráfico em um buffer de memória
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    # Criar uma mensagem motivacional
    motivational_message = "O sucesso é a soma de pequenos esforços repetidos dia após dia."

    # Preparar e enviar e-mails individualmente
    logging.info("Preparando e enviando e-mails individualmente...")
    from_email = "seu_email@example.com"

    for email, user_issues in all_emails.items():
        user_df = df[df['Sprint'].isin([issue.fields.sprint.name for issue in user_issues])]
        personalized_message = create_personalized_message(user_df)

        html_body = f"""
        <html>
        <body>
            <p>Olá,</p>
            <p>Aqui está a comparação de sua performance nos últimos sprints:</p>
            
            {user_df.to_html(index=False)}

            <p>Veja abaixo a evolução da sua performance ao longo dos sprints:</p>
            <img src="data:image/png;base64,{image_base64}">
            
            <p>{motivational_message}</p>
            <p>{personalized_message}</p>
            
            <p>Vamos continuar melhorando!</p>
            <p>Atenciosamente,<br>Equipe de Gestão</p>
        </body>
        </html>
        """
        print(html_body)  # Imprimir o HTML para debug, removido ou substituído na produção
        #send_email(from_email, email, "Comparativo de Performance nos Sprints", html_body)

    logging.info("Todos os e-mails foram enviados com sucesso!")

# Executar a função principal
if __name__ == "__main__":
    main()
