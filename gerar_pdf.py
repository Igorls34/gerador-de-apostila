import argparse
import datetime
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

# ==============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
DIR_BASE: str = os.path.abspath(os.path.dirname(__file__))
DIR_TEMPLATES: str = os.path.join(DIR_BASE, "templates")
DIR_OUTPUT: str = os.path.join(DIR_BASE, "output")
DIR_ASSETS: str = os.path.join(DIR_BASE, "assets")

CAMINHO_JSON_PADRAO: str = os.path.join(DIR_BASE, "data", "apostila_v1.json")
CAMINHO_SAIDA_PDF_PADRAO: str = os.path.join(DIR_OUTPUT, "Apostila_n8n_v1.pdf")
TEMPLATE_PADRAO: str = "base.html"

FORMATO_DATA_HORA: str = "%d/%m/%Y %H:%M:%S"
FORMATO_LOG: str = "%(asctime)s | %(levelname)-7s | %(message)s"

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format=FORMATO_LOG, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("gerador_apostila")


# ==============================================================================
# DETECÇÃO DE MOTORES DE RENDERIZAÇÃO PDF
# ==============================================================================
def localizar_navegador() -> Optional[str]:
    """Localiza o executável do Microsoft Edge ou Google Chrome no sistema."""
    candidatos = [
        # Edge (Padrão nativo do Windows 10/11)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        # Local AppData (instalações por usuário)
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]

    for caminho in candidatos:
        if os.path.isfile(caminho):
            return caminho

    # Tenta encontrar via PATH
    for cmd in ["msedge", "chrome", "chromium", "google-chrome"]:
        encontrado = shutil.which(cmd)
        if encontrado:
            return encontrado

    return None


def converter_via_navegador(caminho_html: str, caminho_pdf: str, navegador_exe: str) -> None:
    """Converte HTML para PDF usando o motor nativo Chromium (Edge ou Chrome headless)."""
    uri_html = "file:///" + os.path.abspath(caminho_html).replace("\\", "/")
    
    cmd = [
        navegador_exe,
        "--headless",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--enable-local-file-access",
        "--no-pdf-header-footer",
        f"--print-to-pdf={caminho_pdf}",
        uri_html,
    ]

    logger.debug("[MOTOR] Executando comando: %s", " ".join(cmd))
    resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if resultado.returncode != 0:
        logger.error("[MOTOR] Erro na conversão do navegador: %s", resultado.stderr)
        raise RuntimeError(f"O navegador retornou código de erro {resultado.returncode}: {resultado.stderr}")


def converter_via_pdfkit(html_content: str, caminho_pdf: str) -> bool:
    """Tenta converter via pdfkit / wkhtmltopdf caso esteja disponível."""
    try:
        import pdfkit
        opcoes = {
            "enable-local-file-access": "",
            "encoding": "UTF-8",
            "quiet": "",
        }
        pdfkit.from_string(html_content, caminho_pdf, options=opcoes)
        return True
    except Exception as exc:
        logger.debug("[PDFKIT] Não foi possível usar pdfkit: %s", exc)
        return False


def converter_via_weasyprint(html_content: str, caminho_pdf: str, base_url: str) -> bool:
    """Tenta converter via weasyprint caso as DLLs nativas estejam instaladas."""
    try:
        from weasyprint import HTML
        HTML(string=html_content, base_url=base_url).write_pdf(caminho_pdf)
        return True
    except Exception as exc:
        logger.debug("[WEASYPRINT] Não foi possível usar weasyprint: %s", exc)
        return False


# ==============================================================================
# PIPELINE PRINCIPAL
# ==============================================================================
def carregar_dados(caminho_json: str) -> dict[str, Any]:
    """Carrega e valida o arquivo JSON com os dados da apostila."""
    caminho_resolvido = caminho_json if os.path.isabs(caminho_json) else os.path.abspath(caminho_json)
    if not os.path.isfile(caminho_resolvido):
        caminho_alt = os.path.join(DIR_BASE, caminho_json)
        if os.path.isfile(caminho_alt):
            caminho_resolvido = caminho_alt
        else:
            raise FileNotFoundError(f"Arquivo de dados não encontrado: {caminho_json}")

    with open(caminho_resolvido, "r", encoding="utf-8") as f:
        dados = json.load(f)

    if not isinstance(dados, dict):
        raise ValueError("O formato do JSON deve conter um objeto raiz com chaves 'metadados' e 'capitulos'.")

    return dados


def renderizar_template(dados: dict[str, Any], nome_template: str = TEMPLATE_PADRAO) -> str:
    """Renderiza o template Jinja2 injetando as variáveis do JSON."""
    env = Environment(loader=FileSystemLoader(DIR_TEMPLATES), autoescape=False)
    template = env.get_template(nome_template)

    metadados = dados.get("metadados", {})
    capitulos = dados.get("capitulos", dados.get("sections", []))
    data_formatada = datetime.datetime.now().strftime(FORMATO_DATA_HORA)
    base_href = "file:///" + DIR_BASE.replace("\\", "/")

    return template.render(
        metadados=metadados,
        capitulos=capitulos,
        base_href=base_href,
        generated_date=data_formatada,
        title=metadados.get("titulo", "Apostila"),
    )


