"""
automacao_core.py

Motor da automação de atualização de "Cotas de Participação de Veículos" no
sistema Hinova (Grupo GolPlus). Este módulo NÃO deve ser executado
diretamente pelo usuário final — ele é importado por:
  - gui.py                (interface gráfica, recomendada no dia a dia)
  - atualizar_cotas.py    (versão de linha de comando, alternativa)

Login: automático quando possível, manual como garantia
----------------------------------------------------------
A tela de login do Hinova passou a exigir "Código de autenticação" (2FA) e
um reCAPTCHA ("Não sou um robô"), além de usuário e senha. O "Código
cliente" também aparece na tela, mas é fixo por link — o próprio endereço
de login (LOGIN_URL, abaixo) já identifica a conta/tenant, então esse campo
vem preenchido automaticamente pelo Hinova e não precisa de nenhuma ação
aqui.

Se o reCAPTCHA estiver desativado no painel administrativo durante a
execução (decisão de quem administra a conta, não algo que este script
decide), o login pode ser automático — o script tenta preencher
usuário/senha e clicar em Entrar. Se ainda aparecer o código de autenticação
ou o captcha (reCAPTCHA ligado, ou 2FA obrigatório independente dele), o
script espera a pessoa completar esse passo manualmente na janela do Chrome
e detecta automaticamente quando o login foi concluído. Nunca tentamos
resolver o captcha programaticamente — isso não é automatizável de forma
legítima.

Conceito de "perfil de planilha"
--------------------------------
PT1 e PT2 têm particularidades na forma de busca dentro do sistema Hinova,
espelhando o desenvolvimento original de cada uma, mas ambas agora tentam
os dois campos de descrição antes de desistir de uma linha: PT1 tenta
primeiro "tipo_veiculo_cota" e cai para "descricao_cota"; PT2 tenta
primeiro "descricao_cota" e cai para "tipo_veiculo_cota". Cada perfil
descreve isso separadamente em PERFIS, abaixo.

Conferência do código antes de editar
--------------------------------------
Depois de encontrar uma linha na tabela do SGA, o código realmente exibido
nela é lido e comparado com o código que a planilha pedia para buscar. Se
não bater, a linha NÃO é editada (fica registrada como erro de divergência)
— isso evita repetir o problema de atualizar uma cota diferente da que
estava na planilha.

Resultados salvos mesmo com interrupção
----------------------------------------
historico_total/erros_total são preenchidos diretamente pelo
processar_planilha (em vez de criados e devolvidos por ele), e
salvar_resultados roda dentro de um "finally" em executar(). Isso garante
que a planilha de histórico/erros seja salva com o que já foi processado
até aquele ponto mesmo se a execução for interrompida (pelo botão "Parar"
na interface, Ctrl+C, fechamento do Chrome, erro inesperado etc.).

Pausar/Parar pela interface
----------------------------
ControleExecucao é um objeto simples e thread-safe (a automação roda numa
thread separada da janela) que a GUI usa para pedir pausa/retomada ou
parada. A checagem acontece em pontos seguros do loop — nunca no meio de
uma ação dentro do navegador.
"""

import os
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

# Este arquivo mora em .../AtualizaCotas/src/ — ROOT_DIR é a pasta acima
# (.../AtualizaCotas), onde ficam .env, logs/ e chrome_profile/, para que
# esses fiquem visíveis e fáceis de achar na raiz do projeto.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# As planilhas PT1/PT2 continuam guardadas na pasta original do OneDrive —
# aqui na pasta de automação usamos apenas um apontamento (caminho absoluto)
# para elas, sem duplicar/copiar os dados.
ONEDRIVE_DIR = (
    r"C:\Users\luigi.faria\OneDrive - Gol Plus Proteção Patrimonial"
    r"\Documentos\DESENVOLVIMENTOS\AtualizacaoDeCotas"
)

LOGIN_URL = "https://saturno.hinova.com.br/sga/sgav4_grupo_golplus/v5/login.php"
COTAS_URL = "https://saturno.hinova.com.br/sga/sgav4_grupo_golplus/v5/Cota/listar"

LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Perfil de navegador persistente: mantém cookies entre execuções para que o
# próprio Hinova possa "lembrar" o dispositivo (se ele oferecer isso),
# reduzindo com que frequência o código de autenticação/captcha aparece.
# Isso não contorna nada — só evita limpar cookies a cada execução, como um
# navegador normal que você não desloga.
CHROME_PROFILE_DIR = os.path.join(ROOT_DIR, "chrome_profile")
os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)


class ExecucaoInterrompida(Exception):
    """Levantada internamente quando o usuário pede para parar pela GUI.
    Sempre capturada dentro de executar(), que garante que os resultados
    parciais sejam salvos antes de encerrar."""


class ControleExecucao:
    """Permite pausar/retomar e interromper a execução a partir da GUI, de
    forma thread-safe (a automação roda numa thread separada da janela).
    Um único objeto é criado por execução e repassado por toda a cadeia de
    chamadas (executar -> login/processar_planilha -> loop de linhas)."""

    def __init__(self):
        self._pausado = threading.Event()
        self._parar = threading.Event()

    def pausar(self):
        self._pausado.set()

    def retomar(self):
        self._pausado.clear()

    def parar(self):
        self._parar.set()
        self._pausado.clear()  # não deixa preso esperando despausar

    @property
    def deve_parar(self):
        return self._parar.is_set()

    def verificar(self, log=print):
        """Bloqueia enquanto pausado; levanta ExecucaoInterrompida se o
        usuário pediu para parar. Chamar isso só em pontos seguros do
        loop (entre linhas/planilhas), nunca no meio de uma ação dentro
        do navegador."""
        avisou_pausa = False
        while self._pausado.is_set() and not self._parar.is_set():
            if not avisou_pausa:
                log("Execução pausada — clique em 'Retomar' na janela para continuar.")
                avisou_pausa = True
            time.sleep(0.5)
        if self._parar.is_set():
            raise ExecucaoInterrompida()


@dataclass
class PerfilPlanilha:
    """Descreve as particularidades de busca/colunas de uma planilha."""

    chave: str
    nome: str
    caminho_padrao: str
    # Ordem de tentativa dos ids de campo de busca (descrição) na tela do
    # Hinova. O campo de código ("codigo_cota") é sempre preenchido também,
    # como no desenvolvimento original — a busca combina os dois critérios.
    campos_busca: tuple = ("descricao_cota", "tipo_veiculo_cota")
    # Confirmado pelo usuário: em PT1 e PT2 a busca usa a coluna "Código"
    # (código) + "Tipo do veículo" (descrição), e o valor atualizado vem da
    # coluna "Valor". As demais colunas (Valor fipe inicial/final, Cota,
    # Valor antes da transformação, Multilicador, Taxa Adição, IDEAL,
    # calculo) não são usadas por este processo. "Cota" fica como
    # alternativa só por segurança, caso um arquivo futuro venha diferente.
    coluna_codigo: tuple = ("Código", "Cota")
    coluna_descricao: str = "Tipo do veículo"
    coluna_valor: str = "Valor"


PERFIS = {
    "PT1": PerfilPlanilha(
        chave="PT1",
        nome="PT 1",
        caminho_padrao=os.path.join(ONEDRIVE_DIR, "boot_pt1", "DEFINITIVO_COTAS PT 1.xlsx"),
        # PT1: tenta primeiro "tipo_veiculo_cota" (campo original) e, se
        # não achar, cai para "descricao_cota" também — como na PT2, só
        # que na ordem inversa — antes de considerar a cota não encontrada
        # e passar para a próxima linha.
        campos_busca=("tipo_veiculo_cota", "descricao_cota"),
    ),
    "PT2": PerfilPlanilha(
        chave="PT2",
        nome="PT 2",
        caminho_padrao=os.path.join(ONEDRIVE_DIR, "boot_pt2", "DEFINITIVO_COTAS PT 2.xlsx"),
        # PT2 (desenvolvimento original/beta): tenta primeiro
        # "descricao_cota" e, se não achar, cai para "tipo_veiculo_cota".
        campos_busca=("descricao_cota", "tipo_veiculo_cota"),
    ),
}
# Os caminhos acima apontam para a pasta original no OneDrive — nada foi
# copiado. Se preferir, use o botão "Selecionar arquivo..." na interface
# gráfica para apontar para outro local a qualquer momento.


