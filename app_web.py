import json
import logging
import os
import re
import sys
import threading
import time
import webbrowser
from typing import Any, Dict

from flask import Flask, jsonify, render_template_string, request, send_from_directory

import gerar_pdf
import validador

DIR_BASE = os.path.abspath(os.path.dirname(__file__))
DIR_DATA = os.path.join(DIR_BASE, "data")
DIR_OUTPUT = os.path.join(DIR_BASE, "output")
os.makedirs(DIR_OUTPUT, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerador de Apostilas em PDF • Web Studio</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        :root {
            --cor-primaria: #0056b3;
            --cor-secundaria: #00a8e8;
            --cor-fundo: #0f172a;
        }
        body {
            background-color: #f1f5f9;
            color: #1e293b;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            min-height: 100vh;
        }
        .navbar-brand {
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .card-custom {
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            background: #ffffff;
            transition: all 0.2s ease-in-out;
        }
        .editor-textarea {
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            background-color: #0f172a;
            color: #e2e8f0;
            border-radius: 8px;
            border: 1px solid #334155;
            resize: vertical;
            min-height: 480px;
        }
        .editor-textarea:focus {
            background-color: #0f172a;
            color: #ffffff;
            border-color: var(--cor-secundaria);
            box-shadow: 0 0 0 0.25rem rgba(0, 168, 232, 0.25);
        }
        .badge-block {
            font-size: 11px;
            padding: 4px 8px;
            background-color: #e2e8f0;
            color: #334155;
            border-radius: 6px;
            margin: 2px;
            display: inline-block;
        }
        .status-badge {
            font-size: 13px;
            padding: 6px 12px;
            border-radius: 20px;
        }
        .btn-action {
            background-color: var(--cor-primaria);
            color: white;
            font-weight: 600;
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
        }
        .btn-action:hover {
            background-color: #004085;
            color: white;
        }
        .pdf-preview-frame {
            width: 100%;
            height: 600px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
        }
        .drop-zone {
            border: 2px dashed #cbd5e1;
            border-radius: 8px;
            padding: 18px;
            text-align: center;
            background-color: #f8fafc;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .drop-zone:hover {
            border-color: var(--cor-secundaria);
            background-color: #f0f9ff;
        }
    </style>
</head>
<body>

<nav class="navbar navbar-dark bg-dark px-4 py-3 shadow-sm" style="background: linear-gradient(90deg, #0f172a 0%, #0056b3 100%) !important;">
    <div class="container-fluid">
        <span class="navbar-brand mb-0 h1 d-flex align-items-center gap-2">
            <i class="bi bi-file-earmark-pdf-fill text-info fs-4"></i>
            <span>Gerador de Apostilas em PDF</span>
            <span class="badge bg-info text-dark ms-2 fw-semibold">Web Studio</span>
        </span>
        <div class="d-flex align-items-center gap-3 small">
            <button class="btn btn-outline-info btn-sm fw-semibold d-flex align-items-center gap-1" data-bs-toggle="modal" data-bs-target="#modalPrompts" onclick="carregarPrompts()">
                <i class="bi bi-magic"></i> Prompts para IA
            </button>
            <span class="text-white-50"><i class="bi bi-check-circle-fill text-success"></i> Motor Chromium Ativo</span>
        </div>
    </div>
</nav>

<div class="container-fluid px-4 py-4">
    <div class="row g-4">
        
        <!-- COLUNA ESQUERDA: EDITOR E CARREGAMENTO DE JSON -->
        <div class="col-lg-6">
            <div class="card card-custom p-4 h-100">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold mb-0 text-primary d-flex align-items-center gap-2">
                        <i class="bi bi-braces"></i> Conteúdo JSON
                    </h5>
                    <div class="d-flex gap-2">
                        <select id="selectExemplos" class="form-select form-select-sm" style="width: auto;" onchange="carregarExemplo()">
                            <option value="">📂 Carregar Exemplo...</option>
                        </select>
                        <button class="btn btn-sm btn-outline-secondary" onclick="limparEditor()" title="Limpar editor">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>

                <!-- DROPZONE / UPLOAD -->
                <div class="drop-zone mb-3" onclick="document.getElementById('inputArquivo').click()">
                    <i class="bi bi-cloud-arrow-up text-primary fs-3 d-block mb-1"></i>
                    <span class="fw-semibold text-secondary">Clique para selecionar um arquivo .JSON</span> ou arraste aqui
                    <input type="file" id="inputArquivo" accept=".json" style="display: none;" onchange="aoSelecionarArquivo(event)">
                </div>

                <!-- TEXTAREA EDITOR -->
                <div class="mb-3 position-relative">
                    <textarea id="jsonEditor" class="form-control editor-textarea p-3" placeholder="Cole ou digite aqui seu JSON..."></textarea>
                </div>

                <div class="d-flex justify-content-between align-items-center">
                    <button class="btn btn-outline-primary fw-semibold" onclick="validarJSON()">
                        <i class="bi bi-shield-check"></i> Validar Estrutura
                    </button>
                    <button class="btn btn-action" id="btnGerar" onclick="gerarPDF()">
                        <i class="bi bi-rocket-takeoff"></i> Gerar Apostila PDF
                    </button>
                </div>
            </div>
        </div>

        <!-- COLUNA DIREITA: VALIDAÇÃO, RELATÓRIO E PRÉVIA -->
        <div class="col-lg-6">
            <div class="card card-custom p-4 h-100">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold mb-0 text-primary d-flex align-items-center gap-2">
                        <i class="bi bi-clipboard2-pulse"></i> Diagnóstico e Resultado
                    </h5>
                    <span id="badgeStatus" class="status-badge bg-secondary text-white">Aguardando Validação</span>
                </div>

                <!-- CARD DE RESUMO ESTRUTURAL -->
                <div id="painelResumo" class="alert alert-light border p-3 mb-3 d-none">
                    <div class="row g-2 small">
                        <div class="col-sm-6">
                            <strong>Título:</strong> <span id="resTitulo" class="text-primary fw-bold">-</span>
                        </div>
                        <div class="col-sm-6">
                            <strong>Autor:</strong> <span id="resAutor">-</span>
                        </div>
                        <div class="col-sm-6">
                            <strong>Capítulos:</strong> <span id="resCapitulos" class="badge bg-primary">-</span>
                        </div>
                        <div class="col-sm-6">
                            <strong>Total de Blocos:</strong> <span id="resBlocos" class="badge bg-secondary">-</span>
                        </div>
                        <div class="col-12 mt-2">
                            <strong>Distribuição de Blocos:</strong>
                            <div id="resDistribuicao" class="mt-1"></div>
                        </div>
                    </div>
                </div>

                <!-- PAINEL DE ERROS CRÍTICOS -->
                <div id="painelErros" class="d-none mb-3">
                    <div class="alert alert-danger mb-0">
                        <h6 class="fw-bold d-flex align-items-center gap-2 mb-2">
                            <i class="bi bi-x-octagon-fill"></i> Erros Críticos Identificados (<span id="qtdErros">0</span>)
                        </h6>
                        <div id="listaErros" class="small" style="max-height: 220px; overflow-y: auto;"></div>
                    </div>
                </div>

                <!-- PAINEL DE AVISOS / BOAS PRÁTICAS -->
                <div id="painelAvisos" class="d-none mb-3">
                    <div class="alert alert-warning mb-0">
                        <h6 class="fw-bold d-flex align-items-center gap-2 mb-2">
                            <i class="bi bi-exclamation-triangle-fill"></i> Alertas e Recomendações (<span id="qtdAvisos">0</span>)
                        </h6>
                        <div id="listaAvisos" class="small" style="max-height: 180px; overflow-y: auto;"></div>
                    </div>
                </div>

                <!-- PAINEL DE SUCESSO E DOWNLOAD DE PDF -->
                <div id="painelPDF" class="d-none flex-grow-1 d-flex flex-column">
                    <div class="alert alert-success d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <i class="bi bi-check-circle-fill me-1"></i>
                            <strong>PDF gerado com sucesso!</strong>
                            <span id="pdfMetricas" class="small text-muted ms-2"></span>
                        </div>
                        <a id="btnDownloadPDF" href="#" class="btn btn-sm btn-success fw-bold" target="_blank" download>
                            <i class="bi bi-download"></i> Baixar PDF
                        </a>
                    </div>
                    <iframe id="iframePDF" class="pdf-preview-frame flex-grow-1" src=""></iframe>
                </div>

                <!-- PLACEHOLDER INICIAL -->
                <div id="painelPlaceholder" class="text-center text-muted my-auto py-5">
                    <i class="bi bi-file-earmark-code fs-1 d-block mb-2 text-secondary"></i>
                    <p class="mb-1 fw-semibold">Nenhuma validação realizada ainda.</p>
                    <p class="small text-secondary">Carregue ou cole um JSON à esquerda e clique em <strong>Validar Estrutura</strong> ou <strong>Gerar Apostila</strong>.</p>
                </div>

            </div>
        </div>

    </div>
</div>

<script>
let dadosExemplos = [];

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
    carregarListaExemplos();
});