def gerar_apostila(
    caminho_json: str = CAMINHO_JSON_PADRAO,
    caminho_saida_pdf: str = CAMINHO_SAIDA_PDF_PADRAO,
    abrir_ao_concluir: bool = False,
) -> str:
    """Função orquestradora: processa o JSON, renderiza o HTML e cria o arquivo PDF final."""
    inicio = time.perf_counter()
    logger.info("▶ Iniciando geração da apostila...")
    logger.info("  Arquivo de origem: %s", caminho_json)
    logger.info("  Arquivo de destino: %s", caminho_saida_pdf)

    # 1. Carregar dados
    dados = carregar_dados(caminho_json)
    qtd_capitulos = len(dados.get("capitulos", []))
    titulo = dados.get("metadados", {}).get("titulo", "Sem Título")
    logger.info("✔ Dados carregados: '%s' (%d capítulo(s))", titulo, qtd_capitulos)

    # 2. Renderizar HTML
    html_renderizado = renderizar_template(dados)
    logger.info("✔ Template renderizado com sucesso.")

    # 3. Preparar diretório de saída
    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida_pdf)), exist_ok=True)
    caminho_pdf_abs = os.path.abspath(caminho_saida_pdf)

    # 4. Seleção e execução do motor de PDF
    navegador = localizar_navegador()
    pdf_gerado = False

    if navegador:
        nome_motor = "Microsoft Edge" if "msedge" in navegador.lower() else "Google Chrome"
        logger.info("✔ Motor selecionado: %s (Nativo / Alta fidelidade CSS)", nome_motor)

        # Salva HTML temporário para renderização do navegador
        caminho_html_temp = os.path.join(DIR_OUTPUT, ".temp_apostila_render.html")
        with open(caminho_html_temp, "w", encoding="utf-8") as f:
            f.write(html_renderizado)

        try:
            converter_via_navegador(caminho_html_temp, caminho_pdf_abs, navegador)
            pdf_gerado = os.path.isfile(caminho_pdf_abs) and os.path.getsize(caminho_pdf_abs) > 0
        finally:
            if os.path.isfile(caminho_html_temp):
                try:
                    os.remove(caminho_html_temp)
                except OSError:
                    pass

    # Fallback 1: pdfkit
    if not pdf_gerado:
        logger.info("Tentando motor alternativo (pdfkit/wkhtmltopdf)...")
        pdf_gerado = converter_via_pdfkit(html_renderizado, caminho_pdf_abs)

    # Fallback 2: weasyprint
    if not pdf_gerado:
        logger.info("Tentando motor alternativo (weasyprint)...")
        pdf_gerado = converter_via_weasyprint(html_renderizado, caminho_pdf_abs, DIR_TEMPLATES)

    if not pdf_gerado:
        raise RuntimeError(
            "Nenhum motor de PDF compatível pôde gerar o arquivo. "
            "Certifique-se de que o Microsoft Edge, Google Chrome ou wkhtmltopdf esteja disponível."
        )

    tamanho_kb = os.path.getsize(caminho_pdf_abs) / 1024
    tempo_total = time.perf_counter() - inicio
    logger.info("🎉 PDF gerado com sucesso!")
    logger.info("   Destino: %s", caminho_pdf_abs)
    logger.info("   Tamanho: %.1f KB", tamanho_kb)
    logger.info("   Tempo:   %.2f segundos", tempo_total)

    if abrir_ao_concluir and os.path.isfile(caminho_pdf_abs):
        abrir_arquivo(caminho_pdf_abs)

    return caminho_pdf_abs


def abrir_arquivo(caminho: str) -> None:
    """Abre um arquivo no visualizador padrão do sistema operacional."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", caminho], check=False)
        else:
            subprocess.run(["xdg-open", caminho], check=False)
    except Exception as exc:
        logger.warning("Não foi possível abrir o arquivo automaticamente: %s", exc)


def parse_argumentos() -> argparse.Namespace:
    """Configura o leitor de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Gerador Automatizado de Apostilas em PDF a partir de JSON e HTML/CSS.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-j", "--json",
        dest="caminho_json",
        default=CAMINHO_JSON_PADRAO,
        help="Caminho do arquivo JSON de entrada contendo metadados e capítulos.",
    )
    parser.add_argument(
        "-o", "--output",
        dest="caminho_saida",
        default=CAMINHO_SAIDA_PDF_PADRAO,
        help="Caminho do arquivo PDF de saída que será gerado.",
    )
    parser.add_argument(
        "--open",
        dest="abrir",
        action="store_true",
        help="Abre o arquivo PDF no leitor padrão assim que a geração for concluída.",
    )
    parser.add_argument(
        "--gui",
        dest="iniciar_gui",
        action="store_true",
        help="Inicia a interface gráfica amigável (GUI).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_argumentos()

    if args.iniciar_gui:
        try:
            import app_gui
            app_gui.iniciar_interface()
        except ImportError:
            logger.error("Módulo app_gui não encontrado para iniciar a interface gráfica.")
            sys.exit(1)
    else:
        try:
            gerar_apostila(
                caminho_json=args.caminho_json,
                caminho_saida_pdf=args.caminho_saida,
                abrir_ao_concluir=args.abrir,
            )
        except Exception as erro:
            logger.error("❌ Falha na geração: %s", erro)
            sys.exit(1)
