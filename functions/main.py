import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from functions.algorithm.bfs import executar_bfs
from functions.algorithm.dijskra import executar_dijkstra


PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "template" / "index.html"
STYLE_PATH = ROOT / "template" / "style.css"
USUARIO = "usuario"
DEFAULT_LOCATION = {
    "latitude": -3.7319,
    "longitude": -38.5267,
    "label": "Fortaleza/CE",
}

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

if os.getenv("VERCEL"):
    os.environ["MPLCONFIGDIR"] = "/tmp/.matplotlib"
    os.environ["XDG_CACHE_HOME"] = "/tmp/.cache"

RESTAURANTES_EXEMPLO = [
    {
        "id": "sabor_ceara",
        "nome": "Sabor Ceara",
        "tipo": "regional",
        "distancia": 620,
        "nota": 4.6,
        "endereco": "Av. Beira Mar, 455",
    },
    {
        "id": "cantina_luz",
        "nome": "Cantina da Luz",
        "tipo": "italiano",
        "distancia": 850,
        "nota": 4.8,
        "endereco": "Rua das Flores, 120",
    },
    {
        "id": "casa_arabe",
        "nome": "Casa Arabe",
        "tipo": "arabe",
        "distancia": 1250,
        "nota": 4.5,
        "endereco": "Rua Libano, 42",
    },
    {
        "id": "tempero_zen",
        "nome": "Tempero Zen",
        "tipo": "vegetariano",
        "distancia": 1400,
        "nota": 4.7,
        "endereco": "Rua Verde, 88",
    },
    {
        "id": "tokyo_praia",
        "nome": "Tokyo Praia",
        "tipo": "japones",
        "distancia": 1750,
        "nota": 4.9,
        "endereco": "Rua do Sol, 310",
    },
]


def load_env(path=".env"):
    env_path = ROOT / path
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_key():
    load_env()
    return os.getenv("API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")


def post_json(url, payload, headers=None, timeout=20):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Erro de conexao: {error.reason}") from error


def get_json(url, params, timeout=20):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Erro de conexao: {error.reason}") from error


def normalizar_raio(valor):
    texto = (valor or "3").strip().lower().replace(",", ".")
    if texto.endswith("km"):
        return float(texto[:-2].strip()) * 1000
    if texto.endswith("m"):
        return float(texto[:-1].strip())

    numero = float(texto)
    return numero * 1000 if numero <= 50 else numero


def distancia_metros(origem, destino):
    raio_terra = 6371000
    lat1 = math.radians(origem["latitude"])
    lat2 = math.radians(destino["latitude"])
    delta_lat = math.radians(destino["latitude"] - origem["latitude"])
    delta_lng = math.radians(destino["longitude"] - origem["longitude"])

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    return raio_terra * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def resolver_localizacao(localizacao, chave_api):
    latitude = _float_ou_none(localizacao.get("latitude"))
    longitude = _float_ou_none(localizacao.get("longitude"))
    if latitude is not None and longitude is not None:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "label": "localizacao do navegador",
        }

    endereco = montar_endereco(localizacao)
    if endereco and chave_api:
        dados = get_json(GEOCODING_URL, {"address": endereco, "key": chave_api})
        resultados = dados.get("results", [])
        if resultados:
            ponto = resultados[0]["geometry"]["location"]
            return {
                "latitude": ponto["lat"],
                "longitude": ponto["lng"],
                "label": resultados[0].get("formatted_address", endereco),
            }

    return DEFAULT_LOCATION


def montar_endereco(localizacao):
    partes_usuario = [
        localizacao.get("endereco", ""),
        localizacao.get("numero", ""),
        localizacao.get("cidade", ""),
        localizacao.get("estado", ""),
    ]
    if not any(partes_usuario):
        return ""

    partes = [*partes_usuario, "Brasil"]
    return ", ".join(parte for parte in partes if parte)