// Busca lista de JSONs disponíveis na pasta data/
async function carregarListaExemplos() {
    try {
        const resp = await fetch("/api/arquivos-exemplo");
        const lista = await resp.json();
        const select = document.getElementById("selectExemplos");
        select.innerHTML = '<option value="">📂 Carregar Exemplo...</option>';
        lista.forEach(arquivo => {
            const opt = document.createElement("option");
            opt.value = arquivo;
            opt.textContent = arquivo;
            select.appendChild(opt);
        });

        // Seleciona apostila_v1.json por padrão se existir
        if (lista.includes("apostila_v1.json")) {
            select.value = "apostila_v1.json";
            carregarExemplo();
        }
    } catch (e) {
        console.error("Erro ao listar exemplos:", e);
    }
}

// Carrega o arquivo selecionado no select para o editor
async function carregarExemplo() {
    const nome = document.getElementById("selectExemplos").value;
    if (!nome) return;
    try {
        const resp = await fetch("/api/carregar-arquivo/" + encodeURIComponent(nome));
        const conteudo = await resp.text();
        document.getElementById("jsonEditor").value = conteudo;
        validarJSON();
    } catch (e) {
        alert("Erro ao carregar arquivo de exemplo: " + e);
    }
}

// Upload via input file
function aoSelecionarArquivo(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById("jsonEditor").value = e.target.result;
        validarJSON();
    };
    reader.readAsText(file, "UTF-8");
}

