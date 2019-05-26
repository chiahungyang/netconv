"""
decoders.py
-----------

Convert texts to GraphData.

"""

from .graph import GraphData
from io import BytesIO
import lxml.etree as ET

def parse(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        try:
            return float(s)
        except (ValueError, TypeError):
            return s


def decode_edgelist(text, delimiter=' ', attr=False, header=False):
    """Return a GraphData object converted from a text of edgelist."""
    g = GraphData()
    n_counter = 0
    label2id = dict()

    for line in text.strip().split('\n'):
        node1, node2, *attrs = line.strip().split(sep=delimiter)

        # Add nodes
        for n in [node1, node2]:
            if n not in label2id:
                label2id[n] = n_counter
                n_counter += 1
                g.nodes.append((n,))

        # Add the edge
        edge = [(label2id[node1], label2id[node2])]
        if attr:
            edge += attrs
        g.edges.append(tuple(edge))

    return g


def decode_graphml(text):
    """
    Return a GraphData object parsed from `text`.
    """

    G = GraphData()

    it = ET.iterparse(BytesIO(str.encode(text)))
    # strip the XML namespace to simplify things
    for _, el in it:
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    root = it.root

    graph_attrs = {'directed': False}
    node_attrs = set()
    node_idx_to_id = dict()
    node_idx = 0
    directed = False
    edge_attrs = set()
    edge_idx = 0
    num_edges = 0

    # traverse iterator twice, hitting all the nodes and attrs
    # and then all the edges

    # first pass
    for item in root.iter():
        tag, attrib = item.tag, item.attrib
        if tag == 'graph':
            if item.attrib.get('edgedefault',
                               'undirected').lower() == 'directed':
                graph_attrs['directed'] = True
                # TODO: in theory, individual edges can disobey edgedefault,
                # so we should check the directedness of all edges. However,
                # it is unlikely that many GraphML objects disobey edgedefault
                # in this way.

            data = item.findall("data")
            for dat in data:
                if 'key' in dat.attrib:
                    graph_attrs[dat.attrib['key']] = dat.text
        elif tag == 'node':
            data = item.getchildren()
            for dat in data:
                node_attrs.update({list(dat.attrib.values())[0]})

            node_idx_to_id[attrib['id']] = node_idx
            node_idx += 1

            entry = [attrib['id']]
            G.nodes.append(entry)

        elif tag == 'edge':
            num_edges += 1
            data = item.getchildren()
            for dat in data:
                edge_attrs.update({list(dat.attrib.values())[0]})

    edge_attrs = ['edge'] + list(edge_attrs)
    edge_attr_lookup = {v:i for i, v in enumerate(edge_attrs)}
    G.edges = [[None for _ in range(len(edge_attrs))] for _ in range(num_edges)]
    for node in G.nodes:
        node.extend([None for _ in range(len(node_attrs))])
    node_attrs = ['label'] + list(node_attrs)
    node_attr_lookup = {v:i for i, v in enumerate(node_attrs)}
    node_idx = 0

    # second pass
    for item in root.iter():
        tag, attrib = item.tag, item.attrib
        if tag == 'node':
            data = item.getchildren()
            for dat in data:
                idx = node_attr_lookup[dat.attrib.values()[0]]
                G.nodes[node_idx][idx] = parse(dat.text)
            node_idx += 1

        elif tag == 'edge':

            G.edges[edge_idx][0] = (node_idx_to_id[attrib['source']],
                      node_idx_to_id[attrib['target']])

            data = item.getchildren()
            for dat in data:
                idx = edge_attr_lookup[dat.attrib.values()[0]]
                G.edges[edge_idx][idx] = parse(dat.text)

            edge_idx += 1

    G.graph_attr = graph_attrs
    G.node_attr = node_attrs
    G.edge_attr = edge_attrs
    G.edges = [tuple(x) for x in G.edges]
    G.nodes = [tuple(x) for x in G.nodes]

    return G
