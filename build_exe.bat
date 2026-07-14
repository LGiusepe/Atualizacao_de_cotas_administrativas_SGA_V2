@echo off
REM ============================================================
REM  build_exe.bat - gera um executavel (.exe) unico e distribuivel
REM  do programa, sem expor o codigo-fonte Python.
REM
REM  Ao final, cria uma PASTA pronta para distribuir em:
REM    dist\AtualizacaoDeCotas\
REM  contendo:
REM    - AtualizacaoDeCotas.exe   (o programa)
REM    - .env.example             (modelo para login automatico opcional)
REM    - LEIA-ME.txt              (instrucoes rapidas para quem for usar)
REM
REM  IMPORTANTE: o .env.example aqui e so um MODELO com campos em branco -
REM  nunca coloque um .env de verdade (com usuario/senha reais) dentro
REM  dessa pasta antes de distribuir. Cada pessoa preenche o dela por
REM  conta propria, na maquina dela.
REM
REM  Distribua essa PASTA inteira (ex.: compactando em .zip e anexando
REM  numa Release do GitHub). Veja docs\DISTRIBUICAO.md para o passo a
REM  passo completo.
REM ============================================================
cd /d "%~dp0"

if not exist ".venv" (
    echo Criando ambiente virtual pela primeira vez...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando dependencias do projeto...
pip install -r requirements.txt -q

echo Instalando o PyInstaller (ferramenta de empacotamento)...
pip install pyinstaller -q

echo.
echo Gerando o executavel (isso pode levar alguns minutos)...
pyinstaller --noconfirm --onefile --windowed --name AtualizacaoDeCotas ^
    --add-data "assets;assets" ^
    --collect-all pandas ^
    src\gui.py

if not exist "dist\AtualizacaoDeCotas.exe" (
    echo.
    echo Algo deu errado - o .exe nao foi gerado. Veja as mensagens acima.
    pause
    exit /b 1
)

echo.
echo Montando a pasta de distribuicao...
set "PASTA_DIST=dist\AtualizacaoDeCotas"
if exist "%PASTA_DIST%" rd /s /q "%PASTA_DIST%"
mkdir "%PASTA_DIST%"
move /y "dist\AtualizacaoDeCotas.exe" "%PASTA_DIST%\AtualizacaoDeCotas.exe" >nul
copy /y ".env.example" "%PASTA_DIST%\.env.example" >nul

> "%PASTA_DIST%\LEIA-ME.txt" (
    echo Atualizacao de Cotas — Hinova
    echo ==============================
    echo.
    echo Para usar: de duplo clique em AtualizacaoDeCotas.exe
    echo Nao precisa instalar Python nem nada — e so isso mesmo.
    echo.
    echo Login automatico ^(opcional^):
    echo   1. Copie ".env.example" e renomeie a copia para ".env" ^(mesma pasta^).
    echo   2. Abra o ".env" num editor de texto simples ^(Bloco de Notas^) e
    echo      preencha HINOVA_USUARIO e HINOVA_SENHA com suas credenciais reais.
    echo   3. Isso so funciona de ponta a ponta se o reCAPTCHA estiver desativado
    echo      no painel administrativo. Sem ".env", ou se ainda pedir codigo de
    echo      autenticacao/captcha, complete o login manualmente na janela do
    echo      Chrome que abrir — o programa continua sozinho depois.
    echo.
    echo NUNCA compartilhe seu ".env" preenchido com mais ninguem — ele tem
    echo sua senha real.
)

echo.
echo Pronto! Distribua a pasta: %PASTA_DIST%
echo Teste-a antes de distribuir — veja docs\DISTRIBUICAO.md.
pause
