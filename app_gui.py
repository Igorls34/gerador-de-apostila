import json
import logging
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

# Importa a lógica do motor de geração
import gerar_pdf

DIR_BASE = os.path.abspath(os.path.dirname(__file__))
CAMINHO_JSON_PADRAO = os.path.join(DIR_BASE, "data", "apostila_v1.json")
CAMINHO_PDF_PADRAO = os.path.join(DIR_BASE, "output", "Apostila_n8n_v1.pdf")


class QueueHandler(logging.Handler):
    """Handler de logging para enviar logs em tempo real para a fila da interface gráfica."""
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)


class GeradorApostilaGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gerador de Apostilas em PDF • n8n & Docs")
        self.root.geometry("740x640")
        self.root.minsize(680, 560)

        # Fila de logs thread-safe
        self.log_queue = queue.Queue()
        self.ultimo_pdf_gerado: Optional[str] = None

        self._configurar_estilos()
        self._construir_interface()
        self._configurar_logging()
        self._atualizar_preview_json()
        self._processar_logs()

    def _configurar_estilos(self):
        """Define o visual moderno usando ttk."""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # Cores
        self.cor_primaria = "#0056b3"
        self.cor_fundo = "#f8fafc"
        self.cor_card = "#ffffff"
        self.cor_texto = "#1e293b"

        self.root.configure(bg=self.cor_fundo)

        self.style.configure(".", background=self.cor_fundo, foreground=self.cor_texto, font=("Segoe UI", 9))
        self.style.configure("TLabel", background=self.cor_fundo, foreground=self.cor_texto)
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=self.cor_primaria)
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#64748b")
        self.style.configure("Bold.TLabel", font=("Segoe UI", 9, "bold"))
        
        self.style.configure("Card.TFrame", background=self.cor_card, relief="solid", borderwidth=1)
        self.style.configure("CardLabel.TLabel", background=self.cor_card, foreground="#334155")
        self.style.configure("CardVal.TLabel", background=self.cor_card, foreground=self.cor_primaria, font=("Segoe UI", 9, "bold"))

        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background=self.cor_primaria)
        self.style.map("Action.TButton", background=[("active", "#004085"), ("disabled", "#94a3b8")])

    def _construir_interface(self):
        """Monta a estrutura de widgets da interface."""
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. Cabeçalho
        header_frame = ttk.Frame(container)
        header_frame.pack(fill=tk.X, pady=(0, 14))

        lbl_titulo = ttk.Label(header_frame, text="📘 Gerador Automatizado de Apostilas", style="Header.TLabel")
        lbl_titulo.pack(anchor="w")

        lbl_sub = ttk.Label(header_frame, text="Renderização nativa de alta fidelidade a partir de esquemas JSON estruturados.", style="SubHeader.TLabel")
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 2. Seção de Arquivos (Inputs)
        arquivos_frame = ttk.LabelFrame(container, text=" Configuração de Arquivos ", padding=12)
        arquivos_frame.pack(fill=tk.X, pady=(0, 12))

        # Arquivo JSON
        ttk.Label(arquivos_frame, text="Arquivo JSON de Entrada:", style="Bold.TLabel").grid(row=0, column=0, sticky="w", pady=(2, 4))
        self.entry_json = ttk.Entry(arquivos_frame)
        self.entry_json.insert(0, CAMINHO_JSON_PADRAO)
        self.entry_json.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        self.entry_json.bind("<KeyRelease>", lambda e: self._atualizar_preview_json())

        btn_browse_json = ttk.Button(arquivos_frame, text="Procurar...", command=self._selecionar_json)
        btn_browse_json.grid(row=1, column=1, pady=(0, 8))

        # Arquivo PDF de Saída
        ttk.Label(arquivos_frame, text="Destino do Arquivo PDF:", style="Bold.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 4))
        self.entry_pdf = ttk.Entry(arquivos_frame)
        self.entry_pdf.insert(0, CAMINHO_PDF_PADRAO)
        self.entry_pdf.grid(row=3, column=0, sticky="ew", padx=(0, 8))

        btn_browse_pdf = ttk.Button(arquivos_frame, text="Salvar como...", command=self._selecionar_pdf_destino)
        btn_browse_pdf.grid(row=3, column=1)

        arquivos_frame.columnconfigure(0, weight=1)

        # 3. Card de Prévia Rápida do JSON
        self.card_preview = ttk.Frame(container, style="Card.TFrame", padding=10)
        self.card_preview.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(self.card_preview, text="Prévia dos Metadados:", style="CardLabel.TLabel", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        ttk.Label(self.card_preview, text="Título da Obra:", style="CardLabel.TLabel").grid(row=1, column=0, sticky="w")
        self.lbl_prev_titulo = ttk.Label(self.card_preview, text="---", style="CardVal.TLabel")
        self.lbl_prev_titulo.grid(row=1, column=1, sticky="w", padx=(8, 0))

        ttk.Label(self.card_preview, text="Autor / Instituição:", style="CardLabel.TLabel").grid(row=2, column=0, sticky="w")
        self.lbl_prev_autor = ttk.Label(self.card_preview, text="---", style="CardVal.TLabel")
        self.lbl_prev_autor.grid(row=2, column=1, sticky="w", padx=(8, 0))

        ttk.Label(self.card_preview, text="Capítulos Detectados:", style="CardLabel.TLabel").grid(row=3, column=0, sticky="w")
        self.lbl_prev_caps = ttk.Label(self.card_preview, text="---", style="CardVal.TLabel")
        self.lbl_prev_caps.grid(row=3, column=1, sticky="w", padx=(8, 0))

        # 4. Ações Principais
        actions_frame = ttk.Frame(container)
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        self.var_abrir = tk.BooleanVar(value=True)
        chk_abrir = ttk.Checkbutton(actions_frame, text="Abrir o PDF automaticamente após a geração", variable=self.var_abrir)
        chk_abrir.pack(side=tk.LEFT)

        self.btn_gerar = ttk.Button(actions_frame, text="🚀 Gerar Apostila em PDF", style="Action.TButton", command=self._executar_geracao)
        self.btn_gerar.pack(side=tk.RIGHT, ipady=4, ipadx=10)

        # 5. Barra de Progresso
        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 8))

        # 6. Console de Logs
        log_frame = ttk.LabelFrame(container, text=" Registro de Execução (Logs) ", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.txt_log = tk.Text(log_frame, wrap="word", height=7, font=("Consolas", 8), bg="#0f172a", fg="#e2e8f0", insertbackground="#ffffff")
        scrollbar = ttk.Scrollbar(log_frame, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=scrollbar.set)

        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 7. Barra Inferior de Atalhos
        bottom_frame = ttk.Frame(container)
        bottom_frame.pack(fill=tk.X)

        self.btn_abrir_pasta = ttk.Button(bottom_frame, text="📂 Abrir Pasta de Saída", command=self._abrir_pasta_saida)
        self.btn_abrir_pasta.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_abrir_pdf = ttk.Button(bottom_frame, text="👁️ Ver PDF Gerado", command=self._abrir_pdf_gerado, state=tk.DISABLED)
        self.btn_abrir_pdf.pack(side=tk.LEFT)

        lbl_versao = ttk.Label(bottom_frame, text="v1.0 • Interatech", foreground="#94a3b8")
        lbl_versao.pack(side=tk.RIGHT)

    def _configurar_logging(self):
        """Conecta os logs do gerador_pdf ao console da interface."""
        handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        gerar_pdf.logger.addHandler(handler)

    def _processar_logs(self):
        """Atualiza a caixa de texto com os logs da fila em tempo real."""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
        self.root.after(100, self._processar_logs)

    def _selecionar_json(self):
        """Abre caixa de diálogo para escolher o arquivo JSON."""
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo JSON da Apostila",
            initialdir=os.path.join(DIR_BASE, "data"),
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os Arquivos", "*.*")],
        )
        if caminho:
            self.entry_json.delete(0, tk.END)
            self.entry_json.insert(0, caminho)
            self._atualizar_preview_json()

    def _selecionar_pdf_destino(self):
        """Abre caixa de diálogo para definir onde salvar o PDF."""
        caminho = filedialog.asksaveasfilename(
            title="Salvar PDF como...",
            initialdir=os.path.join(DIR_BASE, "output"),
            defaultextension=".pdf",
            filetypes=[("Documentos PDF", "*.pdf")],
        )
        if caminho:
            self.entry_pdf.delete(0, tk.END)
            self.entry_pdf.insert(0, caminho)

    def _atualizar_preview_json(self):
        """Lê o arquivo JSON atual e atualiza os rótulos de prévia."""
        caminho_json = self.entry_json.get().strip()
        if not os.path.isfile(caminho_json):
            self.lbl_prev_titulo.config(text="Arquivo não encontrado", foreground="#ef4444")
            self.lbl_prev_autor.config(text="---", foreground="#64748b")
            self.lbl_prev_caps.config(text="---", foreground="#64748b")
            return

        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                dados = json.load(f)

            metadados = dados.get("metadados", {})
            titulo = metadados.get("titulo", dados.get("title", "Sem Título"))
            autor = metadados.get("autor", "Não especificado")
            instituicao = metadados.get("instituicao", "")
            autor_completo = f"{autor} ({instituicao})" if instituicao else autor
            capitulos = dados.get("capitulos", dados.get("sections", []))

            self.lbl_prev_titulo.config(text=titulo[:60] + ("..." if len(titulo) > 60 else ""), foreground=self.cor_primaria)
            self.lbl_prev_autor.config(text=autor_completo[:60], foreground="#334155")
            self.lbl_prev_caps.config(text=f"{len(capitulos)} capítulo(s)", foreground="#059669")
        except Exception:
            self.lbl_prev_titulo.config(text="Erro de sintaxe no JSON", foreground="#ef4444")
            self.lbl_prev_autor.config(text="---", foreground="#64748b")
            self.lbl_prev_caps.config(text="---", foreground="#64748b")

    def _executar_geracao(self):
        """Inicia a geração do PDF em uma thread separada para não travar a GUI."""
        caminho_json = self.entry_json.get().strip()
        caminho_pdf = self.entry_pdf.get().strip()
        abrir = self.var_abrir.get()

        if not os.path.isfile(caminho_json):
            messagebox.showerror("Arquivo Ausente", f"O arquivo JSON especificado não existe:\n{caminho_json}")
            return

        # Desabilita o botão e inicia a barra de progresso
        self.btn_gerar.config(state=tk.DISABLED, text="⏳ Gerando Apostila...")
        self.progress.start(10)

        def worker():
            sucesso = False
            pdf_final = None
            try:
                pdf_final = gerar_pdf.gerar_apostila(
                    caminho_json=caminho_json,
                    caminho_saida_pdf=caminho_pdf,
                    abrir_ao_concluir=abrir,
                )
                sucesso = True
            except Exception as erro:
                gerar_pdf.logger.error("Erro na thread de geração: %s", erro)
            finally:
                self.root.after(0, lambda: self._finalizar_geracao(sucesso, pdf_final))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _finalizar_geracao(self, sucesso: bool, caminho_pdf: Optional[str]):
        """Restaura o estado da GUI após o término da geração."""
        self.progress.stop()
        self.btn_gerar.config(state=tk.NORMAL, text="🚀 Gerar Apostila em PDF")

        if sucesso and caminho_pdf and os.path.isfile(caminho_pdf):
            self.ultimo_pdf_gerado = caminho_pdf
            self.btn_abrir_pdf.config(state=tk.NORMAL)
            messagebox.showinfo("Sucesso!", f"Apostila gerada com sucesso!\n\nArquivo salvo em:\n{caminho_pdf}")
        else:
            messagebox.showerror("Erro", "Não foi possível gerar a apostila. Verifique os logs no console da janela para mais detalhes.")

    def _abrir_pasta_saida(self):
        """Abre o diretório onde os PDFs são salvos."""
        pasta = os.path.abspath(os.path.dirname(self.entry_pdf.get().strip()))
        os.makedirs(pasta, exist_ok=True)
        gerar_pdf.abrir_arquivo(pasta)

    def _abrir_pdf_gerado(self):
        """Abre o último PDF gerado."""
        if self.ultimo_pdf_gerado and os.path.isfile(self.ultimo_pdf_gerado):
            gerar_pdf.abrir_arquivo(self.ultimo_pdf_gerado)
        else:
            caminho_pdf = self.entry_pdf.get().strip()
            if os.path.isfile(caminho_pdf):
                gerar_pdf.abrir_arquivo(caminho_pdf)


def iniciar_interface():
    """Ponto de entrada para iniciar a interface Tkinter."""
    root = tk.Tk()
    app = GeradorApostilaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    iniciar_interface()
