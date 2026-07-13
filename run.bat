@echo off
REM ============================================================
REM  run.bat - abre a interface de atualizacao de cotas
REM ============================================================
cd /d "%~dp0"

if not exist ".env" (
    echo [AVISO] Arquivo .env nao encontrado.
    echo Isso e opcional - sem ele, o login e sempre manual.
    echo Se quiser tentar o login automatico, copie ".env.example" para
    echo ".env" e preencha usuario/senha antes de continuar.
    echo.
)

if not exist ".venv" (
    echo Criando ambiente virtual pela primeira vez...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando/atualizando dependencias...
pip install -r requirements.txt -q

python src\gui.py
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao iniciar a interface. Veja a mensagem acima.
    pause
)
