# Recomendacao de Restaurantes

Aplicacao web simples em Python para recomendar restaurantes usando grafos. O sistema recebe filtros de busca, monta um grafo ligando o usuario aos restaurantes encontrados e usa os algoritmos de Dijkstra e BFS para organizar os resultados.

## Funcionalidades

- Busca por tipo de restaurante.
- Filtro por raio de distancia.
- Filtro por nota minima.
- Uso de localizacao pelo navegador ou endereco informado no formulario.
- Busca real pela Google Places API, quando uma chave de API esta configurada.
- Modo de demonstracao com dados de exemplo, quando nao ha chave de API.
- Geracao de imagem do grafo com NetworkX e Matplotlib.
- Cards com restaurantes recomendados, distancia, nota e ordem de visita BFS.

## Tecnologias

- Python
- HTTP server nativo do Python
- NetworkX
- Matplotlib
- Google Places API e Geocoding API, opcionalmente
- HTML e CSS

## Estrutura do projeto

```text
.
├── main.py
├── functions/
│   ├── main.py
│   └── algorithm/
│       ├── bfs.py
│       └── dijskra.py
├── template/
│   ├── index.html
│   └── style.css
├── requirements.txt
├── PLANEJAMENTO.md
└── README.md
```

## Como executar

1. Crie e ative um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Instale as dependencias:

```bash
pip install -r requirements.txt
```

3. Inicie o servidor:

```bash
python3 main.py
```

4. Acesse no navegador:

```text
http://127.0.0.1:8000
```

Para encerrar o servidor, use `Ctrl+C` no terminal.

## Deploy na Vercel

O projeto tambem possui uma entrada serverless para deploy na Vercel:

- `api/index.py`: handler Python usado pela Vercel.
- `vercel.json`: redireciona as rotas da aplicacao para o handler.
- `.vercelignore`: evita enviar arquivos locais desnecessarios no deploy.

Passos para publicar:

1. Suba este projeto para um repositorio no GitHub.
2. Acesse a Vercel e clique em `Add New Project`.
3. Importe o repositorio do GitHub.
4. Mantenha as configuracoes padrao do projeto.
5. Em `Environment Variables`, adicione a chave `API_KEY` ou `GOOGLE_MAPS_API_KEY`, se quiser usar dados reais do Google.
6. Clique em `Deploy`.

Sem variavel de ambiente da API, a aplicacao ainda funciona na Vercel usando os dados de exemplo.

## Configuracao da API do Google

A aplicacao funciona sem chave de API usando dados de exemplo. Para buscar restaurantes reais, crie um arquivo `.env` na raiz do projeto com uma das variaveis abaixo:

```env
API_KEY=sua_chave_google
```

ou:

```env
GOOGLE_MAPS_API_KEY=sua_chave_google
```

A chave precisa ter acesso as APIs:

- Places API
- Geocoding API

## Como funciona

O arquivo `main.py` inicia o servidor web definido em `functions/main.py`.

O fluxo principal da aplicacao e:

1. Ler os filtros enviados pelo formulario.
2. Resolver a localizacao do usuario.
3. Buscar restaurantes pela Google Places API ou pelos dados de exemplo.
4. Criar um grafo com o usuario e os restaurantes.
5. Executar Dijkstra para ordenar restaurantes pela menor distancia.
6. Executar BFS para registrar a ordem de visita dos restaurantes no grafo.
7. Renderizar a pagina HTML com o grafo e os cards dos restaurantes.

## Algoritmos

### Dijkstra

Implementado em `functions/algorithm/dijskra.py`.

Calcula as menores distancias entre o no inicial `usuario` e os restaurantes conectados ao grafo. O resultado e usado para ordenar as recomendacoes por proximidade.

### BFS

Implementado em `functions/algorithm/bfs.py`.

Percorre os nos conectados ao usuario e retorna a ordem de visita. Essa ordem aparece nos cards dos restaurantes.

## Rotas

- `/` ou `/index.html`: pagina principal da aplicacao.
- `/style.css`: arquivo de estilos.
- `/graph.png`: imagem PNG do grafo gerado para a busca atual.

## Observacoes

- Se a chave de API nao estiver configurada, o sistema mostra uma mensagem informando que esta usando dados de exemplo.
- O raio aceita valores como `3`, `2km` ou `500m`.
- Quando apenas um numero ate `50` e informado no raio, ele e interpretado como quilometros.
- A localizacao padrao, quando nenhum endereco ou coordenada e resolvido, e Fortaleza/CE.
