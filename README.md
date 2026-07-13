# Atualização de Cotas — Hinova

Automação da atualização de "Cotas de Participação de Veículos" no sistema
Hinova (Grupo GolPlus), a partir das planilhas PT1 e PT2.

## Para rodar

Dê **duplo clique em `run.bat`** nesta pasta. Ele abre a interface gráfica
e guia o resto.

Durante a execução, os botões **Pausar** e **Parar** ficam disponíveis na
janela. Pausar espera terminar a linha/planilha atual antes de parar; Parar
interrompe de vez — o que já foi processado até aquele momento é salvo
mesmo assim na pasta de logs.

## Estrutura da pasta

- **`run.bat`** — clique aqui para começar.
- **`.env.example`** — modelo de credenciais opcionais (copie para `.env`
  e preencha localmente; o `.env` real nunca é versionado).
- **`requirements.txt`** — dependências Python (instaladas automaticamente
  pelo `run.bat`).
- **`src/`** — código da automação (`gui.py`, `automacao_core.py`,
  `atualizar_cotas.py`).
- **`docs/`** — documentação:
  - `RUNBOOK.md` — passo a passo completo de execução (comece por aqui).
  - `POWER_AUTOMATE_MIGRATION.md` — guia opcional de migração futura.
  - `Documentacao_Atualizacao_Cotas.pdf` / `.docx` — versão para
    compartilhar/imprimir com o mesmo conteúdo do RUNBOOK. Esses dois
    arquivos ficam só na máquina local (não são versionados no
    repositório — veja `.gitignore`).
- **`logs/`** e **`chrome_profile/`** — criadas automaticamente na primeira
  execução (resultados e perfil de navegador persistente). Também não são
  versionadas: `chrome_profile/` guarda cookies de sessão reais e nunca
  deve ir para um repositório, ainda mais um público.

## Leia primeiro

Antes de rodar por conta própria, veja **`docs/RUNBOOK.md`** — explica o
fluxo completo, inclusive a parte de login (que pode pedir código de
autenticação e captcha; o código cliente é fixo por link e já vem
preenchido automaticamente).

## Segurança

Este repositório não deve nunca conter: o arquivo `.env` (credenciais
reais), a pasta `chrome_profile/` (cookies de sessão) ou a pasta `logs/`
(dados de execução). Tudo isso já está listado no `.gitignore`. Se algum
desses itens aparecer em `git status` como pronto para commit, **não
prossiga** — confira o `.gitignore` antes de continuar.