def buscar_restaurantes_google(chave_api, localizacao, tipo, raio_metros, nota_minima):
    query = f"restaurante {tipo}".strip()
    payload = {
        "textQuery": query,
        "includedType": "restaurant",
        "strictTypeFiltering": True,
        "maxResultCount": 20,
        "rankPreference": "DISTANCE",
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": localizacao["latitude"],
                    "longitude": localizacao["longitude"],
                },
                "radius": raio_metros,
            }
        },
    }
    headers = {
        "X-Goog-Api-Key": chave_api,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.rating,"
            "places.userRatingCount,"
            "places.primaryTypeDisplayName"
        ),
    }
    resposta = post_json(PLACES_URL, payload, headers=headers)
    restaurantes = []

    for place in resposta.get("places", []):
        place_location = place.get("location")
        if not place_location:
            continue

        destino = {
            "latitude": place_location["latitude"],
            "longitude": place_location["longitude"],
        }
        distancia = distancia_metros(localizacao, destino)
        nota = float(place.get("rating") or 0)
        if distancia > raio_metros or nota < nota_minima:
            continue

        tipo_texto = place.get("primaryTypeDisplayName", {}).get("text", "Restaurante")
        restaurantes.append(
            {
                "id": place.get("id") or _id_seguro(place.get("displayName", {}).get("text", "restaurante")),
                "nome": place.get("displayName", {}).get("text", "Restaurante sem nome"),
                "tipo": tipo_texto,
                "distancia": distancia,
                "nota": nota,
                "endereco": place.get("formattedAddress", "Endereco nao informado"),
            }
        )

    return sorted(restaurantes, key=lambda restaurante: restaurante["distancia"])


def buscar_restaurantes_exemplo(tipo, raio_metros, nota_minima):
    tipo = tipo.strip().lower()
    restaurantes = []
    for restaurante in RESTAURANTES_EXEMPLO:
        tipo_ok = not tipo or tipo in restaurante["tipo"].lower() or tipo in restaurante["nome"].lower()
        if tipo_ok and restaurante["distancia"] <= raio_metros and restaurante["nota"] >= nota_minima:
            restaurantes.append(restaurante)
    return restaurantes


def criar_grafo(restaurantes):
    import networkx as nx

    grafo = nx.Graph()
    grafo.add_node(USUARIO)
    for restaurante in restaurantes:
        grafo.add_node(restaurante["id"])
        grafo.add_edge(USUARIO, restaurante["id"], weight=round(restaurante["distancia"]))
    return grafo


def recomendar_restaurantes(tipo="", raio="3", nota_minima="0", localizacao=None):
    try:
        raio_metros = normalizar_raio(raio)
    except ValueError:
        raio_metros = 3000

    try:
        nota = float(str(nota_minima or "0").replace(",", "."))
    except ValueError:
        nota = 0

    chave_api = api_key()
    mensagens = []
    origem = "Google Places API"

    try:
        localizacao_resolvida = resolver_localizacao(localizacao or {}, chave_api)
    except Exception as error:
        localizacao_resolvida = DEFAULT_LOCATION
        mensagens.append(f"Nao foi possivel resolver o endereco: {error}")

    if chave_api:
        try:
            restaurantes = buscar_restaurantes_google(
                chave_api,
                localizacao_resolvida,
                tipo,
                raio_metros,
                nota,
            )
        except Exception as error:
            restaurantes = buscar_restaurantes_exemplo(tipo, raio_metros, nota)
            origem = "dados de exemplo"
            mensagens.append(f"Falha ao buscar na Google Places API: {error}")
    else:
        restaurantes = buscar_restaurantes_exemplo(tipo, raio_metros, nota)
        origem = "dados de exemplo"
        mensagens.append("API_KEY nao encontrada no .env. Usando dados de exemplo.")

    grafo = criar_grafo(restaurantes) if restaurantes else None
    dijkstra = executar_dijkstra(grafo, USUARIO) if grafo else []
    ordem_bfs = executar_bfs(grafo, USUARIO) if grafo else []
    restaurantes_por_id = {restaurante["id"]: restaurante for restaurante in restaurantes}
    ordem_por_id = {restaurante_id: indice for indice, restaurante_id in enumerate(ordem_bfs, start=1)}

    recomendacoes = []
    for item in dijkstra:
        restaurante = restaurantes_por_id[item["no"]]
        recomendacoes.append(
            {
                **restaurante,
                "distancia_calculada": item["distancia"],
                "ordem_bfs": ordem_por_id.get(restaurante["id"]),
            }
        )

    return {
        "tipo": tipo,
        "raio": raio,
        "nota_minima": nota_minima,
        "raio_metros": raio_metros,
        "localizacao": localizacao_resolvida,
        "restaurantes": recomendacoes,
        "ordem_bfs": ordem_bfs,
        "mensagens": mensagens,
        "origem": origem,
    }


