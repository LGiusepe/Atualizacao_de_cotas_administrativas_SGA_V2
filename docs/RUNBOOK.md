# Runbook — Atualização de Cotas de Participação de Veículos

Processo de reajuste das cotas de veículos no sistema Hinova (Grupo GolPlus),
do recebimento do percentual pela diretoria até a atualização no sistema.
Feito para poder ser executado por qualquer pessoa da equipe, mesmo sem
conhecimento técnico.

## Estrutura da pasta da automação

```
AtualizaCotas/
├── run.bat                  <- duplo clique para começar
├── .env.example
├── requirements.txt
├── src/
│   ├── gui.py               <- interface gráfica
│   ├── automacao_core.py    <- motor da automação
│   └── atualizar_cotas.py   <- alternativa por linha de comando
├── docs/                    <- esta pasta (RUNBOOK, guia Power Automate, PDF/DOCX)
├── logs/                    <- criada automaticamente a cada execução
└── chrome_profile/          <- criada automaticamente (cookies entre execuções)
```

## Visão geral do fluxo

1. **Diretoria divulga o percentual** de reajuste no Teams.
2. **Atualização manual da planilha base** (`DEFINITIVO_COTAS ORIGINAL.xlsx`)
   com o novo percentual, e geração/atualização das subplanilhas:
   - `boot_pt1/DEFINITIVO_COTAS PT 1.xlsx`
   - `boot_pt2/DEFINITIVO_COTAS PT 2.xlsx`
   (essas planilhas continuam na pasta original do OneDrive — ver seção
   "Onde encontrar cada arquivo" mais abaixo.)
3. **Login no Hinova** — automático (se possível) ou manual (ver seção
   abaixo) — e **atualização automática** de cada cota via interface
   gráfica (`src/gui.py`, aberta pelo `run.bat`).
4. **Conferência** dos arquivos gerados em `logs/` (histórico de alterações e,
   se houver, itens que falharam).

Os passos 1 e 2 continuam manuais (dependem de decisão da diretoria e da
planilha já existente). O passo 3 é o que esta automação cobre.

> PT1 e PT2 são tratadas como planilhas independentes (cada uma com seu
> próprio "perfil" de busca no sistema, configurado em `src/automacao_core.py`).
> Se um dia a forma de busca de uma delas mudar no Hinova, ajuste apenas o
> perfil correspondente — não afeta a outra planilha.

## IMPORTANTE — a tela de login do Hinova mudou

A tela de login (`saturno.hinova.com.br/.../login.php`) passou a exigir,
além de usuário e senha: **Código cliente**, **Código de autenticação**
(um código que muda a cada login) e um **reCAPTCHA** ("Não sou um robô").
Isso foi identificado ao revisar uma gravação do processo antigo sendo
executado — o script anterior parava exatamente nessa tela.

O **Código cliente é fixo por link**: o próprio endereço de login já
identifica a conta/tenant, então esse campo vem preenchido automaticamente
pelo Hinova — não precisa ser digitado nem automatizado.

Já o código de autenticação (2FA) e o reCAPTCHA são diferentes: não é
possível, e não é correto, automatizar a resolução de captcha — isso existe
justamente para impedir automação. Por isso o programa funciona assim:

- Se o `.env` tiver `HINOVA_USUARIO`/`HINOVA_SENHA` **e** o reCAPTCHA
  estiver **desativado no painel administrativo** durante a execução
  (decisão de quem administra a conta Hinova — o programa não decide isso),
  o login tende a completar automaticamente.
- Caso contrário — captcha ativo, ou código de autenticação pendente — o
  Chrome abre na tela de login e **a pessoa completa manualmente** (usuário,
  senha, código de autenticação, marcar o captcha, clicar Entrar — o código
  cliente já estará preenchido). O programa detecta automaticamente quando
  o login foi concluído e segue sozinho com a atualização das cotas.

Ou seja: funciona nos dois cenários, só muda se alguém precisa digitar o
login na hora ou não.

## Pré-requisitos (uma única vez por computador)

- Windows com Python 3.10+ instalado (verifique com `python --version` no
  Prompt de Comando).
- Google Chrome instalado (a automação controla o Chrome diretamente).
- Acesso normal ao sistema Hinova com usuário e senha.

## Configuração inicial (uma única vez, opcional)

1. Na raiz da pasta da automação, copie o arquivo `.env.example` e renomeie
   a cópia para `.env`.
2. Abra o `.env` e preencha, se quiser tentar o login automático:
   ```
   HINOVA_USUARIO=seu_usuario
   HINOVA_SENHA=sua_senha
   ```
3. Não compartilhe esse arquivo `.env` — ele fica só no computador e não deve
   ser enviado por e-mail, Teams ou subido para nenhum repositório.
4. Se preferir sempre fazer login manual (mais simples, sem guardar senha em
   arquivo nenhum), pode pular esta seção — o programa funciona sem `.env`.

