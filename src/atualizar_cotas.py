"""
atualizar_cotas.py

Versão de linha de comando (sem interface gráfica) da atualização de cotas.
Para o dia a dia — principalmente para quem não tem conhecimento técnico —
prefira abrir a interface gráfica (gui.py, via duplo clique em run.bat).

O login no Hinova pode precisar ser concluído manualmente na janela do
Chrome que abrir (usuário, senha, código de autenticação e o captcha "Não
sou um robô" — o código cliente é fixo por link e já vem preenchido
automaticamente). O script detecta quando o login foi concluído e segue com
a atualização das cotas.

Este script continua disponível como alternativa para quem preferir rodar
direto pelo terminal. Não há mais um caminho de planilha fixo no código —
ele usa o último caminho usado por cada perfil (PT1/PT2), lembrado
localmente em config.local.json (a mesma configuração que a GUI usa e
atualiza). Rode a GUI pelo menos uma vez e selecione as planilhas por lá
antes de usar este script, ou informe os caminhos na hora de chamar
core.executar(...) diretamente.
"""

import sys

import automacao_core as core


def log(mensagem):
    print(mensagem)


def progresso(atual, total, nome_perfil):
    print(f"{nome_perfil}: {atual}/{total}", end="\r")


def main():
    caminhos_planilhas = {
        chave: core.obter_ultimo_caminho(chave) for chave in ("PT1", "PT2")
    }
    faltando = [chave for chave, caminho in caminhos_planilhas.items() if not caminho]
    if faltando:
        print(
            "Nenhum caminho de planilha configurado ainda para: " + ", ".join(faltando) + ".\n"
            "Abra a interface gráfica (gui.py) e selecione as planilhas pelo menos uma vez — "
            "o caminho fica lembrado para as próximas execuções, inclusive por aqui."
        )
        sys.exit(1)

    resultado = core.executar(["PT1", "PT2"], caminhos_planilhas=caminhos_planilhas, log=log, progresso=progresso)
    print()
    if resultado.get("erro_fatal"):
        print(resultado["erro_fatal"])
    else:
        print(f"Concluído — {resultado['total_atualizados']} atualizados, {resultado['total_erros']} com erro.")
    for tipo, caminho in resultado["arquivos"].items():
        print(f"Arquivo salvo ({tipo}): {caminho}")


if __name__ == "__main__":
    main()
