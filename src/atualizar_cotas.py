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
direto pelo terminal. Processa PT1 e PT2 nos caminhos padrão definidos em
automacao_core.PERFIS.
"""

import automacao_core as core


def log(mensagem):
    print(mensagem)


def progresso(atual, total, nome_perfil):
    print(f"{nome_perfil}: {atual}/{total}", end="\r")


def main():
    resultado = core.executar(["PT1", "PT2"], log=log, progresso=progresso)
    print()
    print(f"Concluído — {resultado['total_atualizados']} atualizados, {resultado['total_erros']} com erro.")
    for tipo, caminho in resultado["arquivos"].items():
        print(f"Arquivo salvo ({tipo}): {caminho}")


if __name__ == "__main__":
    main()