function limparEditor() {
    document.getElementById("jsonEditor").value = "";
    document.getElementById("selectExemplos").value = "";
    resetarPaineis();
}

function resetarPaineis() {
    document.getElementById("painelPlaceholder").classList.remove("d-none");
    document.getElementById("painelResumo").classList.add("d-none");
    document.getElementById("painelErros").classList.add("d-none");
    document.getElementById("painelAvisos").classList.add("d-none");
    document.getElementById("painelPDF").classList.add("d-none");
    document.getElementById("badgeStatus").className = "status-badge bg-secondary text-white";
    document.getElementById("badgeStatus").textContent = "Aguardando Validação";
}

// Validação Inteligente
async function validarJSON() {
    const jsonStr = document.getElementById("jsonEditor").value.trim();
    if (!jsonStr) {
        alert("Por favor, cole ou carregue um JSON antes de validar.");
        return null;
    }

    try {
        const resp = await fetch("/api/validar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ conteudo: jsonStr })
        });
        const resultado = await resp.json();
        exibirResultadoValidacao(resultado);
        return resultado;
    } catch (e) {
        alert("Falha na comunicação com o validador: " + e);
        return null;
    }
}

function exibirResultadoValidacao(res) {
    document.getElementById("painelPlaceholder").classList.add("d-none");

    // Status Badge
    const badge = document.getElementById("badgeStatus");
    if (res.valido) {
        if (res.avisos.length > 0) {
            badge.className = "status-badge bg-warning text-dark";
            badge.textContent = "Válido com Recomendações";
        } else {
            badge.className = "status-badge bg-success text-white";
            badge.textContent = "Estrutura 100% Válida";
        }
    } else {
        badge.className = "status-badge bg-danger text-white";
        badge.textContent = "Estrutura Inválida (" + res.erros.length + " erros)";
    }

    // Painel de Resumo
    if (res.resumo && res.resumo.titulo) {
        document.getElementById("painelResumo").classList.remove("d-none");
        document.getElementById("resTitulo").textContent = res.resumo.titulo;
        document.getElementById("resAutor").textContent = res.resumo.autor + (res.resumo.instituicao ? " (" + res.resumo.instituicao + ")" : "");
        document.getElementById("resCapitulos").textContent = res.resumo.total_capitulos + " capítulos";
        document.getElementById("resBlocos").textContent = res.resumo.total_blocos + " blocos";

        const divDist = document.getElementById("resDistribuicao");
        divDist.innerHTML = "";
        for (const [tipo, qtd] of Object.entries(res.resumo.contagem_blocos || {})) {
            divDist.innerHTML += `<span class="badge-block"><strong>${tipo}:</strong> ${qtd}</span>`;
        }
    } else {
        document.getElementById("painelResumo").classList.add("d-none");
    }

    // Painel de Erros
    const painelErros = document.getElementById("painelErros");
    const listaErros = document.getElementById("listaErros");
    if (res.erros && res.erros.length > 0) {
        painelErros.classList.remove("d-none");
        document.getElementById("qtdErros").textContent = res.erros.length;
        listaErros.innerHTML = "";
        res.erros.forEach((err, idx) => {
            listaErros.innerHTML += `
                <div class="mb-2 p-2 bg-white rounded border border-danger-subtle">
                    <strong class="text-danger">[${err.categoria}]</strong> em <code>${err.localizacao}</code><br>
                    <span>${err.mensagem}</span>
                    ${err.trecho ? `<pre class="bg-dark text-warning p-2 mt-1 rounded small mb-1"><code>${err.trecho}</code></pre>` : ''}
                    <div class="text-muted mt-1 small">💡 <em>Sugestão: ${err.sugestao}</em></div>
                </div>
            `;
        });
    } else {
        painelErros.classList.add("d-none");
    }

    // Painel de Avisos
    const painelAvisos = document.getElementById("painelAvisos");
    const listaAvisos = document.getElementById("listaAvisos");
    if (res.avisos && res.avisos.length > 0) {
        painelAvisos.classList.remove("d-none");
        document.getElementById("qtdAvisos").textContent = res.avisos.length;
        listaAvisos.innerHTML = "";
        res.avisos.forEach(av => {
            listaAvisos.innerHTML += `
                <div class="mb-2 p-2 bg-white rounded border border-warning-subtle">
                    <strong class="text-warning-emphasis">[${av.categoria}]</strong> em <code>${av.localizacao}</code><br>
                    <span>${av.mensagem}</span>
                    <div class="text-muted mt-1 small">💡 <em>Recomendação: ${av.sugestao}</em></div>
                </div>
            `;
        });
    } else {
        painelAvisos.classList.add("d-none");
    }
}

