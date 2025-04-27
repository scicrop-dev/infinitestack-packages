import argparse
import http.server
import json
import sys
import osmnx as ox
from shapely.ops import nearest_points
import geopandas as gpd
import networkx as nx
import shapely
from shapely.geometry import Point, shape, LineString, MultiLineString
from geopy.distance import distance
import math
from pathlib import Path

def get_cli_args() -> argparse.Namespace:
    """
    Lê a linha de comando e retorna um Namespace com:
      • project_id  (obrigatório – string ou int)
      • ref         (opcional  – string, default: None)
    """
    parser = argparse.ArgumentParser(
        description="Exemplo de leitura de argumentos CLI."
    )

    # --project_id (obrigatório)
    parser.add_argument(
        "--project_id",
        required=True,
        help="Identificador do projeto "
    )

    # --ref (opcional)
    parser.add_argument(
        "--ref",
        required=False,
        default=None,
        help="uuid"
    )

    parser.add_argument(
        "--workflowId",
        required=True,
        help="Identificador do workflow "
    )

    return parser.parse_args()



def main(workflow_id: str, project_id: str):
    filePath = Path(f'/tmp/is/{workflow_id}.json')
    if not filePath.exists():
        raise FileNotFoundError(f'File {filePath} not found')
        exit(1)

    with open(filePath, 'r') as f:
        data = json.load(f)
        a_map = data['map']
        points = data['points']
        process(a_map, points, project_id)


def process(map, points, project_id):

    G = geojson_dict_to_G(map)
    print(f"Grafo carregado com {G.number_of_nodes()} nós e {G.number_of_edges()} arestas.")

    for points_element in points:

        pA = Point(points_element["from"]["point"][0], points_element["from"]["point"][1])  # A
        pB = Point(points_element["to"]["point"][0], points_element["to"]["point"][1])

        # 3) Inserir ambos no grafo
        G, A_node = add_node_in_edge(G, pA)
        G, B_node = add_node_in_edge(G, pB)

        if A_node is None or B_node is None:
            print("Não foi possível criar nós de origem ou destino. Encerrando.")
            return

        print(f"Nó A: {A_node}, Nó B: {B_node}")
        print(f"Agora temos {G.number_of_nodes()} nós e {G.number_of_edges()} arestas no grafo.")

        # 4) Executar Dijkstra (shortest_path)
        try:
            rota = nx.shortest_path(G, A_node, B_node, weight='length')
            distancia = nx.shortest_path_length(G, A_node, B_node, weight='length')
            print(f"Rota encontrada! Distância: {distancia:.2f} (mesma unidade do CRS, ex: graus ou metros).")
        except nx.NetworkXNoPath:
            print("Não foi possível encontrar uma rota entre A e B.")
            return

        distancia_m = nx.shortest_path_length(G, A_node, B_node, weight='length')
        print(f"Distância de A até B = {distancia_m:.2f} metros")

        #if data["output"]["output_type"] == "gpx":
        filename = "/opt/infinitestack/etc/data/projects/"+project_id+"/output/"+points_element["from"]["name"]+"_"+points_element["to"]["name"]+".gpx"
        filename = filename.replace(' ','-').lower()
        gen_gpx_file(rota, filename)