def credenciais_configuradas():
    """True se HINOVA_USUARIO/HINOVA_SENHA estiverem no .env. Usado só para
    decidir se vale tentar o login automático — não bloqueia a execução,
    já que o login manual continua funcionando sem isso."""
    return bool(os.getenv("HINOVA_USUARIO")) and bool(os.getenv("HINOVA_SENHA"))


def _limpar_travas_chrome(pasta_perfil):
    """Remove os arquivos de "trava" que o Chrome deixa para trás quando um
    processo anterior não fecha direito (ex.: a janela foi fechada no X, o
    processo travou, ou o computador foi desligado com o Chrome aberto).

    Enquanto esses arquivos existem, o Chrome se recusa a abrir de novo
    usando essa mesma pasta de perfil — e o Selenium recebe o erro
    "unknown error: net::ERR_CONNECTION_REFUSED" (o Chrome nem chega a
    abrir de verdade). Apagar esses arquivos antes de cada início resolve
    isso sem precisar apagar o perfil inteiro (login/cookies continuam
    salvos)."""
    for nome in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        caminho = os.path.join(pasta_perfil, nome)
        try:
            if os.path.islink(caminho) or os.path.exists(caminho):
                os.remove(caminho)
        except OSError:
            pass


def iniciar_driver(log=print):
    os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
    _limpar_travas_chrome(CHROME_PROFILE_DIR)

    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")

    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as e:
        # Segunda tentativa: às vezes a trava só aparece de novo bem no
        # instante do lançamento (ex.: outro Chrome com o mesmo perfil
        # ainda fechando). Espera um pouco, limpa de novo e tenta uma
        # última vez antes de desistir com uma mensagem clara.
        log(f"Chrome não abriu na primeira tentativa ({e}). Tentando novamente...")
        time.sleep(2)
        _limpar_travas_chrome(CHROME_PROFILE_DIR)
        try:
            driver = webdriver.Chrome(options=options)
        except WebDriverException as e2:
            raise RuntimeError(
                "Não foi possível abrir o Chrome para a automação. Feche TODAS as "
                "janelas do Chrome (inclusive pelo Gerenciador de Tarefas, procurando "
                "por 'chrome.exe' e 'chromedriver.exe') e tente novamente. "
                f"Detalhe técnico: {e2}"
            ) from e2

    driver.maximize_window()
    return driver, WebDriverWait(driver, 20)