def gerar_imagem_grafo(restaurantes):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    grafo = criar_grafo(restaurantes)
    nomes = {USUARIO: "usuario"}
    nomes.update({restaurante["id"]: restaurante["nome"] for restaurante in restaurantes})

    figura = plt.figure(figsize=(9, 5))
    posicoes = nx.spring_layout(grafo)
    nx.draw(grafo, posicoes, labels=nomes, with_labels=True)
    pesos = nx.get_edge_attributes(grafo, "weight")
    nx.draw_networkx_edge_labels(grafo, posicoes, edge_labels=pesos)
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png")
    plt.close(figura)
    buffer.seek(0)
    return buffer.getvalue()


def _formatar_distancia(distancia):
    if distancia >= 1000:
        return f"{distancia / 1000:.1f} km"
    return f"{distancia:.0f} m"


def _renderizar_cards(restaurantes):
    if not restaurantes:
        return '<p class="empty">Nenhum restaurante encontrado. Ajuste tipo, raio, nota ou localizacao.</p>'

    cards = []
    for restaurante in restaurantes:
        cards.append(
            '<article class="restaurant-card">'
            f"<h3>{escape(restaurante['nome'])}</h3>"
            f"<p>{escape(restaurante['endereco'])}</p>"
            '<dl>'
            f"<div><dt>Tipo</dt><dd>{escape(restaurante['tipo'])}</dd></div>"
            f"<div><dt>Distancia</dt><dd>{escape(_formatar_distancia(restaurante['distancia_calculada']))}</dd></div>"
            f"<div><dt>Nota</dt><dd>{restaurante['nota']:.1f}</dd></div>"
            f"<div><dt>BFS</dt><dd>{restaurante['ordem_bfs'] or '-'}</dd></div>"
            "</dl>"
            "</article>"
        )
    return "".join(cards)