// Geração de PDF
async function gerarPDF() {
    const jsonStr = document.getElementById("jsonEditor").value.trim();
    if (!jsonStr) {
        alert("Insira um JSON antes de gerar o PDF.");
        return;
    }

    const btn = document.getElementById("btnGerar");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Gerando PDF...';

    // Primeiro valida
    const validacao = await validarJSON();
    if (!validacao || !validacao.valido) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-rocket-takeoff"></i> Gerar Apostila PDF';
        alert("Não é possível gerar o PDF pois o documento contém erros críticos. Corrija-os e tente novamente.");
        return;
    }

    try {
        const resp = await fetch("/api/gerar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ conteudo: jsonStr })
        });
        const resultado = await resp.json();

        if (resultado.sucesso) {
            const painelPDF = document.getElementById("painelPDF");
            painelPDF.classList.remove("d-none");
            document.getElementById("btnDownloadPDF").href = resultado.url_pdf;
            document.getElementById("iframePDF").src = resultado.url_pdf;
            document.getElementById("pdfMetricas").textContent = `(${resultado.tamanho_kb} KB gerados em ${resultado.tempo_s}s)`;
            painelPDF.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert("Erro ao gerar o PDF: " + resultado.erro);
        }
    } catch (e) {
        alert("Erro na requisição de geração: " + e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-rocket-takeoff"></i> Gerar Apostila PDF';
    }
}

