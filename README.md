# Recomendacao de Restaurantes

Aplicacao web em Python que recomenda restaurantes a partir de filtros do usuario e representa a busca como um grafo. A ideia principal do projeto e tratar o usuario como o no inicial do grafo e cada restaurante encontrado como um no conectado a ele. A distancia ate cada restaurante vira o peso da aresta.

Com isso, o sistema consegue mostrar os restaurantes mais proximos usando Dijkstra e tambem registrar uma ordem de visita usando BFS.

## O que o projeto faz

- Recebe filtros de busca pelo formulario: tipo de restaurante, raio, nota minima e localizacao.
- Usa a localizacao do navegador, se o usuario permitir.
- Tambem aceita endereco, numero, cidade e estado.
- Busca restaurantes reais pela Google Places API, quando uma chave esta configurada.
- Usa uma lista local de restaurantes de exemplo quando nao existe chave de API ou quando a API falha.
- Monta um grafo com NetworkX.
- Executa Dijkstra para ordenar os restaurantes pela menor distancia.
- Executa BFS para mostrar a ordem de visita dos nos do grafo.
- Renderiza uma pagina HTML com cards dos restaurantes e uma imagem PNG do grafo.

## Ideia central

O projeto nao recomenda restaurantes por aprendizado de maquina. Ele usa uma logica baseada em grafos.

O grafo tem este formato:

```text
usuario
+-- restaurante_1  peso = distancia em metros
+-- restaurante_2  peso = distancia em metros
+-- restaurante_3  peso = distancia em metros
```

Cada restaurante e ligado diretamente ao no `usuario`. A aresta entre eles recebe um peso, que e a distancia calculada ou recebida para aquele restaurante.

Exemplo:

```text
usuario --620m--> Sabor Ceara
usuario --850m--> Cantina da Luz
usuario --1750m--> Tokyo Praia
```

Depois que esse grafo e criado, os algoritmos entram para organizar e explicar os resultados:

- Dijkstra calcula a menor distancia do usuario ate cada restaurante.
- BFS percorre os restaurantes conectados ao usuario e gera uma ordem de visita.

Como o grafo atual liga todos os restaurantes diretamente ao usuario, Dijkstra funciona principalmente como uma ordenacao por menor distancia. Mesmo assim, a estrutura deixa claro como o projeto poderia crescer para um grafo mais complexo, com ruas, bairros, conexoes intermediarias ou outros pontos de interesse.

## Fluxo da aplicacao

O fluxo principal fica em `functions/main.py`, na funcao `recomendar_restaurantes`.

1. O usuario abre a pagina inicial.
2. O formulario envia os filtros pela URL usando `GET`.
3. A aplicacao le os campos do formulario.
4. O raio e normalizado para metros.
5. A nota minima e convertida para numero.
6. A localizacao e resolvida.
7. Os restaurantes sao buscados no Google ou nos dados de exemplo.
8. Os restaurantes sao filtrados por tipo, raio e nota.
9. Um grafo e criado com o usuario e os restaurantes encontrados.
10. Dijkstra calcula as distancias finais.
11. BFS calcula a ordem de visita.
12. A pagina HTML e preenchida com cards, mensagens e o caminho da imagem do grafo.

## Entrada dos dados

Os dados entram pelo formulario em `template/index.html`.

Campos principais:

- `tipo`: texto usado para buscar ou filtrar o tipo de restaurante.
- `raio`: distancia maxima aceita.
- `nota_minima`: menor nota permitida.
- `cidade`, `estado`, `endereco`, `numero`: dados usados para montar um endereco.
- `latitude`, `longitude`: preenchidos automaticamente quando o usuario clica em `Usar localizacao`.

O botao `Usar localizacao` usa a API de geolocalizacao do navegador. Se funcionar, latitude e longitude sao enviadas no formulario. Se nao funcionar, o usuario ainda pode preencher o endereco manualmente.

## Tratamento do raio

A funcao `normalizar_raio` transforma o valor digitado em metros.

Exemplos:

```text
3      -> 3000 metros
2km    -> 2000 metros
500m   -> 500 metros
1000   -> 1000 metros
```

Quando o usuario informa apenas um numero ate `50`, o sistema entende que o valor esta em quilometros. Numeros maiores que `50` sao tratados como metros.

## Resolucao da localizacao

A funcao `resolver_localizacao` decide qual ponto geografico sera usado como origem.

A prioridade e:

1. Usar `latitude` e `longitude`, se vierem do navegador.
2. Montar um endereco com rua, numero, cidade e estado e consultar a Geocoding API.
3. Usar a localizacao padrao de Fortaleza/CE.

A localizacao padrao fica em `DEFAULT_LOCATION`:

```python
{
    "latitude": -3.7319,
    "longitude": -38.5267,
    "label": "Fortaleza/CE",
}
```

## Busca dos restaurantes

Existem dois caminhos possiveis.

### Com API do Google

Se existir `API_KEY` ou `GOOGLE_MAPS_API_KEY`, o projeto usa a Google Places API.

A funcao `buscar_restaurantes_google`:

1. Monta uma busca textual com `restaurante` mais o tipo informado.
2. Limita a busca ao raio configurado.
3. Pede os campos necessarios: nome, endereco, localizacao, nota, tipo e id.
4. Calcula a distancia entre a origem e cada restaurante.
5. Descarta restaurantes fora do raio.
6. Descarta restaurantes abaixo da nota minima.
7. Ordena os restaurantes pela distancia.

A distancia e calculada pela funcao `distancia_metros`, usando a formula de Haversine. Essa formula estima a distancia entre duas coordenadas na superficie da Terra.

### Sem API do Google

