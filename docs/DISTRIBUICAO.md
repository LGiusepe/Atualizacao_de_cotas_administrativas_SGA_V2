# Distribuição como programa (.exe) — sem compartilhar o código

Este guia explica como gerar uma pasta pronta para distribuir, com o
programa já empacotado (`.exe`), para quem vai usar no dia a dia sem
precisar instalar Python, sem clonar o repositório e sem ver o
código-fonte — como qualquer programa baixado da internet.

## Resumo do que muda

| | Rodando do código-fonte (`run.bat`) | Rodando o `.exe` empacotado |
|---|---|---|
| Precisa de Python instalado? | Sim | Não |
| A pessoa vê os arquivos `.py`? | Sim | Não (ficam dentro do `.exe`) |
| Como se distribui? | Compartilhando a pasta/repositório inteiro | Compartilhando **uma pasta** com o `.exe` |
| Precisa de internet para instalar dependências? | Sim, na primeira vez (`pip install`) | Não — já vem tudo embutido |

Importante: empacotar com PyInstaller (a ferramenta usada aqui) embute o
código dentro do `.exe`, mas não é uma proteção contra engenharia reversa
séria — alguém com ferramentas específicas ainda conseguiria extrair uma
versão aproximada do código. Para o uso interno da empresa (impedir que o
código circule casualmente por e-mail/pen-drive, e dar uma experiência de
"instalar um programa" para quem não é técnico), isso é mais do que
suficiente.

## 1. Gerar o pacote (só quem desenvolve precisa fazer isso)

Na pasta do projeto, dê duplo clique em **`build_exe.bat`**. Ele:

1. Cria/reaproveita o ambiente virtual (`.venv`) e instala as dependências
   do projeto (`requirements.txt`).
2. Instala o PyInstaller (a ferramenta que gera o `.exe`).
3. Empacota `src/gui.py` — junto com a logo (`assets/`) e tudo que o
   programa precisa para rodar — num único executável.
4. Monta uma pasta pronta para distribuir.

Ao final, o resultado fica em:

```
dist\AtualizacaoDeCotas\
    AtualizacaoDeCotas.exe   <- o programa
    .env.example             <- modelo em branco para login automático opcional
    LEIA-ME.txt              <- instruções rápidas para quem for usar
```

O `.env.example` incluído aqui é só um **modelo com campos em branco**
(`HINOVA_USUARIO=SEU_USUARIO_AQUI`) — nada de credenciais reais é
empacotado. Cada pessoa que for usar copia esse arquivo, renomeia para
`.env` e preenche com as próprias credenciais na própria máquina, se
quiser tentar o login automático (é opcional; sem isso, o login é sempre
manual).

Isso pode levar alguns minutos na primeira vez. Rodar de novo (depois de
alterar o código) é só dar duplo clique em `build_exe.bat` outra vez — ele
sempre reconstrói a pasta inteira a partir do código atual.

## 2. Testar antes de distribuir

Copie a pasta `dist\AtualizacaoDeCotas\` inteira para outro lugar **fora**
da pasta do projeto (ex.: a Área de Trabalho) e dê duplo clique no `.exe`
de lá. Confirme que:

- A janela abre normalmente, com a logo aparecendo.
- Selecionar uma planilha e rodar PT1/PT2 funciona (login manual ou
  automático, pausar/parar, etc. — tudo deve se comportar igual ao rodar
  pelo `run.bat`).
- Depois de rodar, aparecem ao lado do `.exe` uma pasta `logs/`, uma pasta
  `chrome_profile/` e um `config.local.json` — é aqui que o programa guarda
  os dados dessa instalação (histórico, progresso salvo, cookies de sessão,
  último caminho de planilha usado). Isso é esperado: o `.exe` sempre lê e
  escreve esses dados na pasta onde ELE está, nunca dentro de si mesmo.
- Se testar o login automático: copie `.env.example` para `.env` nessa
  mesma pasta de teste e preencha com credenciais reais só para o teste —
  depois apague esse `.env` de teste antes de distribuir (não deixe suas
  credenciais dentro da pasta que vai ser compartilhada).

## 3. Distribuir

**Não** coloque o `.exe` (nem a pasta) dentro do repositório Git (arquivos
binários grandes não devem ir para o histórico do Git, e mudam a cada
build). Em vez disso, use uma **Release do GitHub**:

1. Compacte a pasta `dist\AtualizacaoDeCotas\` inteira num `.zip` (clique
   com o botão direito nela → "Enviar para" → "Pasta compactada").
2. No GitHub, vá em **Releases** → **Draft a new release**.
3. Escolha uma tag (ex.: `v1.0.0`) e escreva uma descrição curta do que
   mudou.
4. Em **Attach binaries**, anexe o `.zip` que você acabou de criar.
5. Publique a release.

Quem for usar o programa baixa o `.zip` direto da página da Release,
extrai numa pasta própria (ex.: `Atualização de Cotas` na área de
trabalho) e dá duplo clique no `.exe` de dentro — nunca precisa clonar o
repositório nem ver uma linha de código.

Alternativas mais simples (sem GitHub) para o dia a dia interno: enviar o
`.zip` por e-mail, ou deixar numa pasta compartilhada (ex.: o próprio
OneDrive da empresa) para quem precisar baixar.

## 4. Quando gerar um novo pacote

Sempre que o código em `src/` mudar (nova funcionalidade, correção de bug),
rode `build_exe.bat` de novo e publique uma nova Release com um número de
versão maior (ex.: `v1.1.0`). Quem já tem o pacote antigo continua
funcionando, mas não recebe a atualização automaticamente — é preciso
baixar o novo `.zip`.

## Observações técnicas

- O `.exe` precisa do **Google Chrome instalado** na máquina de quem vai
  rodar (o programa controla o Chrome já instalado — ele não vem embutido
  no `.exe`). O driver do Chrome (chromedriver) é baixado automaticamente
  pelo Selenium na primeira execução — por isso a máquina precisa de
  internet no primeiro uso.
- O build empacota **só a interface gráfica** (`gui.py`). A versão de
  linha de comando (`atualizar_cotas.py`) continua existindo apenas para
  quem roda a partir do código-fonte.
- Se aparecer um erro do tipo `ModuleNotFoundError` ao rodar o `.exe` (uma
  biblioteca que o PyInstaller não detectou sozinho), adicione
  `--collect-all NOME_DA_BIBLIOTECA` na linha do `pyinstaller` dentro de
  `build_exe.bat` e gere de novo.