> **Atenção de segurança:** os notebooks antigos (`_webscraping_rateio.ipynb`
> e `webscraping_beta.ipynb`) tinham a senha do Hinova escrita diretamente no
> código. Considere trocar essa senha, já que ela ficou exposta em texto
> puro nesses arquivos.

## Rodando o processo (a cada reajuste) — para quem não é técnico

1. Confirme que a diretoria já divulgou o percentual no Teams.
2. Confirme que as planilhas finais de PT1 e PT2 já estão prontas e reajustadas.
3. Dê **duplo clique em `run.bat`** (na raiz da pasta da automação).
   - Na primeira vez, ele demora um pouco mais (instala tudo automaticamente).
   - Depois disso, abre direto uma janela chamada **"Atualização de Cotas —
     Hinova"**.
4. Na janela:
   - Confira se os caminhos de PT1 e PT2 estão certos. Se precisar usar
     outro arquivo, clique em **"Selecionar arquivo..."** na seção
     correspondente.
   - Clique em **"Iniciar PT1 + PT2"** para rodar as duas, ou em
     **"Rodar só PT1"/"Rodar só PT2"** para rodar uma de cada vez.
   - Confirme a mensagem de aviso que aparece.
5. O Chrome abre. Se o login não completar sozinho, **complete manualmente**
   (usuário, senha, código de autenticação, captcha, Entrar — o código
   cliente já vem preenchido). O programa aguarda e detecta automaticamente
   quando terminar.
6. Depois do login, o processamento das cotas é automático — acompanhe o
   progresso e o log dentro da própria janela do programa.
7. Ao final, aparece um resumo (quantas cotas foram atualizadas e quantas
   falharam). Clique em **"Abrir pasta de logs"** para ver os detalhes:
   - `execucao_<data_hora>.log` — log completo da execução.
   - `historico_atualizacoes_<data_hora>.xlsx` — todas as cotas alteradas
     com sucesso (valor antigo x novo valor, com a coluna "planilha"
     indicando se veio de PT1 ou PT2).
   - `itens_para_reprocessar_<data_hora>.xlsx` — só aparece se algum item
     falhou. Nesse caso, avise o responsável ou rode novamente.

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Chrome fica parado na tela de login | reCAPTCHA ativo e/ou código de autenticação pendente | Complete o login manualmente na janela; o programa detecta e segue sozinho |
| "Tempo esgotado aguardando o login manual" | Login não foi concluído em 10 minutos | Rode de novo e complete o login mais rapidamente |
| Login automático não preenche nada | `.env` não existe ou está vazio | Normal — nesse caso o login é sempre manual. Preencha o `.env` se quiser tentar o automático |
| Muitos itens em "itens_para_reprocessar" | Código da planilha não bate com o cadastrado no sistema | Confirme os códigos na planilha base antes de gerar PT1/PT2 |
| Processo trava no meio (depois do login) | Internet instável ou sistema Hinova lento | Pode rodar de novo — o programa salva o progresso e continua automaticamente de onde parou, sem reprocessar o que já foi feito |
| Janela do programa não abre ao dar duplo clique em run.bat | Python não instalado, ou Tkinter ausente na instalação | Instale o Python oficial (python.org), marcando a opção "tcl/tk" durante a instalação |

## Onde encontrar cada arquivo

**Automação** (a pasta onde este projeto foi instalado):

- `run.bat` — launcher de um clique (na raiz).
- `.env.example` / `requirements.txt` — configuração (na raiz).
- `src/gui.py` — interface gráfica (uso recomendado no dia a dia).
- `src/automacao_core.py` — motor da automação (login, busca, atualização),
  com os "perfis" de PT1 e PT2 configuráveis separadamente.
- `src/atualizar_cotas.py` — versão alternativa por linha de comando.
- `docs/` — esta documentação, incluindo PDF/DOCX para compartilhar.
- `logs/` e `chrome_profile/` — criadas automaticamente na raiz.

**Planilhas PT1/PT2**: não ficam num caminho fixo dentro do programa — você
escolhe o arquivo pelo botão "Selecionar arquivo..." na interface. O último
caminho escolhido de cada uma fica lembrado localmente (em
`config.local.json`, que não é compartilhado nem vai para o repositório),
então nas próximas execuções o campo já vem preenchido sozinho.

## Próximo passo (opcional): Power Automate Desktop

A empresa já tem ambiente Microsoft 365 Standard e 1 licença Power Automate
Premium. Essa automação em Python/Selenium funciona hoje e não depende de
licenciamento adicional, mas pode ser reconstruída no Power Automate Desktop
para ficar mais "oficial"/integrada ao ecossistema 365 (Teams, SharePoint,
histórico de execução no portal). Veja `POWER_AUTOMATE_MIGRATION.md` para o
passo a passo — incluindo a mesma limitação de captcha/2FA descrita aqui, que
vale para qualquer ferramenta de automação, não só para este script.
Recomenda-se manter as duas versões rodando em paralelo por um tempo antes
de aposentar a versão em Python.
