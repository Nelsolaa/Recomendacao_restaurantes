from heapq import heappop, heappush


def _vizinhos(grafo, no):
    if hasattr(grafo, "neighbors"):
        for vizinho in grafo.neighbors(no):
            peso = grafo[no][vizinho].get("weight", 1)
            yield vizinho, peso
        return

    conexoes = grafo.get(no, {})
    if isinstance(conexoes, dict):
        for vizinho, peso in conexoes.items():
            if isinstance(peso, dict):
                peso = peso.get("weight", 1)
            yield vizinho, peso
        return

    for item in conexoes:
        if isinstance(item, tuple) and len(item) == 2:
            yield item
        else:
            yield item, 1


def executar_dijkstra(grafo, no_inicial):
    distancias = {no_inicial: 0}
    fila = [(0, no_inicial)]
    visitados = set()

    while fila:
        distancia_atual, no_atual = heappop(fila)
        if no_atual in visitados:
            continue

        visitados.add(no_atual)

        for vizinho, peso in _vizinhos(grafo, no_atual):
            nova_distancia = distancia_atual + float(peso)
            if nova_distancia < distancias.get(vizinho, float("inf")):
                distancias[vizinho] = nova_distancia
                heappush(fila, (nova_distancia, vizinho))

    return [
        {"no": no, "distancia": distancia}
        for no, distancia in sorted(distancias.items(), key=lambda item: item[1])
        if no != no_inicial
    ]