Se nao houver chave de API, o projeto usa `RESTAURANTES_EXEMPLO`, uma lista fixa dentro de `functions/main.py`.

A funcao `buscar_restaurantes_exemplo` aplica os mesmos filtros principais:

- tipo;
- raio;
- nota minima.

Esse modo permite testar a aplicacao sem depender de internet, conta do Google ou chave de API.

## Criacao do grafo

A funcao `criar_grafo` usa NetworkX para montar o grafo.

Ela faz tres coisas:

1. Cria um grafo vazio.
2. Adiciona o no `usuario`.
3. Para cada restaurante, adiciona um no e uma aresta ligando `usuario` ao restaurante.

O peso da aresta e a distancia arredondada:

```python
grafo.add_edge(USUARIO, restaurante["id"], weight=round(restaurante["distancia"]))
```

Isso faz a distancia ser parte da estrutura do grafo, nao apenas um campo visual nos cards.

## Dijkstra

O algoritmo esta em `functions/algorithm/dijskra.py`.

Ele recebe:

- o grafo;
- o no inicial, que neste projeto e `usuario`.

Ele retorna uma lista com os nos alcancaveis e suas menores distancias a partir do usuario.

No projeto, o resultado de Dijkstra vira a lista final de recomendacoes:

```python
for item in dijkstra:
    restaurante = restaurantes_por_id[item["no"]]
```

Como os itens retornam ordenados pela distancia, os cards aparecem do restaurante mais proximo para o mais distante.

## BFS

O algoritmo esta em `functions/algorithm/bfs.py`.

BFS significa busca em largura. Ele visita primeiro os vizinhos diretos do no inicial. Como todos os restaurantes sao vizinhos diretos de `usuario`, a BFS gera uma ordem simples de visita dos restaurantes encontrados.

Essa ordem aparece no campo `BFS` de cada card.

No codigo, a ordem e transformada em um mapa:

```python
ordem_por_id = {
    restaurante_id: indice
    for indice, restaurante_id in enumerate(ordem_bfs, start=1)
}
```

Assim cada restaurante recebe seu numero na ordem de visita.

## Imagem do grafo

A rota `/graph.png` gera uma imagem PNG do grafo atual.

Ela chama:

1. `recomendar_restaurantes`, para obter os restaurantes filtrados.
2. `gerar_imagem_grafo`, para criar o desenho com NetworkX e Matplotlib.

Na imagem:

- os nos representam o usuario e os restaurantes;
- as arestas representam as conexoes;
- os pesos nas arestas representam as distancias.

## Rotas

- `/`: pagina principal.
- `/index.html`: tambem renderiza a pagina principal.
- `/style.css`: entrega o CSS.
- `/graph.png`: gera a imagem do grafo para a busca atual.

## Estrutura do projeto

```text
.
+-- main.py
+-- api/
|   +-- index.py
+-- functions/
|   +-- main.py
|   +-- algorithm/
|       +-- bfs.py
|       +-- dijskra.py
+-- template/
|   +-- index.html
|   +-- style.css
+-- requirements.txt
+-- vercel.json
+-- README.md
```

Principais arquivos:

- `main.py`: ponto de entrada local. Chama `iniciar_servidor`.
- `functions/main.py`: concentra servidor, formulario, busca, grafo, renderizacao e rotas.
- `functions/algorithm/dijskra.py`: implementacao do Dijkstra.
- `functions/algorithm/bfs.py`: implementacao da BFS.
- `template/index.html`: interface HTML.
- `template/style.css`: estilos da pagina.
- `api/index.py`: entrada usada no deploy da Vercel.
- `vercel.json`: redireciona as rotas para o handler serverless.

## Como executar localmente

Crie e ative um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Inicie o servidor:

```bash
python3 main.py
```

Acesse:

```text
http://127.0.0.1:8000
```

Para encerrar, use `Ctrl+C`.

## Configuracao da API do Google

A aplicacao funciona sem chave usando dados de exemplo. Para usar restaurantes reais, crie um arquivo `.env` na raiz do projeto:

```env
API_KEY=sua_chave_google
```

Tambem funciona com:

```env
GOOGLE_MAPS_API_KEY=sua_chave_google
```

A chave precisa ter acesso a:

- Places API;
- Geocoding API.

## Deploy na Vercel

O projeto tem suporte a Vercel por meio do arquivo `api/index.py`.

No deploy, `vercel.json` reescreve as rotas para:

```text
/api?path=:path*
```

Dentro de `functions/main.py`, a funcao `_normalizar_url_vercel` transforma essa URL novamente em rotas normais, como `/`, `/style.css` e `/graph.png`.

Para publicar:

1. Envie o projeto para um repositorio no GitHub.
2. Importe o repositorio na Vercel.
3. Configure `API_KEY` ou `GOOGLE_MAPS_API_KEY` nas variaveis de ambiente, se quiser usar dados reais.
4. Faca o deploy.

Sem chave de API, a aplicacao ainda abre usando dados de exemplo.

## Resumo da logica

Em resumo, o projeto funciona assim:

```text
Formulario
   |
   v
Filtros e localizacao
   |
   v
Google Places API ou dados de exemplo
   |
   v
Lista de restaurantes filtrados
   |
   v
Grafo: usuario conectado aos restaurantes
   |
   v
Dijkstra: ordena por menor distancia
   |
   v
BFS: registra ordem de visita
   |
   v
HTML com cards + PNG do grafo
```

Essa separacao facilita entender o projeto: a interface coleta dados, `functions/main.py` coordena o fluxo, os arquivos em `functions/algorithm` executam os algoritmos, e o resultado final aparece na pagina.