let promptsCarregados = false;
let templateFormularioBase = "";

async function carregarPrompts() {
    if (promptsCarregados) return;
    try {
        const resp = await fetch("/api/prompts");
        const data = await resp.json();
        document.getElementById("txtPromptMestre").value = data.prompt_mestre || "Prompt Mestre não encontrado.";
        templateFormularioBase = data.prompt_formulario || "";
        document.getElementById("txtPromptFormulario").value = templateFormularioBase;
        promptsCarregados = true;
    } catch (e) {
        console.error("Erro ao carregar prompts:", e);
    }
}

function atualizarFormularioDinamico() {
    const tema = document.getElementById("fTema").value.trim() || "[Digite aqui o tema da apostila]";
    const subtitulo = document.getElementById("fSubtitulo").value.trim() || "[Digite aqui o subtítulo ou o objetivo da apostila]";
    const publico = document.getElementById("fPublico").value.trim() || "[Ex: Iniciante, Intermediário, Avançado / Profissionais de TI / Alunos]";
    const autor = document.getElementById("fAutor").value.trim() || "[Digite o nome do autor]";
    const inst = document.getElementById("fInst").value.trim() || "[Digite o nome da empresa ou escola]";
    const versao = document.getElementById("fVersao").value.trim() || "1.0 - 2026";
    const caps = document.getElementById("fCaps").value.trim() || "[Ex: 3 capítulos detalhados]";
    const topicos = document.getElementById("fTopicos").value.trim() || "- [Tópico 1...]\n   - [Tópico 2...]";
    const cores = document.getElementById("fCores").value.trim() || "Deixe a IA escolher";

    const texto = `Por favor, gere a apostila completa em formato JSON seguindo rigorosamente o esquema técnico e as regras estabelecidas no Prompt Mestre.

Abaixo estão os dados do formulário de solicitação:

[FORMULÁRIO DE GERAÇÃO DA APOSTILA]
--------------------------------------------------------------------------------
1. TEMA PRINCIPAL: 
   ${tema}

2. SUBTÍTULO / FOCO DO MATERIAL: 
   ${subtitulo}

3. PÚBLICO-ALVO E NÍVEL: 
   ${publico}

4. NOME DO AUTOR: 
   ${autor}

5. NOME DA INSTITUIÇÃO / EMPRESA: 
   ${inst}

6. VERSÃO / ANO: 
   ${versao}

7. QUANTIDADE DE CAPÍTULOS DESEJADA: 
   ${caps}

8. TÓPICOS ESPECÍFICOS QUE NÃO PODEM FALTAR (OPCIONAL):
   ${topicos.replace(/\\n/g, '\\n   ')}

9. PREFERÊNCIA DE CORES OU IDENTIDADE (OPCIONAL): 
   ${cores}
--------------------------------------------------------------------------------

Retorne apenas o JSON puro, formatado e pronto para renderização.`;

    document.getElementById("txtPromptFormulario").value = texto;
}