def _clicar_robusto(driver, elemento):
    """Clica em um elemento tratando o caso comum de outro elemento (ex.:
    uma coluna do layout ainda se ajustando) estar cobrindo o ponto do
    clique no instante exato do clique. Rola o elemento para o centro da
    tela e, se o clique normal for interceptado, usa um clique via
    JavaScript (que não depende de qual elemento está "por cima")."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
    time.sleep(0.3)
    try:
        elemento.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", elemento)


def tentar_login_automatico(driver, log=print):
    """Tentativa best-effort de preencher usuário/senha e clicar em Entrar.
    O campo "Código cliente" não precisa ser preenchido — é fixo por link
    (o próprio LOGIN_URL já identifica a conta) e o Hinova já o resolve
    automaticamente. Esta tentativa só completa o login de ponta a ponta se
    o reCAPTCHA estiver desativado e não houver código de autenticação
    pendente — caso contrário, simplesmente não completa, e
    aguardar_login_manual assume a partir daí. Nunca interage com o captcha.
    """
    usuario = os.getenv("HINOVA_USUARIO")
    senha = os.getenv("HINOVA_SENHA")
    if not usuario or not senha:
        return

    try:
        try:
            modal_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="myModal"]/div/div/div[2]/div/div/div/button')
                )
            )
            modal_btn.click()
            time.sleep(1)
        except TimeoutException:
            pass

        campo_usuario = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="usuario"]'))
        )
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)

        campo_senha = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="senha"]'))
        )
        campo_senha.clear()
        campo_senha.send_keys(senha)

        entrar_botao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="login"]/button[1]'))
        )
        _clicar_robusto(driver, entrar_botao)
        time.sleep(2)

        # Segundo clique, conforme observado na prática: às vezes o primeiro
        # clique só termina de ajustar/validar a tela, e é preciso confirmar
        # de novo. Se a página já tiver navegado e o botão não existir mais,
        # ignora — sinal de que o primeiro clique já bastou.
        try:
            entrar_botao = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="login"]/button[1]'))
            )
            _clicar_robusto(driver, entrar_botao)
        except (TimeoutException, StaleElementReferenceException):
            pass

        # Aguarda a página carregar antes de seguir para a checagem de
        # login, em vez de continuar no meio de um carregamento.
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass
        time.sleep(1)

        log("Usuário e senha preenchidos automaticamente.")
    except Exception as e:
        log(f"Login automático não foi possível ({e}). Complete manualmente se necessário.")


def aguardar_login_manual(driver, log=print, timeout_segundos=600, controle=None):
    """Confirma se o login já foi concluído (inclusive pelo tentar_login_
    automatico) e, se não, espera a pessoa completar manualmente na janela
    do Chrome (usuário, senha, código de autenticação e/ou o captcha — o
    código cliente já vem preenchido automaticamente pelo link). Detecta o
    sucesso tentando abrir a página de listagem de cotas até conseguir, ou
    até estourar o tempo limite (10 minutos). Se `controle` pedir para
    parar, levanta ExecucaoInterrompida em vez de continuar esperando.
    """
    avisou = False
    inicio = time.time()
    ultimo_aviso = inicio

    while time.time() - inicio < timeout_segundos:
        if controle is not None:
            controle.verificar(log=log)
        try:
            driver.get(COTAS_URL)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="codigo_cota"]'))
            )
            log("Login confirmado — iniciando a atualização das cotas.")
            return
        except TimeoutException:
            if not avisou:
                log("")
                log("=" * 60)
                log("AÇÃO NECESSÁRIA: complete o login na janela do Chrome que abriu")
                log("(usuário, senha, código de autenticação e/ou o captcha \"Não sou")
                log("um robô\") e clique em Entrar. O código cliente já vem preenchido")
                log("automaticamente. O programa continua sozinho ao detectar o login.")
                log("=" * 60)
                avisou = True
            elif time.time() - ultimo_aviso > 30:
                log("Ainda aguardando o login ser concluído na janela do Chrome...")
                ultimo_aviso = time.time()
            time.sleep(3)

    raise RuntimeError(
        "Tempo esgotado aguardando o login manual (10 minutos). Rode novamente "
        "e complete o login mais rapidamente na janela do Chrome."
    )


def login(driver, wait, log=print, controle=None):
    log("Abrindo a página de login do Hinova...")
    driver.get(LOGIN_URL)
    tentar_login_automatico(driver, log=log)
    aguardar_login_manual(driver, log=log, controle=controle)


def _formatar_codigo_busca(codigo):
    """Formata o valor da coluna de código para o campo de busca do Hinova.

    Evita enviar algo como "123.0" quando o valor é um número inteiro
    (ex.: 123): a busca do Hinova pode não reconhecer o ".0" e não filtrar
    a tabela corretamente. Nesse caso a linha clicada acaba sendo a
    primeira exibida (não necessariamente filtrada pelo código certo) —
    o que explica cotas erradas serem atualizadas mesmo com o valor certo
    na planilha, especialmente quando várias linhas compartilham a mesma
    descrição (ex.: mesma categoria de veículo, faixa de FIPE diferente).
    """
    try:
        valor_float = float(codigo)
    except (TypeError, ValueError):
        return str(codigo).strip()
    if valor_float.is_integer():
        return str(int(valor_float))
    return str(round(valor_float, 2))


def _codigos_conferem(codigo_busca, codigo_sga):
    """Confere se o código que o SGA está mostrando na linha encontrada
    bate com o código que a planilha pedia para buscar. Se não bater, é
    sinal de que a busca não filtrou corretamente e a linha errada seria
    editada — nesse caso o chamador deve pular a linha em vez de editar,
    para não repetir o problema de "atualizou uma cota diferente"."""
    if codigo_sga is None:
        return True  # não conseguimos ler a coluna para conferir; não bloqueia
    a = str(codigo_busca).strip()
    b = str(codigo_sga).strip()
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except ValueError:
        return False


def buscar_cota(driver, wait, codigo, descricao, campos_busca):
    """Busca a cota preenchendo SEMPRE os dois critérios — código
    ("codigo_cota") e descrição (um dos campos em `campos_busca`, na
    ordem definida pelo perfil) — como no desenvolvimento original, e só
    segue adiante depois de confirmar que a tabela de resultados
    realmente atualizou (em vez de um "sleep" fixo, que pode não ser
    suficiente e fazer o código clicar numa linha antiga/errada que
    ainda não refletia os critérios de busca).

    Retorna (encontrado, codigo_sga): encontrado é True se apareceu um
    resultado clicável na tabela; codigo_sga é o código exibido na coluna 1
    dessa linha (para conferência em processar_planilha), ou None se não
    foi possível ler.
    """
    linha_acao_xpath = '//*[@id="DataTables_Table_0"]/tbody/tr/td[10]/div/a'
    linha_codigo_xpath = '//*[@id="DataTables_Table_0"]/tbody/tr/td[1]'

    # Guarda uma referência à linha de ação atual (se existir) ANTES de
    # preencher a busca, para depois conseguirmos confirmar que a tabela
    # realmente recarregou (em vez de continuar mostrando essa mesma linha
    # antiga, de uma busca anterior, com o clique caindo no lugar errado).
    try:
        linha_anterior = driver.find_element(By.XPATH, linha_acao_xpath)
    except Exception:
        linha_anterior = None

    campo_codigo = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="codigo_cota"]')))
    campo_codigo.clear()
    campo_codigo.send_keys(str(codigo))

    for campo_id in campos_busca:
        try:
            campo_descricao = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="{campo_id}"]'))
            )
        except TimeoutException:
            continue  # esse campo não existe nesta tela, tenta o próximo

        campo_descricao.clear()
        campo_descricao.send_keys(descricao)

        # Espera a tabela realmente reagir aos dois critérios de busca
        # (código + descrição) antes de seguir. Se havia uma linha antes,
        # espera ela ficar "stale" (sinal de que o DataTables recarregou o
        # corpo da tabela) antes de checar a nova linha.
        try:
            if linha_anterior is not None:
                WebDriverWait(driver, 8).until(EC.staleness_of(linha_anterior))
        except TimeoutException:
            pass  # às vezes o resultado não muda de fato — segue mesmo assim

        try:
            WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.XPATH, linha_acao_xpath)))
            codigo_sga = None
            try:
                codigo_sga = driver.find_element(By.XPATH, linha_codigo_xpath).text.strip()
            except Exception:
                pass
            return True, codigo_sga
        except TimeoutException:
            campo_descricao.clear()
            continue

    return False, None


def atualizar_linha(driver, wait, novo_valor):
    driver.execute_script(
        """
        let backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
        """
    )
    time.sleep(0.5)

    driver.find_element(By.XPATH, '//*[@id="DataTables_Table_0"]/tbody/tr/td[10]/div/a').click()
    driver.find_element(By.XPATH, '//*[@id="DataTables_Table_0"]/tbody/tr/td[10]/div/div/button[1]').click()
    time.sleep(3)

    campo_valor = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="cota_valor"]')))
    valor_antigo = campo_valor.get_attribute("value")
    campo_valor.clear()
    string_valor_novo = f"{novo_valor:.2f}"
    campo_valor.send_keys(string_valor_novo)
    time.sleep(3)

    try:
        for botao in driver.find_elements(By.XPATH, '//button[span[@aria-hidden="true"]]'):
            if not botao.is_displayed():
                continue
            is_safe = driver.execute_script(
                """
                let btn = arguments[0];
                while (btn && !btn.classList.contains("modal")) { btn = btn.parentElement; }
                if (!btn) return false;
                if (btn.id === "cota") return false;
                if (btn.querySelector("#cota_valor")) return false;
                let style = window.getComputedStyle(btn);
                return style.display !== "none" && parseFloat(style.opacity) > 0;
                """,
                botao,
            )
            if is_safe:
                driver.execute_script("arguments[0].click();", botao)
                time.sleep(1)
    except Exception:
        pass  # fechar modal residual é best-effort, não deve travar o fluxo

    driver.find_element(By.XPATH, '//*[@id="cota"]/button').click()
    return valor_antigo, string_valor_novo


def _normalizar_nome_coluna(nome):
    """Remove espaços nas pontas, acentos e diferenças de maiúsculas/
    minúsculas, para comparar nomes de coluna de forma tolerante (ex.:
    "Código " ou "codigo" devem ser reconhecidos como "Código")."""
    nome = str(nome).strip()
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def _resolver_coluna(df, candidatos, log=print):
    """Encontra, de forma tolerante a acento/maiúscula/espaço, a coluna do
    DataFrame correspondente a um nome esperado. `candidatos` pode ser uma
    string (um único nome) ou uma tupla/lista de nomes alternativos,
    tentados nessa ordem — útil quando o template já teve mais de um nome
    para a mesma coluna (ex.: "Cota" no template atual, "Código" em
    templates antigos). Levanta um erro claro (com a lista de colunas
    reais da planilha) se não encontrar nada parecido com nenhum dos
    candidatos, em vez de um KeyError genérico no meio do processamento."""
    if isinstance(candidatos, str):
        candidatos = (candidatos,)

    for nome_esperado in candidatos:
        if nome_esperado in df.columns:
            return nome_esperado

        alvo = _normalizar_nome_coluna(nome_esperado)
        for coluna in df.columns:
            if _normalizar_nome_coluna(coluna) == alvo:
                if coluna != nome_esperado:
                    log(f"[AVISO] Coluna \"{nome_esperado}\" não encontrada exatamente — usando \"{coluna}\".")
                return coluna

    nomes_tentados = " / ".join(f'"{c}"' for c in candidatos)
    colunas_disponiveis = ", ".join(str(c) for c in df.columns)
    raise KeyError(
        f"Nenhuma das colunas esperadas ({nomes_tentados}) foi encontrada na planilha. "
        f"Colunas disponíveis: [{colunas_disponiveis}]"
    )


def processar_planilha(
    driver, wait, perfil: PerfilPlanilha, caminho_planilha, log=print, progresso=None,
    historico=None, erros=None, controle=None,
):
    """Processa uma planilha, linha por linha. `historico`/`erros` podem
    ser listas já existentes (mutadas diretamente, por referência) —
    assim, se a execução for interrompida no meio desta planilha, quem
    chamou esta função (executar, abaixo) ainda enxerga tudo que já foi
    processado até aquele ponto, e consegue salvar a planilha de log
    mesmo assim.
    """
    log(f"Processando {perfil.nome}: {caminho_planilha}")
    df = pd.read_excel(caminho_planilha).round(2)
    # Remove espaços indesejados nos nomes de coluna (ex.: "Código " lido
    # do Excel com um espaço a mais no fim), para não perder a coluna certa
    # por causa de um detalhe de formatação do arquivo.
    df.columns = [str(c).strip() for c in df.columns]
    total = len(df)

    # Resolve os nomes reais das colunas antes de começar o loop, para dar
    # um erro claro (com as colunas disponíveis) de uma vez só, em vez de
    # falhar no meio do processamento com um KeyError seco.
    col_codigo = _resolver_coluna(df, perfil.coluna_codigo, log=log)
    col_descricao = _resolver_coluna(df, perfil.coluna_descricao, log=log)
    col_valor = _resolver_coluna(df, perfil.coluna_valor, log=log)

    historico = historico if historico is not None else []
    erros = erros if erros is not None else []

    for i in range(total):
        if controle is not None:
            controle.verificar(log=log)  # bloqueia se pausado; levanta se pediram parar

        codigo = df.iloc[i][col_codigo]
        descricao = df.iloc[i][col_descricao]
        novo_valor = df.iloc[i][col_valor]
        codigo_busca = _formatar_codigo_busca(codigo)

        if progresso:
            progresso(i + 1, total, perfil.nome)

        try:
            encontrado, codigo_sga = buscar_cota(driver, wait, codigo_busca, descricao, perfil.campos_busca)
            if not encontrado:
                log(f"[NÃO ENCONTRADO] {perfil.nome} — código {codigo_busca}")
                registro = df.iloc[i].to_dict()
                registro["Motivo_Erro"] = "Cota não encontrada na busca"
                erros.append(registro)
                driver.get(COTAS_URL)
                time.sleep(3)
                continue

            if not _codigos_conferem(codigo_busca, codigo_sga):
                log(
                    f"[DIVERGÊNCIA] {perfil.nome} — planilha pedia código {codigo_busca}, "
                    f"mas o SGA mostrou {codigo_sga}. Pulando esta linha para não atualizar "
                    f"a cota errada."
                )
                registro = df.iloc[i].to_dict()
                registro["Motivo_Erro"] = f"Código divergente: esperado {codigo_busca}, SGA mostrou {codigo_sga}"
                erros.append(registro)
                driver.get(COTAS_URL)
                time.sleep(3)
                continue

            valor_antigo, valor_novo_str = atualizar_linha(driver, wait, novo_valor)
            historico.append(
                {
                    "planilha": perfil.nome,
                    "codigo_planilha": codigo_busca,
                    "codigo_sga": codigo_sga,
                    "descricao": descricao,
                    "valor_antigo": valor_antigo,
                    "valor_novo": valor_novo_str,
                }
            )
            log(f"[OK] {perfil.nome} — código {codigo_sga}: {valor_antigo} -> {valor_novo_str}")

        except ExecucaoInterrompida:
            raise
        except Exception as e:
            log(f"[ERRO] {perfil.nome} — código {codigo_busca}: {e}")
            registro = df.iloc[i].to_dict()
            registro["Motivo_Erro"] = str(e)
            erros.append(registro)

        driver.get(COTAS_URL)
        time.sleep(3)

    return historico, erros


def salvar_resultados(historico, erros, timestamp=None):
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    caminhos = {}
    if historico:
        caminho_hist = os.path.join(LOG_DIR, f"historico_atualizacoes_{timestamp}.xlsx")
        pd.DataFrame(historico).to_excel(caminho_hist, index=False)
        caminhos["historico"] = caminho_hist
    if erros:
        caminho_erros = os.path.join(LOG_DIR, f"itens_para_reprocessar_{timestamp}.xlsx")
        pd.DataFrame(erros).to_excel(caminho_erros, index=False)
        caminhos["erros"] = caminho_erros
    return caminhos


def executar(chaves_perfis, caminhos_planilhas=None, log=print, progresso=None, controle=None):
    """Ponto de entrada único usado pela GUI e pelo script de linha de comando.

    chaves_perfis: lista de chaves de PERFIS a processar, ex: ["PT1", "PT2"]
    caminhos_planilhas: dict opcional {chave: caminho_do_arquivo}. Se omitido
        (ou faltando uma chave), usa o caminho_padrao do perfil.
    controle: ControleExecucao opcional, usado pela GUI para pausar/retomar
        ou interromper a execução.

    historico_total/erros_total são passados por referência para
    processar_planilha e salvos num "finally" — ou seja, mesmo que a
    execução seja interrompida (botão "Parar" na GUI, Ctrl+C, o Chrome ser
    fechado, um erro inesperado no meio do processamento etc.), a planilha
    de histórico e/ou de itens com erro é salva com tudo que já tinha sido
    processado até aquele momento.
    """
    caminhos_planilhas = caminhos_planilhas or {}

    driver, wait = iniciar_driver(log=log)
    historico_total, erros_total = [], []
    caminhos_resultado = {}

    try:
        login(driver, wait, log=log, controle=controle)
        for chave in chaves_perfis:
            if controle is not None and controle.deve_parar:
                log(f"Execução interrompida pelo usuário antes de iniciar {PERFIS[chave].nome}.")
                break
            perfil = PERFIS[chave]
            caminho = caminhos_planilhas.get(chave) or perfil.caminho_padrao
            if not os.path.exists(caminho):
                log(f"Planilha não encontrada para {perfil.nome}, pulando: {caminho}")
                continue
            processar_planilha(
                driver, wait, perfil, caminho, log=log, progresso=progresso,
                historico=historico_total, erros=erros_total, controle=controle,
            )
    except ExecucaoInterrompida:
        log("")
        log("Execução interrompida pelo usuário — salvando o que já foi processado...")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

        caminhos_resultado = salvar_resultados(historico_total, erros_total)
        for tipo, caminho_salvo in caminhos_resultado.items():
            log(f"[LOG] Arquivo salvo ({tipo}): {caminho_salvo}")

    return {
        "total_atualizados": len(historico_total),
        "total_erros": len(erros_total),
        "arquivos": caminhos_resultado,
        "interrompido": bool(controle is not None and controle.deve_parar),
    }
