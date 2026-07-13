"""
gui.py

Interface gráfica da atualização de cotas no Hinova — feita para ser usada
por quem NÃO tem conhecimento técnico. Basta selecionar (ou manter) as
planilhas de PT1 e PT2 e clicar em um dos botões de início.

Login: se o .env tiver usuário/senha e o reCAPTCHA estiver desativado no
painel administrativo durante a execução, o programa tenta logar sozinho.
Caso contrário (captcha ativo e/ou código de autenticação pendente), a
pessoa completa o login manualmente na janela do Chrome que abrir — o
programa detecta automaticamente quando o login foi concluído e segue com
a atualização das cotas. O campo "Código cliente" é fixo por link (o
próprio endereço de login já identifica a conta) e já vem preenchido
automaticamente pelo Hinova — não precisa de nenhuma ação.

Pausar/Parar: durante uma execução, os botões "Pausar" e "Parar" ficam
disponíveis. Pausar para a execução no início da próxima linha/planilha
(sem deixar nada pela metade) até clicar em "Retomar". Parar interrompe de
vez — o que já tiver sido processado até aquele momento é salvo mesmo
assim na pasta de logs.

Nada é executado automaticamente: a pessoa sempre precisa clicar em um
botão e confirmar antes de qualquer ação real no sistema.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import automacao_core as core

APP_TITLE = "Atualização de Cotas — Hinova"

# Logo exibida no topo da janela. Fica em AtualizaCotas/assets/ (uma pasta
# acima de src/) — se o arquivo não existir, a janela abre normalmente sem
# a logo (não trava o programa por causa disso).
LOGO_PATH = os.path.join(core.ROOT_DIR, "assets", "logo_gol_plus.png")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x640")
        self.minsize(680, 540)

        self.caminhos = {
            "PT1": tk.StringVar(value=core.PERFIS["PT1"].caminho_padrao),
            "PT2": tk.StringVar(value=core.PERFIS["PT2"].caminho_padrao),
        }
        self.fila_log = queue.Queue()
        self.executando = False
        self.pausado = False
        self.controle = None

        self._montar_layout()
        self._atualizar_status_login()
        self.after(200, self._drenar_fila_log)

    # ------------------------------------------------------------------
    def _montar_layout(self):
        self._logo_img = None  # mantém referência viva (senão o Tkinter descarta a imagem)
        if os.path.exists(LOGO_PATH):
            try:
                img = tk.PhotoImage(file=LOGO_PATH)
                # Reduz a imagem se ela vier grande (ex.: exportada em alta
                # resolução) para não dominar o topo da janela — mantém a
                # proporção usando subsample (recorte por fator inteiro).
                largura_alvo = 220
                if img.width() > largura_alvo:
                    fator = max(1, img.width() // largura_alvo)
                    img = img.subsample(fator, fator)
                self._logo_img = img
                tk.Label(self, image=self._logo_img).pack(pady=(12, 4))
            except tk.TclError:
                pass  # arquivo presente mas não é um PNG válido — segue sem a logo

        tk.Label(
            self,
            text="Selecione as planilhas já reajustadas de PT1 e PT2 e clique em Iniciar.",
            font=("Segoe UI", 10),
        ).pack(pady=(12, 4))

        self.status_login = tk.Label(self, text="", font=("Segoe UI", 9), fg="#555555",
                                      wraplength=700, justify="center")
        self.status_login.pack(pady=(0, 6))

        self.btn_rodar = {}
        for chave in ("PT1", "PT2"):
            frame = tk.LabelFrame(self, text=f"Planilha {chave}", padx=10, pady=10)
            frame.pack(fill="x", padx=15, pady=8)

            entry = tk.Entry(frame, textvariable=self.caminhos[chave], width=55)
            entry.pack(side="left", padx=(0, 8), fill="x", expand=True)

            tk.Button(
                frame,
                text="Selecionar arquivo...",
                command=lambda c=chave: self._selecionar_arquivo(c),
            ).pack(side="left", padx=4)

            btn_rodar = tk.Button(
                frame,
                text=f"Rodar só {chave}",
                command=lambda c=chave: self._iniciar([c]),
            )
            btn_rodar.pack(side="left", padx=4)
            self.btn_rodar[chave] = btn_rodar

        botoes_frame = tk.Frame(self)
        botoes_frame.pack(pady=10)

        self.btn_iniciar_tudo = tk.Button(
            botoes_frame,
            text="Iniciar PT1 + PT2",
            font=("Segoe UI", 10, "bold"),
            bg="#2e7d32",
            fg="white",
            padx=16,
            pady=6,
            command=lambda: self._iniciar(["PT1", "PT2"]),
        )
        self.btn_iniciar_tudo.pack(side="left", padx=6)

        self.btn_pausar = tk.Button(
            botoes_frame,
            text="Pausar",
            state="disabled",
            padx=10,
            command=self._alternar_pausa,
        )
        self.btn_pausar.pack(side="left", padx=6)

        self.btn_parar = tk.Button(
            botoes_frame,
            text="Parar",
            state="disabled",
            fg="#8a1c1c",
            padx=10,
            command=self._parar_execucao,
        )
        self.btn_parar.pack(side="left", padx=6)

        tk.Button(
            botoes_frame,
            text="Abrir pasta de logs",
            command=self._abrir_pasta_logs,
        ).pack(side="left", padx=6)

        self.progresso_label = tk.Label(self, text="", font=("Segoe UI", 9))
        self.progresso_label.pack(pady=(4, 0))

        # O rodapé precisa ser "reservado" (side="bottom") ANTES do log, que
        # usa expand=True. No gerenciador pack do Tkinter, quem é empacotado
        # primeiro reserva seu espaço primeiro — se o log (expand=True) fosse
        # empacotado antes, ele tomaria toda a altura da janela e o rodapé
        # ficaria sem espaço nenhum sobrando (por isso ele "sumia").
        tk.Label(
            self,
            text="Desenvolvido por Luigi Giuseppe",
            font=("Segoe UI", 8),
            fg="#1F1E1E",
        ).pack(side="bottom", pady=(0, 6))

        self.log_text = scrolledtext.ScrolledText(self, height=18, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=15, pady=10)

    # ------------------------------------------------------------------
    def _atualizar_status_login(self):
        if core.credenciais_configuradas():
            self.status_login.config(
                text=(
                    "Login automático será tentado com o usuário/senha do .env "
                    "(só funciona de ponta a ponta se o reCAPTCHA estiver desativado). "
                    "Se ainda pedir código de autenticação ou captcha, complete manualmente "
                    "(o código cliente já vem preenchido pelo link)."
                )
            )
        else:
            self.status_login.config(
                text=(
                    "O login será feito manualmente na janela do Chrome (usuário, senha, "
                    "código de autenticação e/ou captcha — o código cliente já vem "
                    "preenchido automaticamente pelo link)."
                )
            )

    def _selecionar_arquivo(self, chave):
        caminho = filedialog.askopenfilename(
            title=f"Selecione a planilha {chave}",
            filetypes=[("Planilhas Excel", "*.xlsx")],
        )
        if caminho:
            self.caminhos[chave].set(caminho)

    def _abrir_pasta_logs(self):
        os.makedirs(core.LOG_DIR, exist_ok=True)
        try:
            os.startfile(core.LOG_DIR)  # Windows
        except AttributeError:
            messagebox.showinfo(APP_TITLE, f"Pasta de logs: {core.LOG_DIR}")

    def _log(self, mensagem):
        self.fila_log.put(mensagem)

    def _progresso(self, atual, total, nome_perfil):
        self.fila_log.put(("__progresso__", atual, total, nome_perfil))

    def _drenar_fila_log(self):
        try:
            while True:
                item = self.fila_log.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "__progresso__":
                    _, atual, total, nome_perfil = item
                    self.progresso_label.config(text=f"{nome_perfil}: processando {atual} de {total}")
                else:
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", str(item) + "\n")
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(200, self._drenar_fila_log)

    # ------------------------------------------------------------------
    def _iniciar(self, chaves):
        if self.executando:
            messagebox.showwarning(APP_TITLE, "Já existe uma atualização em andamento.")
            return

        nomes = " e ".join(core.PERFIS[c].nome for c in chaves)
        confirmar = messagebox.askyesno(
            APP_TITLE,
            f"Isso vai abrir o Chrome e atualizar as cotas de {nomes}.\n\n"
            "Se o login automático não completar (captcha ativo ou código de "
            "autenticação pendente), complete o login manualmente na janela que "
            "abrir (usuário, senha, código de autenticação/captcha — o código "
            "cliente já vem preenchido). O programa detecta e continua sozinho.\n\n"
            "Durante a execução você pode usar os botões 'Pausar' e 'Parar'.\n\n"
            "Deseja continuar?",
        )
        if not confirmar:
            return

        caminhos_planilhas = {c: self.caminhos[c].get() for c in chaves}
        self.executando = True
        self.pausado = False
        self.controle = core.ControleExecucao()

        self.btn_iniciar_tudo.config(state="disabled")
        for c in ("PT1", "PT2"):
            self.btn_rodar[c].config(state="disabled")
        self.btn_pausar.config(state="normal", text="Pausar")
        self.btn_parar.config(state="normal")

        thread = threading.Thread(
            target=self._executar_em_thread, args=(chaves, caminhos_planilhas), daemon=True
        )
        thread.start()

    def _alternar_pausa(self):
        if self.controle is None:
            return
        if self.pausado:
            self.controle.retomar()
            self.pausado = False
            self.btn_pausar.config(text="Pausar")
            self._log("Retomando a execução...")
        else:
            self.controle.pausar()
            self.pausado = True
            self.btn_pausar.config(text="Retomar")
            self._log("Pausa solicitada — a execução para no início da próxima linha/planilha.")

    def _parar_execucao(self):
        if self.controle is None:
            return
        confirmar = messagebox.askyesno(
            APP_TITLE,
            "Isso vai interromper a execução assim que possível. O que já foi "
            "processado até agora será salvo na pasta de logs mesmo assim.\n\n"
            "Deseja interromper?",
        )
        if not confirmar:
            return
        self._log("Interrupção solicitada pelo usuário...")
        self.controle.parar()
        self.btn_parar.config(state="disabled")
        self.btn_pausar.config(state="disabled")

    def _executar_em_thread(self, chaves, caminhos_planilhas):
        try:
            resultado = core.executar(
                chaves, caminhos_planilhas, log=self._log, progresso=self._progresso,
                controle=self.controle,
            )
            self._log("")
            if resultado.get("interrompido"):
                self._log(
                    f"INTERROMPIDO PELO USUÁRIO — {resultado['total_atualizados']} atualizados, "
                    f"{resultado['total_erros']} com erro até o momento da parada."
                )
            else:
                self._log(
                    f"CONCLUÍDO — {resultado['total_atualizados']} atualizados, "
                    f"{resultado['total_erros']} com erro."
                )
            for tipo, caminho in resultado["arquivos"].items():
                self._log(f"Arquivo salvo ({tipo}): {caminho}")

            titulo_msg = "Interrompido" if resultado.get("interrompido") else "Concluído!"
            self.after(
                0,
                lambda: messagebox.showinfo(
                    APP_TITLE,
                    f"{titulo_msg}\n{resultado['total_atualizados']} cotas atualizadas.\n"
                    f"{resultado['total_erros']} com erro (veja a pasta de logs).",
                ),
            )
        except Exception as e:
            # Captura a mensagem como string agora: "except ... as e" apaga
            # a variável "e" assim que este bloco termina, então um lambda
            # agendado com self.after (que só roda mais tarde) não consegue
            # mais acessá-la — daí o NameError. Guardando em "erro_msg" isso
            # não acontece.
            erro_msg = str(e)
            self._log(f"ERRO FATAL: {erro_msg}")
            self.after(
                0,
                lambda erro_msg=erro_msg: messagebox.showerror(
                    APP_TITLE, f"Ocorreu um erro:\n{erro_msg}"
                ),
            )
        finally:
            self.executando = False
            self.pausado = False
            self.controle = None
            self.after(0, lambda: self.btn_iniciar_tudo.config(state="normal"))
            for c in ("PT1", "PT2"):
                self.after(0, lambda c=c: self.btn_rodar[c].config(state="normal"))
            self.after(0, lambda: self.btn_pausar.config(state="disabled", text="Pausar"))
            self.after(0, lambda: self.btn_parar.config(state="disabled"))
            self.after(0, lambda: self.progresso_label.config(text=""))


if __name__ == "__main__":
    app = App()
    app.mainloop()