async function copiarTexto(elementId, btnElement) {
    const texto = document.getElementById(elementId).value;
    try {
        await navigator.clipboard.writeText(texto);
        const originalHtml = btnElement.innerHTML;
        btnElement.innerHTML = '<i class="bi bi-check-lg"></i> Copiado!';
        btnElement.classList.replace("btn-primary", "btn-success");
        setTimeout(() => {
            btnElement.innerHTML = originalHtml;
            btnElement.classList.replace("btn-success", "btn-primary");
        }, 2000);
    } catch (e) {
        alert("Erro ao copiar: " + e);
    }
}
</script>

<!-- MODAL DE PROMPTS PARA IA -->
<div class="modal fade" id="modalPrompts" tabindex="-1" aria-labelledby="modalPromptsLabel" aria-hidden="true">
    <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header bg-dark text-white" style="background: linear-gradient(90deg, #0f172a 0%, #0056b3 100%);">
                <h5 class="modal-title fw-bold d-flex align-items-center gap-2" id="modalPromptsLabel">
                    <i class="bi bi-magic text-info"></i> Prompts de Preenchimento via IA
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Fechar"></button>
            </div>
            <div class="modal-body bg-light">
                <ul class="nav nav-tabs mb-3" id="promptsTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active fw-semibold" id="tab-mestre-btn" data-bs-toggle="tab" data-bs-target="#tab-mestre" type="button" role="tab">
                            🧠 1. Prompt Mestre (System / Zero-Shot)
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link fw-semibold" id="tab-form-btn" data-bs-toggle="tab" data-bs-target="#tab-form" type="button" role="tab">
                            📝 2. Prompt de Formulário (User Prompt)
                        </button>
                    </li>
                </ul>

                <div class="tab-content" id="promptsTabsContent">
                    <!-- TAB 1: PROMPT MESTRE -->
                    <div class="tab-pane fade show active" id="tab-mestre" role="tabpanel">
                        <div class="alert alert-info small d-flex justify-content-between align-items-center py-2">
                            <span><strong>Onde usar:</strong> Cole no campo <em>System Message</em> da sua IA (ChatGPT, Claude, Gemini ou nó AI do n8n). Ele define todas as regras e o schema JSON.</span>
                            <button class="btn btn-primary btn-sm fw-semibold text-nowrap ms-2" onclick="copiarTexto('txtPromptMestre', this)">
                                <i class="bi bi-clipboard"></i> Copiar Prompt Mestre
                            </button>
                        </div>
                        <textarea id="txtPromptMestre" class="form-control editor-textarea p-3" style="min-height: 420px;" readonly></textarea>
                    </div>

                    <!-- TAB 2: PROMPT DE FORMULÁRIO -->
                    <div class="tab-pane fade" id="tab-form" role="tabpanel">
                        <div class="alert alert-info small d-flex justify-content-between align-items-center py-2">
                            <span><strong>Onde usar:</strong> Preencha os campos abaixo para montar seu pedido personalizado e envie para a IA após configurar o Prompt Mestre.</span>
                            <button class="btn btn-primary btn-sm fw-semibold text-nowrap ms-2" onclick="copiarTexto('txtPromptFormulario', this)">
                                <i class="bi bi-clipboard"></i> Copiar Formulário
                            </button>
                        </div>
                        <div class="row g-3">
                            <div class="col-md-5">
                                <div class="card p-3 border-0 shadow-sm h-100">
                                    <h6 class="fw-bold text-primary mb-3">Preenchimento Rápido</h6>
                                    <div class="mb-2">
                                        <label class="form-label small fw-semibold mb-1">1. Tema Principal</label>
                                        <input type="text" id="fTema" class="form-control form-control-sm" placeholder="Ex: Automação com n8n" oninput="atualizarFormularioDinamico()">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label small fw-semibold mb-1">2. Subtítulo / Foco</label>
                                        <input type="text" id="fSubtitulo" class="form-control form-control-sm" placeholder="Ex: Do Zero à Integração de APIs" oninput="atualizarFormularioDinamico()">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label small fw-semibold mb-1">3. Público-Alvo e Nível</label>
                                        <input type="text" id="fPublico" class="form-control form-control-sm" placeholder="Ex: Iniciantes e Analistas" oninput="atualizarFormularioDinamico()">
                                    </div>
                                    <div class="row g-2 mb-2">
                                        <div class="col-6">
                                            <label class="form-label small fw-semibold mb-1">4. Autor</label>
                                            <input type="text" id="fAutor" class="form-control form-control-sm" placeholder="Ex: Igor Dev" oninput="atualizarFormularioDinamico()">
                                        </div>
                                        <div class="col-6">
                                            <label class="form-label small fw-semibold mb-1">5. Instituição</label>
                                            <input type="text" id="fInst" class="form-control form-control-sm" placeholder="Ex: Interatech" oninput="atualizarFormularioDinamico()">
                                        </div>
                                    </div>
                                    <div class="row g-2 mb-2">
                                        <div class="col-6">
                                            <label class="form-label small fw-semibold mb-1">6. Versão / Ano</label>
                                            <input type="text" id="fVersao" class="form-control form-control-sm" value="1.0 - 2026" oninput="atualizarFormularioDinamico()">
                                        </div>
                                        <div class="col-6">
                                            <label class="form-label small fw-semibold mb-1">7. Capítulos</label>
                                            <input type="text" id="fCaps" class="form-control form-control-sm" placeholder="Ex: 3 capítulos" oninput="atualizarFormularioDinamico()">
                                        </div>
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label small fw-semibold mb-1">8. Tópicos Obrigatórios</label>
                                        <textarea id="fTopicos" class="form-control form-control-sm" rows="2" placeholder="- Tópico 1&#10;- Tópico 2" oninput="atualizarFormularioDinamico()"></textarea>
                                    </div>
                                    <div class="mb-0">
                                        <label class="form-label small fw-semibold mb-1">9. Preferência de Cores</label>
                                        <input type="text" id="fCores" class="form-control form-control-sm" placeholder="Ex: Azul (#0056b3) ou Deixe a IA escolher" oninput="atualizarFormularioDinamico()">
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-7">
                                <textarea id="txtPromptFormulario" class="form-control editor-textarea p-3 h-100" style="min-height: 440px;"></textarea>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/arquivos-exemplo", methods=["GET"])
def listar_exemplos():
    """Lista todos os arquivos .json existentes na pasta data/."""
    arquivos = []
    if os.path.isdir(DIR_DATA):
        for f in os.listdir(DIR_DATA):
            if f.endswith(".json"):
                arquivos.append(f)
    return jsonify(sorted(arquivos))


@app.route("/api/prompts", methods=["GET"])
def obter_prompts():
    """Lê o arquivo PROMPTS_MESTRE_E_FORMULARIO.md e extrai os blocos de prompt."""
    caminho_prompts = os.path.join(DIR_DATA, "PROMPTS_MESTRE_E_FORMULARIO.md")
    if not os.path.isfile(caminho_prompts):
        return jsonify({"prompt_mestre": "", "prompt_formulario": ""}), 404

    with open(caminho_prompts, "r", encoding="utf-8") as f:
        conteudo = f.read()

    blocos = re.findall(r"```text\r?\n(.*?)\r?\n```", conteudo, re.DOTALL)
    prompt_mestre = blocos[0] if len(blocos) > 0 else ""
    prompt_formulario = blocos[1] if len(blocos) > 1 else ""

    return jsonify({
        "prompt_mestre": prompt_mestre,
        "prompt_formulario": prompt_formulario,
    })


@app.route("/api/carregar-arquivo/<nome>", methods=["GET"])
def carregar_arquivo(nome: str):
    """Retorna o conteúdo em texto do arquivo solicitado."""
    # Sanitização básica de caminho
    nome_seguro = os.path.basename(nome)
    caminho = os.path.join(DIR_DATA, nome_seguro)
    if not os.path.isfile(caminho):
        return ("Arquivo não encontrado", 404)
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "application/json; charset=utf-8"}


