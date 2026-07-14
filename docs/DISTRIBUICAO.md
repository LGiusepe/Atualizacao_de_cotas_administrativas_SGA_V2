# Distribuição como programa (.exe) — sem compartilhar o código

Este guia explica como gerar um único arquivo `.exe` do programa, para
distribuir para quem vai usar no dia a dia sem precisar instalar Python,
sem clonar o repositório e sem ver o código-fonte — como qualquer programa
baixado da internet.

## Resumo do que muda

| | Rodando do código-fonte (`run.bat`) | Rodando o `.exe` empacotado |
|---|---|---|
| Precisa de Python instalado? | Sim | Não |
| A pessoa vê os arquivos `.py`? | Sim | Não (ficam dentro do `.exe`) |
| Como se distribui? | Compartilhando a pasta/repositório inteiro | Compartilhando **um arquivo** (`AtualizacaoDeCotas.exe`) |
| Precisa de internet para instalar dependências? | Sim, na primeira vez (`pip install`) | Não — já vem tudo embutido |

Importante: empacotar com PyInstaller (a ferramenta usada aqui) embute o
código dentro do `.exe`, mas não é uma proteção contra engenharia reversa
séria — alguém com ferramentas específicas ainda conseguiria extrair uma
versão aproximada do código. Para o uso interno da empresa (impedir que o
código circule casualmente por e-mail/pen-drive, e dar uma experiência de
"instalar um programa" para quem não é técnico), isso é mais do que
suficiente.

## 1. Gerar o `.exe` (só quem desenvolve precisa fazer isso)

Na pasta do projeto, dê duplo clique em **`build_exe.bat`**. Ele:

1. Cria/reaproveita o ambiente virtual (`.venv`) e instala as dependências
   do projeto (`requirements.txt`).
2. Instala o PyInstaller (a ferramenta que gera o `.exe`).
3. Empacota `src/gui.py` — junto com a logo (`assets/`) e tudo que o
   programa precisa para rodar — num único arquivo.

Ao final, o executável fica em:

```
dist\AtualizacaoDeCotas.exe
```

Isso pode levar alguns minutos na primeira vez. Rodar de novo (depois de
alterar o código) é só dar duplo clique em `build_exe.bat` outra vez — ele
sempre gera um `.exe` novo a partir do código atual.

## 2. Testar antes de distribuir

Copie `dist\AtualizacaoDeCotas.exe` para uma pasta **separada** (fora da
pasta do projeto) e dê duplo clique nele. Confirme que:

- A janela abre normalmente, com a logo aparecendo.
- Selecionar uma planilha e rodar PT1/PT2 funciona (login manual ou
  automático, pausar/parar, etc. — tudo deve se comportar igual ao rodar
  pelo `run.bat`).
- Depois de rodar, aparecem ao lado do `.exe` uma pasta `logs/`, uma pasta
  `chrome_profile/` e um `config.local.json` — é aqui que o programa guarda
  os dados dessa instalação (histórico, progresso salvo, cookies de sessão,
  último caminho de planilha usado). Isso é esperado: o `.exe` sempre lê e
  escreve esses dados na pasta onde ELE está, nunca dentro de si mesmo.

Se quiser habilitar o login automático nessa instalação, coloque um
arquivo `.env` (baseado em `.env.example`) na mesma pasta do `.exe`, com
`HINOVA_USUARIO` e `HINOVA_SENHA`. Isso é opcional — sem ele, o login é
sempre manual.

## 3. Distribuir

**Não** coloque o `.exe` dentro do repositório Git (arquivos binários
grandes não devem ir para o histórico do Git, e o `.exe` muda a cada
build). Em vez disso, use uma **Release do GitHub**:

1. No GitHub, vá em **Releases** → **Draft a new release**.
2. Escolha uma tag (ex.: `v1.0.0`) e escreva uma descrição curta do que
   mudou.
3. Em **Attach binaries**, anexe `dist\AtualizacaoDeCotas.exe`.
4. Publique a release.

Quem for usar o programa baixa o `.exe` direto da página da Release —
nunca precisa clonar o repositório nem ver uma linha de código. Basta
colocar o arquivo numa pasta própria (ex.: `Atualização de Cotas` na área
de trabalho) e dar duplo clique.

Alternativas mais simples (sem GitHub) para o dia a dia interno: enviar o
`.exe` por e-mail, ou deixar numa pasta compartilhada (ex.: o próprio
OneDrive da empresa) para quem precisar baixar.

## 4. Quando gerar um novo `.exe`

Sempre que o código em `src/` mudar (nova funcionalidade, correção de bug),
rode `build_exe.bat` de novo e publique uma nova Release com um número de
versão maior (ex.: `v1.1.0`). Quem já tem o `.exe` antigo continua
funcionando, mas não recebe a atualização automaticamente — é preciso
baixar o novo arquivo.

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