def renderizar_pagina(parametros=None):
    parametros = parametros or {}
    formulario = _ler_formulario(parametros)
    resultado = recomendar_restaurantes(
        formulario["tipo"],
        formulario["raio"],
        formulario["nota_minima"],
        formulario["localizacao"],
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    valores = {
        "{{tipo}}": escape(formulario["tipo"]),
        "{{raio}}": escape(str(formulario["raio"])),
        "{{nota_minima}}": escape(str(formulario["nota_minima"])),
        "{{cidade}}": escape(formulario["cidade"]),
        "{{estado}}": escape(formulario["estado"]),
        "{{endereco}}": escape(formulario["endereco"]),
        "{{numero}}": escape(formulario["numero"]),
        "{{latitude}}": escape(formulario["latitude"]),
        "{{longitude}}": escape(formulario["longitude"]),
        "{{total_label}}": _total_label(len(resultado["restaurantes"])),
        "{{graph_src}}": escape(_graph_src(formulario)),
        "{{cards}}": _renderizar_cards(resultado["restaurantes"]),
        "{{mensagens}}": _renderizar_mensagens(resultado),
    }

    for marcador, valor in valores.items():
        template = template.replace(marcador, valor)
    return template


def _renderizar_mensagens(resultado):
    mensagens = [
        f"Fonte: {resultado['origem']}. Local usado: {resultado['localizacao']['label']}."
    ]
    mensagens.extend(resultado["mensagens"])
    itens = "".join(f"<li>{escape(mensagem)}</li>" for mensagem in mensagens)
    return f'<ul class="messages">{itens}</ul>'


def _ler_formulario(parametros):
    def valor(campo, padrao=""):
        return parametros.get(campo, [padrao])[0].strip()

    return {
        "tipo": valor("tipo"),
        "raio": valor("raio", "3"),
        "nota_minima": valor("nota_minima", "0"),
        "cidade": valor("cidade"),
        "estado": valor("estado"),
        "endereco": valor("endereco"),
        "numero": valor("numero"),
        "latitude": valor("latitude"),
        "longitude": valor("longitude"),
        "localizacao": {
            "cidade": valor("cidade"),
            "estado": valor("estado"),
            "endereco": valor("endereco"),
            "numero": valor("numero"),
            "latitude": valor("latitude"),
            "longitude": valor("longitude"),
        },
    }


def _graph_src(formulario):
    campos = {
        chave: formulario[chave]
        for chave in (
            "tipo",
            "raio",
            "nota_minima",
            "cidade",
            "estado",
            "endereco",
            "numero",
            "latitude",
            "longitude",
        )
        if formulario[chave]
    }
    query = urlencode(campos)
    return f"/graph.png?{query}" if query else "/graph.png"


def _total_label(total):
    if total == 1:
        return "1 restaurante"
    return f"{total} restaurantes"


def _id_seguro(texto):
    base = "".join(caractere if caractere.isalnum() else "_" for caractere in texto.lower())
    return base.strip("_") or "restaurante"


def _float_ou_none(valor):
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


class RecomendacaoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._processar_requisicao(enviar_corpo=True)

    def do_HEAD(self):
        self._processar_requisicao(enviar_corpo=False)

    def _processar_requisicao(self, enviar_corpo):
        url = urlparse(self.path)
        url = _normalizar_url_vercel(url)

        if url.path == "/style.css":
            self._responder_texto(STYLE_PATH.read_text(encoding="utf-8"), "text/css", enviar_corpo)
            return

        if url.path == "/graph.png":
            self._responder_grafo(parse_qs(url.query), enviar_corpo)
            return

        if url.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if url.path not in {"/", "/index.html"}:
            self.send_error(404)
            return

        self._responder_texto(renderizar_pagina(parse_qs(url.query)), "text/html", enviar_corpo)

    def _responder_grafo(self, parametros, enviar_corpo):
        formulario = _ler_formulario(parametros)
        resultado = recomendar_restaurantes(
            formulario["tipo"],
            formulario["raio"],
            formulario["nota_minima"],
            formulario["localizacao"],
        )
        if not resultado["restaurantes"]:
            self.send_error(404, "Nenhum restaurante para desenhar no grafo")
            return

        try:
            imagem = gerar_imagem_grafo(resultado["restaurantes"])
        except ImportError as error:
            self.send_error(500, f"Instale as dependencias: pip install -r requirements.txt ({error})")
            return

        self._responder_bytes(imagem, "image/png", enviar_corpo)

    def _responder_texto(self, conteudo, content_type, enviar_corpo=True):
        self._responder_bytes(conteudo.encode("utf-8"), f"{content_type}; charset=utf-8", enviar_corpo)

    def _responder_bytes(self, dados, content_type, enviar_corpo=True):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        if enviar_corpo:
            self.wfile.write(dados)

    def log_message(self, formato, *args):
        print(f"[web] {formato % args}")


def iniciar_servidor(host="127.0.0.1", porta=8000):
    servidor = ThreadingHTTPServer((host, porta), RecomendacaoHandler)
    print(f"Servidor iniciado em http://{host}:{porta}")
    print("Use Ctrl+C para encerrar.")
    servidor.serve_forever()


def _normalizar_url_vercel(url):
    if url.path != "/api":
        return url

    parametros = parse_qs(url.query, keep_blank_values=True)
    caminho = parametros.pop("path", [""])[0].strip()
    caminho = f"/{caminho}" if caminho else "/"
    query = urlencode(parametros, doseq=True)
    return url._replace(path=caminho, query=query)


def main():
    iniciar_servidor()


if __name__ == "__main__":
    main()
