import networkx as nx
import matplotlib.pyplot as plt

def build_graph(relationships):
    """
    Construye un grafo no dirigido a partir de relaciones triples (src, rel, tgt).
    """
    G = nx.Graph()
    for src, rel, tgt in relationships:
        G.add_node(src)
        G.add_node(tgt)
        # Añadimos la arista con el atributo 'label' para la relación
        G.add_edge(src, tgt, label=rel)
    return G

def draw_graph(G):
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(12, 8))
    nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=1500)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
    nx.draw_networkx_edges(G, pos)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')
    plt.axis('off')
    plt.title("Grafo de Relaciones entre Entidades")
    plt.show()