def gen_gpx_file(rota, filename):
    """
    Gera um arquivo GPX a partir de uma lista de coordenadas em (lon, lat).
    Cada coordenada da lista vira um <trkpt> dentro de um <trkseg>.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(
            '<gpx version="1.1" creator="MeuScript" '
            'xmlns="http://www.topografix.com/GPX/1/1" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
            'http://www.topografix.com/GPX/1/1/gpx.xsd">\n'
        )
        f.write('  <trk>\n')
        f.write('    <name>Rota Gerada</name>\n')
        f.write('    <trkseg>\n')

        for (lon, lat) in rota:
            # GPX precisa lat="..." e lon="..."
            # Supondo que (lon, lat) está em graus (EPSG:4326)
            f.write(f'      <trkpt lat="{lat}" lon="{lon}"></trkpt>\n')

        f.write('    </trkseg>\n')
        f.write('  </trk>\n')
        f.write('</gpx>\n')


def add_node_in_edge(G, point):
    """
    Insere um novo nó em G (um DiGraph) 'no meio' da aresta direcionada (u->v)
    mais próxima ao 'point'.
    - Remove a aresta antiga (u->v).
    - Cria duas arestas: (u->new_node) e (new_node->v).
    - Mantém os atributos de 'length' e 'geometry' subdivididos.

    Retorna (G, new_node), onde:
      - G é o DiGraph atualizado
      - new_node é a tupla (x_new, y_new) do nó recém-criado (em coordenadas do grafo)

    Observações importantes:
      1) Se no seu grafo existir também a aresta (v->u), esta NÃO será alterada
         automaticamente. Você pode repetir a lógica se quiser também quebrar a
         direção inversa (v->u).
      2) Se não houver 'geometry' nas arestas, criamos uma LineString[(u),(v)].
      3) Se o grafo estiver em lat/long, você estará usando distância euclidiana
         ou geopy dentro do 'length'? Ajuste conforme sua necessidade.
      4) Se nenhuma aresta for encontrada, retornamos (G, None).
    """

    min_dist = math.inf
    nearest_edge = None
    nearest_line = None

    # 1. Localizar a aresta mais próxima do 'point'
    for (u, v, data) in G.edges(data=True):
        # Pegamos a geometria armazenada ou criamos a partir de (u, v)
        line = data.get("geometry", None)
        if line is None:
            line = LineString([u, v])

        dist = line.distance(point)
        if dist < min_dist:
            min_dist = dist
            nearest_edge = (u, v, data)
            nearest_line = line

    if nearest_edge is None or nearest_line is None:
        print("Nenhuma aresta encontrada para inserir o novo nó.")
        return G, None

    (u, v, data) = nearest_edge

    # 2. Projetar 'point' sobre a line para achar a posição exata
    proj_dist = nearest_line.project(point)
    new_point = nearest_line.interpolate(proj_dist)
    x_new, y_new = new_point.x, new_point.y
    new_node = (x_new, y_new)

    # 3. Remover a aresta antiga (u->v)
    if G.has_edge(u, v):
        G.remove_edge(u, v)

    # 4. Dividir a geometria em duas sub-linhas
    line_a = LineString([u, new_node])
    line_b = LineString([new_node, v])

    dist_a = line_a.length
    dist_b = line_b.length

    # 5. Adicionar a nova aresta (u->new_node)
    G.add_edge(u, new_node, length=dist_a, geometry=line_a)
    # 6. Adicionar a nova aresta (new_node->v)
    G.add_edge(new_node, v, length=dist_b, geometry=line_b)

    # 7. Assegurar que o nó novo está presente
    G.add_node(new_node)

    return G, new_node


def geojson_dict_to_G(geojson_dict):
    """
    Recebe um dicionário no formato GeoJSON (já carregado),
    cria um GeoDataFrame, e converte para um grafo dirigido (nx.DiGraph),
    respeitando vias de mão única ou mão dupla com base na propriedade 'oneway'.

    Regra de exemplo:
      - Se feature["properties"]["oneway"] == "true", insere arestas só na direção
        do vértice[i] -> vértice[i+1].
      - Se == "false", insere arestas nas duas direções.

    geojson_dict: dicionário seguindo o formato GeoJSON
                  ex: {
                        "type": "FeatureCollection",
                        "features": [
                          {
                            "type": "Feature",
                            "properties": {"oneway": "true", ...},
                            "geometry": {...}
                          }, ...
                        ]
                      }

    Retorna: nx.DiGraph
    """

    # 1. Converter o dict GeoJSON para um GeoDataFrame
    #    Extraindo a geometria e as propriedades de cada feature
    features_list = []
    for feature in geojson_dict.get("features", []):
        geometry = shape(feature["geometry"])  # cria uma geometria shapely
        props = feature.get("properties", {}).copy()
        props["geometry"] = geometry
        features_list.append(props)

    # Construir um GeoDataFrame em CRS lat/lon (EPSG:4326) – ajuste se for outro
    gdf = gpd.GeoDataFrame(features_list, crs="EPSG:4326")

    # 2. Criar o DiGraph
    G = nx.DiGraph()
    found_lines = 0

    # 3. Definir função auxiliar para inserir as arestas
    def add_edges_between_coords(coords, oneway):
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]

            # Distância geodésica em metros, via geopy
            dist_m = distance((lat1, lon1), (lat2, lon2)).meters

            # Sempre adicionamos a aresta de (lon1, lat1) -> (lon2, lat2)
            G.add_node((lon1, lat1))
            G.add_node((lon2, lat2))
            G.add_edge((lon1, lat1), (lon2, lat2), length=dist_m)

            # Se a via não for oneway, adicionamos também a direção contrária
            if oneway == "false":
                G.add_edge((lon2, lat2), (lon1, lat1), length=dist_m)

    # 4. Iterar nas linhas do GeoDataFrame
    for _, row in gdf.iterrows():
        geom = row["geometry"]
        oneway_value = row.get("oneway", "false")  # default "false"

        if isinstance(geom, LineString):
            found_lines += 1
            coords = list(geom.coords)
            add_edges_between_coords(coords, oneway_value)

        elif isinstance(geom, MultiLineString):
            for line_part in geom:
                if isinstance(line_part, LineString):
                    found_lines += 1
                    coords = list(line_part.coords)
                    add_edges_between_coords(coords, oneway_value)
        else:
            # Ignora geometrias que não sejam (Multi)LineString
            pass

    if found_lines == 0:
        raise ValueError("Nenhuma (Multi)LineString encontrada no dicionário GeoJSON.")

    return G

def get_dict_from_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

if __name__ == '__main__':
    args = get_cli_args()
    print(f"PROJECT_ID → {args.project_id}")
    workflow_id = 'router' #args.project_id
    main(workflow_id, args.project_id)