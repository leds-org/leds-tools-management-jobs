# Management Jobs

Conjunto de Jobs que buscam dados do JIRA para ajudar na reunião diária e no acompanhamento do sprint.

## Job: `job_daily_report`

O job `job_daliy_report` foi criado para gerar um relatório diário detalhado sobre a reunião diária (daily stand-up). Este job compila informações relevantes da daily, incluindo:

- Resumo das discussões
- Tarefas concluídas e pendentes
- Pontos de bloqueio identificados

Os dados gerados por este job são enviados automaticamente para um canal específico no Discord, mantendo todos os membros da equipe atualizados sobre o progresso diário e quaisquer desafios enfrentados.

## Job: `job_daily_clockify`

O job `job_daily_clockify` foi criado para gerar um relatório diário detalhado sobre as horas de cada desenvolvedor pro dia. Este job compila informações relevantes do projeto, incluindo:

- Horas trabalhadas por dia 
- Total de Horas trabalhadas

Os dados gerados por este job são enviados automaticamente para um canal específico no Discord, mantendo todos os membros da equipe atualizados sobre o progresso diário e quaisquer desafios enfrentados.



## Job: `job_resume_sprint`

O job `job_resume_sprint` foi desenvolvido para fornecer uma visão geral do sprint atual, com foco em métricas de progresso. Este job gera um resumo contendo:

- Percentual de tarefas concluídas
- Percentual de tarefas não concluídas
- Observações sobre o desempenho do sprint

Esses dados são também enviados para um canal dedicado no Discord, facilitando a análise do progresso do sprint e permitindo ajustes nas estratégias da equipe em tempo real.


## Job: `job_resume_project`

O job `job_resume_project` foi criado para gerar um relatório diário detalhado sobre status do projeto. Este job compila informações relevantes do projeto, incluindo:

- Velocidade da Equipe
- Trabalho Restante
- Data Estimada de Conclusão
- Número de Tarefas Concluídas
- Número de Tarefas Pendentes
- Número de Tarefas Não Realizadas
- Percentual Concluído

Os dados gerados por este job são enviados automaticamente para um canal específico no Discord, mantendo todos os membros da equipe atualizados sobre o progresso diário e quaisquer desafios enfrentados.

---

Esses jobs são parte de um sistema integrado para gerenciamento eficiente de projetos, proporcionando insights detalhados e atualizados sobre o desempenho da equipe e o andamento das tarefas diretamente no Discord.


## Configurando o JOB

Para configurar o JOB é necessário criar um aquivo .env com os seguintes dados:

JIRA_URL = 
JIRA_USERNAME = 
JIRA_API_TOKEN = 

# Configurar o Webhook do Discord
WEBHOOK_URL = 

CLOCKIFY_API_KEY = 
CLOCKIFY_WORKSPACE_ID = 
