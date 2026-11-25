import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

DIR_BASE = os.path.abspath(os.path.dirname(__file__))

TIPOS_BLOCOS_VALIDOS = {
    "paragrafo",
    "subtitulo",
    "lista",
    "destaque",
    "tabela",
    "imagem",
    "link",
}

REGEX_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def validar_json_string(conteudo_str: str) -> Dict[str, Any]:
    """
    Executa uma análise sintática e semântica profunda sobre o conteúdo JSON.
    Retorna erros críticos, alertas de boas práticas e um resumo estatístico.
    """
    erros: List[Dict[str, str]] = []
    avisos: List[Dict[str, str]] = []
    resumo: Dict[str, Any] = {
        "titulo": "",
        "autor": "",
        "instituicao": "",
        "total_capitulos": 0,
        "total_blocos": 0,
        "contagem_blocos": {},
    }

    # 1. Validação de Sintaxe JSON
    try:
        dados = json.loads(conteudo_str)
    except json.JSONDecodeError as exc:
        linhas = conteudo_str.splitlines()
        trecho = ""
        if 0 <= exc.lineno - 1 < len(linhas):
            linha_erro = linhas[exc.lineno - 1]
            apontador = " " * (max(0, exc.colno - 1)) + "^"
            trecho = f"{linha_erro}\n{apontador}"

        erros.append({
            "categoria": "Sintaxe JSON",
            "localizacao": f"Linha {exc.lineno}, Coluna {exc.colno}",
            "mensagem": f"Erro de sintaxe JSON: {exc.msg}",
            "trecho": trecho,
            "sugestao": "Verifique se há aspas internas não escapadas, vírgulas sobrando ou chaves abertas sem fechar.",
        })
        return {
            "valido": False,
            "erros": erros,
            "avisos": avisos,
            "resumo": resumo,
            "dados": None,
        }

    # 2. Validação da Raiz
    if not isinstance(dados, dict):
        erros.append({
            "categoria": "Estrutura Raiz",
            "localizacao": "Raiz do documento",
            "mensagem": f"O documento deve ser um objeto JSON (dicionário), mas foi recebido '{type(dados).__name__}'.",
            "sugestao": "Envolva o conteúdo em um objeto com as chaves 'metadados' e 'capitulos'.",
        })
        return {
            "valido": False,
            "erros": erros,
            "avisos": avisos,
            "resumo": resumo,
            "dados": None,
        }

    # 3. Validação de Metadados
    metadados = dados.get("metadados")
    if metadados is None:
        avisos.append({
            "categoria": "Metadados",
            "localizacao": "raiz.metadados",
            "mensagem": "Chave 'metadados' não encontrada. O PDF usará valores padrão.",
            "sugestao": "Adicione a chave 'metadados' com 'titulo', 'autor', 'cor_primaria', etc.",
        })
        metadados = {}
    elif not isinstance(metadados, dict):
        erros.append({
            "categoria": "Metadados",
            "localizacao": "raiz.metadados",
            "mensagem": f"'metadados' deve ser um objeto, mas foi recebido '{type(metadados).__name__}'.",
            "sugestao": "Substitua por um objeto com os atributos da obra.",
        })
        metadados = {}

    titulo = metadados.get("titulo") or dados.get("title")
    if not titulo:
        avisos.append({
            "categoria": "Metadados",
            "localizacao": "metadados.titulo",
            "mensagem": "Título da apostila ausente ou vazio. Será usado o título padrão 'Apostila'.",
            "sugestao": "Defina 'titulo' em 'metadados' para nomear a capa.",
        })
        resumo["titulo"] = "Sem Título"
    else:
        resumo["titulo"] = str(titulo)

    resumo["autor"] = str(metadados.get("autor", "Não especificado"))
    resumo["instituicao"] = str(metadados.get("instituicao", ""))

    # Cores
    for chave_cor in ["cor_primaria", "cor_secundaria"]:
        valor_cor = metadados.get(chave_cor)
        if valor_cor:
            if not isinstance(valor_cor, str) or not REGEX_HEX.match(valor_cor):
                avisos.append({
                    "categoria": "Identidade Visual",
                    "localizacao": f"metadados.{chave_cor}",
                    "mensagem": f"Cor '{valor_cor}' não parece ser um código HEX válido (ex: #0056b3).",
                    "sugestao": "Use o formato '#RRGGBB' com 6 dígitos hexadecimais.",
                })

    # Logo
    logo_path = metadados.get("logo_path")
    if logo_path and isinstance(logo_path, str):
        caminho_abs = os.path.join(DIR_BASE, logo_path)
        if not os.path.isfile(caminho_abs) and not logo_path.startswith("http"):
            avisos.append({
                "categoria": "Assets",
                "localizacao": "metadados.logo_path",
                "mensagem": f"Arquivo de logo '{logo_path}' não foi encontrado localmente no disco.",
                "sugestao": "Certifique-se de que a imagem existe na pasta 'assets/' ou forneça uma URL válida.",
            })

    # 4. Validação dos Capítulos
    capitulos = dados.get("capitulos") or dados.get("sections")
    if capitulos is None:
        erros.append({
            "categoria": "Estrutura",
            "localizacao": "raiz.capitulos",
            "mensagem": "Chave 'capitulos' ausente no documento.",
            "sugestao": "Adicione a lista 'capitulos' contendo ao menos 1 capítulo com blocos de conteúdo.",
        })
        return {
            "valido": False,
            "erros": erros,
            "avisos": avisos,
            "resumo": resumo,
            "dados": dados,
        }

    if not isinstance(capitulos, list):
        erros.append({
            "categoria": "Estrutura",
            "localizacao": "raiz.capitulos",
            "mensagem": f"'capitulos' deve ser uma lista (array), mas foi recebido '{type(capitulos).__name__}'.",
            "sugestao": "Mude o valor de 'capitulos' para uma lista de objetos [ { ... } ].",
        })
        return {
            "valido": False,
            "erros": erros,
            "avisos": avisos,
            "resumo": resumo,
            "dados": dados,
        }

    resumo["total_capitulos"] = len(capitulos)

    if len(capitulos) == 0:
        avisos.append({
            "categoria": "Conteúdo",
            "localizacao": "capitulos",
            "mensagem": "A lista de capítulos está vazia. O PDF gerado conterá apenas a capa.",
            "sugestao": "Adicione capítulos para preencher o corpo do documento.",
        })

    total_blocos = 0
    contagem_blocos: Dict[str, int] = {}

    for idx_cap, cap in enumerate(capitulos, start=1):
        loc_cap = f"Capítulo {idx_cap}"

        if not isinstance(cap, dict):
            erros.append({
                "categoria": "Capítulos",
                "localizacao": loc_cap,
                "mensagem": f"Cada capítulo deve ser um objeto, mas o item {idx_cap} é '{type(cap).__name__}'.",
                "sugestao": "Estruture o capítulo com 'numero', 'titulo' e 'blocos'.",
            })
            continue

        cap_titulo = cap.get("titulo")
        if not cap_titulo:
            avisos.append({
                "categoria": "Capítulos",
                "localizacao": f"{loc_cap}.titulo",
                "mensagem": f"O {loc_cap} não possui título definido.",
                "sugestao": "Adicione o campo 'titulo' para identificar a seção.",
            })
        else:
            loc_cap = f"Capítulo {idx_cap} ('{cap_titulo}')"

        blocos = cap.get("blocos")
        if blocos is None:
            avisos.append({
                "categoria": "Blocos",
                "localizacao": f"{loc_cap}.blocos",
                "mensagem": f"O {loc_cap} não possui a lista 'blocos'.",
                "sugestao": "Adicione a lista 'blocos' contendo os parágrafos, listas e tabelas.",
            })
            continue

        if not isinstance(blocos, list):
            erros.append({
                "categoria": "Blocos",
                "localizacao": f"{loc_cap}.blocos",
                "mensagem": f"A chave 'blocos' deve ser uma lista, obtido '{type(blocos).__name__}'.",
                "sugestao": "Converta 'blocos' em um array de objetos de conteúdo.",
            })
            continue

        if len(blocos) == 0:
            avisos.append({
                "categoria": "Blocos",
                "localizacao": f"{loc_cap}.blocos",
                "mensagem": f"O {loc_cap} não possui nenhum bloco de conteúdo.",
                "sugestao": "Insira blocos como 'paragrafo', 'lista' ou 'destaque'.",
            })

        for idx_bloco, bloco in enumerate(blocos, start=1):
            total_blocos += 1
            loc_bloco = f"{loc_cap} > Bloco {idx_bloco}"

            if not isinstance(bloco, dict):
                erros.append({
                    "categoria": "Blocos",
                    "localizacao": loc_bloco,
                    "mensagem": f"O bloco deve ser um objeto, obtido '{type(bloco).__name__}'.",
                    "sugestao": "Defina o bloco como um objeto com a chave 'tipo'.",
                })
                continue

            tipo = bloco.get("tipo")
            if not tipo:
                erros.append({
                    "categoria": "Blocos",
                    "localizacao": loc_bloco,
                    "mensagem": "Campo obrigatório 'tipo' não informado no bloco.",
                    "sugestao": f"Defina 'tipo' como um dos valores permitidos: {', '.join(sorted(TIPOS_BLOCOS_VALIDOS))}.",
                })
                continue

            contagem_blocos[tipo] = contagem_blocos.get(tipo, 0) + 1

            if tipo not in TIPOS_BLOCOS_VALIDOS:
                erros.append({
                    "categoria": "Blocos",
                    "localizacao": f"{loc_bloco} (tipo: '{tipo}')",
                    "mensagem": f"Tipo de bloco desconhecido: '{tipo}'.",
                    "sugestao": f"Utilize um dos tipos suportados: {', '.join(sorted(TIPOS_BLOCOS_VALIDOS))}.",
                })
                continue

            # Validações Específicas por Tipo
            if tipo == "paragrafo":
                if not bloco.get("conteudo"):
                    avisos.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [parágrafo]",
                        "mensagem": "Parágrafo com 'conteudo' vazio.",
                        "sugestao": "Preencha o texto do parágrafo.",
                    })

            elif tipo == "subtitulo":
                if not bloco.get("conteudo"):
                    avisos.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [subtítulo]",
                        "mensagem": "Subtítulo com 'conteudo' vazio.",
                        "sugestao": "Insira o texto do subtítulo.",
                    })

            elif tipo == "lista":
                itens = bloco.get("itens")
                if not isinstance(itens, list) or len(itens) == 0:
                    erros.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [lista]",
                        "mensagem": "Bloco de lista deve conter um array 'itens' com ao menos 1 elemento.",
                        "sugestao": "Adicione 'itens': ['item 1', 'item 2'].",
                    })

            elif tipo == "destaque":
                if not bloco.get("conteudo") and not bloco.get("titulo"):
                    avisos.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [destaque]",
                        "mensagem": "Caixa de destaque sem 'titulo' e sem 'conteudo'.",
                        "sugestao": "Preencha o conselho ou dica no bloco de destaque.",
                    })

            elif tipo == "tabela":
                cabecalhos = bloco.get("cabecalhos")
                linhas = bloco.get("linhas")
                if not cabecalhos and not linhas:
                    erros.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [tabela]",
                        "mensagem": "Tabela sem 'cabecalhos' e sem 'linhas'.",
                        "sugestao": "Defina 'cabecalhos': ['Col 1', 'Col 2'] e 'linhas': [['A', 'B']].",
                    })

            elif tipo == "imagem":
                caminho_img = bloco.get("caminho") or bloco.get("url")
                if not caminho_img:
                    erros.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [imagem]",
                        "mensagem": "Bloco de imagem sem o campo 'caminho' ou 'url'.",
                        "sugestao": "Informe o caminho relativo (ex: 'assets/diagrama.png') ou URL da imagem.",
                    })
                elif not caminho_img.startswith("http"):
                    caminho_abs = os.path.join(DIR_BASE, caminho_img)
                    if not os.path.isfile(caminho_abs):
                        avisos.append({
                            "categoria": "Assets",
                            "localizacao": f"{loc_bloco} [imagem]",
                            "mensagem": f"Arquivo de imagem '{caminho_img}' não encontrado localmente.",
                            "sugestao": "Verifique se a imagem foi inserida na pasta correta.",
                        })

            elif tipo == "link":
                if not bloco.get("url"):
                    erros.append({
                        "categoria": "Conteúdo",
                        "localizacao": f"{loc_bloco} [link]",
                        "mensagem": "Bloco de link sem o campo 'url'.",
                        "sugestao": "Informe a URL de destino (ex: 'https://docs.n8n.io').",
                    })

    resumo["total_blocos"] = total_blocos
    resumo["contagem_blocos"] = contagem_blocos

    return {
        "valido": len(erros) == 0,
        "erros": erros,
        "avisos": avisos,
        "resumo": resumo,
        "dados": dados,
    }