@app.route("/api/validar", methods=["POST"])
def api_validar():
    """Endpoint de validação inteligente de JSON."""
    payload = request.get_json(silent=True) or {}
    conteudo = payload.get("conteudo", "")
    resultado = validador.validar_json_string(conteudo)
    # Não envia o nó 'dados' para economizar tráfego
    resultado.pop("dados", None)
    return jsonify(resultado)


@app.route("/api/gerar", methods=["POST"])
def api_gerar():
    """Endpoint que valida e renderiza o PDF."""
    payload = request.get_json(silent=True) or {}
    conteudo = payload.get("conteudo", "")

    # Valida antes de processar
    val = validador.validar_json_string(conteudo)
    if not val["valido"]:
        return jsonify({
            "sucesso": False,
            "erro": "O JSON possui erros de validação e não pode ser renderizado.",
            "erros": val["erros"],
        }), 400

    dados = val["dados"]
    titulo_sanitizado = "".join(
        c for c in val["resumo"]["titulo"] if c.isalnum() or c in (" ", "_", "-")
    ).strip().replace(" ", "_")
    if not titulo_sanitizado:
        titulo_sanitizado = "Apostila"

    nome_pdf = f"{titulo_sanitizado}.pdf"
    caminho_pdf = os.path.join(DIR_OUTPUT, nome_pdf)

    # Renderiza e converte
    inicio = time.perf_counter()
    try:
        html = gerar_pdf.renderizar_template(dados)
        navegador = gerar_pdf.localizar_navegador()

        if navegador:
            caminho_html_temp = os.path.join(DIR_OUTPUT, ".temp_web_render.html")
            with open(caminho_html_temp, "w", encoding="utf-8") as f:
                f.write(html)
            try:
                gerar_pdf.converter_via_navegador(caminho_html_temp, caminho_pdf, navegador)
            finally:
                if os.path.isfile(caminho_html_temp):
                    os.remove(caminho_html_temp)
        else:
            if not gerar_pdf.converter_via_pdfkit(html, caminho_pdf):
                if not gerar_pdf.converter_via_weasyprint(html, caminho_pdf, gerar_pdf.DIR_TEMPLATES):
                    raise RuntimeError("Nenhum motor de conversão PDF encontrado.")

        duracao = round(time.perf_counter() - inicio, 2)
        tamanho_kb = round(os.path.getsize(caminho_pdf) / 1024, 1)

        return jsonify({
            "sucesso": True,
            "nome_arquivo": nome_pdf,
            "url_pdf": f"/output/{nome_pdf}",
            "tamanho_kb": tamanho_kb,
            "tempo_s": duracao,
        })
    except Exception as exc:
        logging.error("Erro ao gerar PDF via Web: %s", exc)
        return jsonify({"sucesso": False, "erro": str(exc)}), 500


@app.route("/output/<nome_arquivo>", methods=["GET"])
def baixar_output(nome_arquivo: str):
    """Serve os arquivos PDF gerados."""
    nome_seguro = os.path.basename(nome_arquivo)
    return send_from_directory(DIR_OUTPUT, nome_seguro)


def iniciar_servidor_web(porta: int = 5000, abrir_navegador: bool = True):
    """Inicia o servidor web Flask e abre o navegador automaticamente."""
    url = f"http://127.0.0.1:{porta}"
    print(f"\n🚀 Servidor Web iniciado com sucesso!")
    print(f"👉 Acesse a interface em: {url}\n")
    if abrir_navegador:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=porta, debug=False)


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5000
    iniciar_servidor_web(porta=porta)
