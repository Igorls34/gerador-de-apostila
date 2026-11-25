import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app_web
import gerar_pdf
import validador

SAMPLE_DATA = {
    "metadados": {
        "titulo": "Apostila de Teste Automatizado",
        "subtitulo": "Guia de Validação CI/CD",
        "autor": "Igor Dev",
        "instituicao": "Interatech",
        "versao": "1.0",
        "cor_primaria": "#0056b3",
        "cor_secundaria": "#00a8e8",
    },
    "capitulos": [
        {
            "numero": "01",
            "titulo": "Introdução",
            "blocos": [
                {"tipo": "paragrafo", "conteudo": "Texto de teste."},
                {"tipo": "subtitulo", "conteudo": "Conceitos"},
                {"tipo": "lista", "estilo": "bullet", "itens": ["Item 1", "Item 2"]},
                {"tipo": "destaque", "titulo": "Nota", "conteudo": "Dica importante."},
                {"tipo": "tabela", "cabecalhos": ["A", "B"], "linhas": [["1", "2"]]},
                {"tipo": "link", "texto": "Docs", "url": "https://example.com"},
            ],
        }
    ],
}


def test_health_endpoint():
    client = app_web.app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_index_page():
    client = app_web.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Gerador de Apostilas em PDF" in resp.data


def test_prompts_endpoint():
    client = app_web.app.test_client()
    resp = client.get("/api/prompts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["prompt_mestre"]) > 100
    assert len(data["prompt_formulario"]) > 100


def test_validador_valido():
    res = validador.validar_json_string(json.dumps(SAMPLE_DATA))
    assert res["valido"] is True
    assert len(res["erros"]) == 0


def test_validador_erro_sintaxe():
    res = validador.validar_json_string('{"metadados": {')
    assert res["valido"] is False
    assert len(res["erros"]) == 1
    assert res["erros"][0]["categoria"] == "Sintaxe JSON"


def test_validador_bloco_invalido():
    payload = json.dumps({
        "metadados": {"titulo": "Teste"},
        "capitulos": [{"numero": "01", "titulo": "Cap 1", "blocos": [{"tipo": "desconhecido"}]}]
    })
    res = validador.validar_json_string(payload)
    assert res["valido"] is False
    assert any("desconhecido" in e["mensagem"] for e in res["erros"])


def test_renderizar_template():
    html = gerar_pdf.renderizar_template(SAMPLE_DATA)
    assert "Apostila de Teste Automatizado" in html
    assert '<div class="capa">' in html
