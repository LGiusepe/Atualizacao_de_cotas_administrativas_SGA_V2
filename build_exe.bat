@echo off
REM ============================================================
REM  build_exe.bat - gera um executavel (.exe) unico e distribuivel
REM  do programa, sem expor o codigo-fonte Python.
REM
REM  Depois de rodar, o arquivo fica em:
REM    dist\AtualizacaoDeCotas.exe
REM
REM  Distribua esse UM arquivo (ex.: anexado numa Release do GitHub,
REM  por e-mail ou pasta compartilhada). Quem for usar so precisa dar
REM  duplo clique nele - nao precisa ter Python instalado, nem ver
REM  uma linha de codigo. Veja docs\DISTRIBUICAO.md para o passo a
REM  passo completo (build, teste e publicacao).
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

echo.
if exist "dist\AtualizacaoDeCotas.exe" (
    echo Pronto! O executavel esta em: dist\AtualizacaoDeCotas.exe
    echo Teste-o antes de distribuir - veja docs\DISTRIBUICAO.md.
) else (
    echo Algo deu errado - o .exe nao foi gerado. Veja as mensagens acima.
)
pause
