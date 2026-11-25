# 📘 Gerador Automatizado de Apostilas em PDF

Sistema completo em Python para geração automatizada de apostilas e materiais didáticos profissionais em PDF a partir de esquemas JSON estruturados e templates HTML/CSS de alta fidelidade.

Projetado para operar de forma desacoplada como um motor de renderização independente, ideal para ser conectado a fluxos de **n8n**, APIs externas ou prompts de **Inteligência Artificial (LLMs)**.

---

## 🌟 Principais Recursos

- **Motor de Renderização Nativo:** Utiliza o motor Chromium do **Microsoft Edge** ou **Google Chrome** em modo headless (`--print-to-pdf`), com suporte total a HTML5, CSS Flexbox, gradientes, sombras e regras `@page` (sem dependências nativas como Cairo ou GTK).
- **Validador Inteligente de JSON:** Diagnóstico aprofundado com indicação exata de erros de sintaxe (linha/coluna), inconsistência de schema, cores hexadecimais inválidas e blocos desconhecidos.
- **Três Formas de Utilização:**
  1. 🌐 **Web Studio (`app_web.py`):** Interface web moderna no navegador com upload, editor ao vivo, relatório de erros e prévia embutida de PDF.
  2. 🖥️ **Desktop GUI (`app_gui.py`):** Aplicação desktop rápida em Tkinter com seleção de arquivos e logs em tempo real.
  3. ⚡ **Linha de Comando (CLI - `gerar_pdf.py`):** Executável flexível com argumentos para automação e scripts.
- **Padrão de Blocos Polimórficos:** Suporte nativo a 7 tipos de blocos estruturais pedagógicos: `paragrafo`, `subtitulo`, `lista`, `destaque`, `tabela`, `imagem` e `link`.
- **Prompts Mestre & Formulário para IA:** Modelos prontos para instruir ChatGPT, Claude, Gemini ou DeepSeek a gerar conteúdos diretamente no padrão do sistema.

---

## 📂 Estrutura do Projeto

```text
gerador-de-apostila/
├── assets/
│   ├── logo.png                     # Logotipo institucional da capa
│   └── diagrama_exemplo.png         # Diagrama/figura de exemplo
├── data/
│   ├── apostila_v1.json             # Exemplo funcional de apostila (n8n)
│   ├── molde_schema_modelo.json     # Molde JSON em branco pronto para uso
│   ├── PROMPTS_MESTRE_E_FORMULARIO.md # Prompts de IA para preenchimento
│   └── SCHEMA_GUIA.md               # Guia técnico do esquema de dados
├── templates/
│   ├── base.html                    # Template estrutural em Jinja2
│   └── style.css                    # Estilização completa e regras de página A4
├── output/                          # Diretório onde os PDFs são salvos
├── app_web.py                       # Interface Web Studio (Flask)
├── app_gui.py                       # Interface Desktop (Tkinter)
├── validador.py                     # Motor de validação inteligente de JSON
├── gerar_pdf.py                     # Script orquestrador e CLI
├── iniciar_web.bat                  # Inicializador rápido do Web Studio no Windows
├── iniciar_gui.bat                  # Inicializador rápido da Desktop GUI no Windows
├── requirements.txt                 # Dependências Python mínimas
└── README.md                        # Documentação do projeto
```

---

## 🚀 Instalação Rápida

1. Clone o repositório:
```bash
git clone https://github.com/Igorls34/gerador-de-apostila.git
cd gerador-de-apostila
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

---

## 💻 Como Utilizar

### 1. Web Studio (Recomendado para Usuários)
Inicie pelo atalho [iniciar_web.bat](iniciar_web.bat) ou via terminal:
```bash
python app_web.py
```
O navegador abrirá automaticamente em `http://127.0.0.1:5000`. Você poderá:
- Selecionar um JSON de exemplo ou fazer upload do seu próprio arquivo.
- Visualizar erros e avisos com destaque visual e sugestão de correção.
- Gerar e pré-visualizar o PDF diretamente na tela.

### 2. Interface Gráfica Desktop (GUI)
Inicie pelo atalho [iniciar_gui.bat](iniciar_gui.bat) ou via terminal:
```bash
python app_gui.py
```

### 3. Linha de Comando (CLI)
```bash
# Execução padrão
python gerar_pdf.py

# Informando arquivo JSON e destino
python gerar_pdf.py -j "data/apostila_v1.json" -o "output/MinhaApostila.pdf"

# Gerando e abrindo automaticamente
python gerar_pdf.py -j "data/apostila_v1.json" --open
```

---

## 📐 Esquema do JSON (Exemplo Rápido)

```json
{
  "metadados": {
    "titulo": "Título da Apostila",
    "subtitulo": "Subtítulo do material",
    "autor": "Nome do Autor",
    "instituicao": "Nome da Instituição",
    "versao": "1.0 - 2026",
    "logo_path": "assets/logo.png",
    "cor_primaria": "#0056b3",
    "cor_secundaria": "#00a8e8"
  },
  "capitulos": [
    {
      "numero": "01",
      "titulo": "Introdução",
      "blocos": [
        { "tipo": "paragrafo", "conteudo": "Texto explicativo..." },
        { "tipo": "subtitulo", "conteudo": "Conceitos Chave" },
        { "tipo": "destaque", "titulo": "Nota", "conteudo": "Dica importante..." },
        { "tipo": "lista", "estilo": "bullet", "itens": ["Item 1", "Item 2"] }
      ]
    }
  ]
}
```

Consulte [SCHEMA_GUIA.md](data/SCHEMA_GUIA.md) para detalhes completos de cada bloco e [PROMPTS_MESTRE_E_FORMULARIO.md](data/PROMPTS_MESTRE_E_FORMULARIO.md) para gerar conteúdo via IA.

---

## 📄 Licença
Distribuído sob a licença MIT. Sinta-se livre para utilizar e customizar em seus próprios projetos!
