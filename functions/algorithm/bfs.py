from collections import deque


def _vizinhos(grafo, no):
    if hasattr(grafo, "neighbors"):
        return list(grafo.neighbors(no))

    conexoes = grafo.get(no, {})
    if isinstance(conexoes, dict):
        return list(conexoes.keys())

    return [item[0] if isinstance(item, tuple) else item for item in conexoes]


def executar_bfs(grafo, no_inicial):
    visitados = {no_inicial}
    fila = deque([no_inicial])
    ordem = []

    while fila:
        no_atual = fila.popleft()

        for vizinho in _vizinhos(grafo, no_atual):
            if vizinho in visitados:
                continue

            visitados.add(vizinho)
            fila.append(vizinho)
            ordem.append(vizinho)

    return ordem
