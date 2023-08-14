# ===============================================================================

import ast
import logging as log
import os
import re
from urllib.parse import urljoin

import rdflib
import requests
import stardog

from npoexplorer.query import Namespace, Query

# ===============================================================================

ENDPOINT_STARDOG = "https://sd-63f05fc2.stardog.cloud:5820"
ENDPOINT_BLAZEGRAPH = "https://blazegraph.scicrunch.io/blazegraph/sparql"
NPO_USERNAME = os.environ.get("NPO_USERNAME")
NPO_PASSWORD = os.environ.get("NPO_PASSWORD")
DB_NAME = "NPO"

NPO_OWNER = "SciCrunch"
NPO_REPO = "NIF-Ontology"
NPO_BRANCH = "neurons"

NPO_DIR = "ttl/generated/neurons"
NPO_SOURCE = f"https://raw.githubusercontent.com/{NPO_OWNER}/{NPO_REPO}/{NPO_BRANCH}/"
NPO_API = f"https://api.github.com/repos/{NPO_OWNER}/{NPO_REPO}/contents/{NPO_DIR}?ref={NPO_BRANCH}"
NPO_FILES = {
    "NPO": "../../npo.ttl",
    "NEU_POP": "apinatomy-neuron-populations.ttl",
    "PARTIAL_ORDER": "apinat-partial-orders.ttl",
    "POPS_MORE": "apinat-pops-more.ttl",
    "SIMP_SHEET": "apinat-simple-sheet.ttl",
    "NLP": "sparc-nlp.ttl",
}

SCKAN_TO_NPO_MODEL = {
    "https://apinatomy.org/uris/models/ard-arm-cardiac": "ilxtr:NeuronAacar",
    "https://apinatomy.org/uris/models/bolser-lewis": "ilxtr:NeuronBolew",
    "https://apinatomy.org/uris/models/bronchomotor": "ilxtr:NeuronBromo",
    "https://apinatomy.org/uris/models/keast-bladder": "ilxtr:NeuronKblad",
    "https://apinatomy.org/uris/models/pancreas": "ilxtr:NeuronPancr",
    "https://apinatomy.org/uris/models/sawg-distal-colon": "ilxtr:NeuronSdcol",
    "https://apinatomy.org/uris/models/spleen": "ilxtr:NeuronSplen",
    "https://apinatomy.org/uris/models/sawg-stomach": "ilxtr:NeuronSstom",
}

NPO_TO_SCKAN_MODEL = {
    term_npo: term_sckan for term_sckan, term_npo in SCKAN_TO_NPO_MODEL.items()
}

# Layers shouldn't be resolving to
# ``spinal cord``, etc. nor to ``None``.
# A SCKAN issue
EXCLUDED_LAYERS = (
    None,
    'UBERON:0000010',      # peripheral nervous system
    'UBERON:0000178',      # blood
    'UBERON:0000468',      # multicellular organism
    'UBERON:0001017',      # central nervous system
    'UBERON:0001359',      # cerebrospinal fluid
    'UBERON:0002318',      # spinal cord white matter
    'UBERON:0003714',      # neural tissue
    'UBERON:0005844',      # spinal cord segment
    'UBERON:0016549',      # cns white matter
)

# ===============================================================================

__version__ = "0.0.2"

# ===============================================================================

class SPARQLConnection(stardog.Connection):
    def __init__(self, endpoint) -> None:
        self.__ep = endpoint
        if endpoint == ENDPOINT_STARDOG:
            connection_details = {
                "endpoint": endpoint,
                "username": NPO_USERNAME,
                "password": NPO_PASSWORD,
            }
            super().__init__(DB_NAME, **connection_details)
            super().begin()

    def select(self, query):
        if self.__ep == ENDPOINT_STARDOG:
            return super().select(query)
        elif self.__ep == ENDPOINT_BLAZEGRAPH:
            headers = {
                "Accept": "application/sparql-results+json",  # Set the desired response format
            }
            params = {
                "query": query,
            }
            response = requests.get(self.__ep, headers=headers, params=params, timeout=10)
            return response.json()

    def close(self):
        if self.__ep == ENDPOINT_STARDOG:
            super().close()

# ===============================================================================

class NPOExplorer:
    def __init__(self, allow_loop=False, endpoint=ENDPOINT_STARDOG) -> None:
        self.__conn = SPARQLConnection(endpoint)
        self.__connectivity_models = self.__get_connectivity_models()
        self.__labels = {}
        # self.__load_npo_as_graph()
        self.__load_npo_connectivities(allow_loop)
        self.__load_npo_mmset_connectivities()

        _, db_version = self.__select(Query.DB_VERSION)
        self.__metadata = {
            "SimpleSCKAN": db_version[0]["SimpleSCKAN"]["value"],
            "NPO": db_version[0]["NPO"]["value"],
        }
        s_sckan_term = f'SimpleSCKAN built at {self.__metadata["SimpleSCKAN"]}'
        npo_term = f'NPO built at {self.__metadata["NPO"]}'
        log.info(
            f"NPO Explorer version {__version__} using {s_sckan_term} and {npo_term}"
        )

    def __load_npo_connectivities(self, allow_loop):
        # loading partial connectivities from NPO repository
        # due to unvailability in stardog
        url = f'{NPO_SOURCE}{NPO_DIR}/{NPO_FILES["PARTIAL_ORDER"]}'
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                partial_order_text = response.text
            else:
                log.error(
                    f'Failed to load {NPO_FILES["PARTIAL_ORDER"]}. Status code: {response.status_code}'
                )
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching the file: {e}")

        # functions to parse connectivities
        def parse_connectivities(connectivities, sub_structure, root="blank"):
            for sub_sub in sub_structure:
                adj = (
                    (
                        list(reversed(sub_sub[0]))[0],
                        tuple(list(reversed(sub_sub[0]))[1:]),
                    )
                    if isinstance(sub_sub[0], list)
                    else (sub_sub[0], ())
                )
                if root != ("blank", ()):
                    if root != adj or allow_loop:
                        connectivities += [(root, adj)]
                if len(sub_sub) > 1:
                    parse_connectivities(connectivities, sub_sub[1:], adj)

        # function to filter layer terms, returning filtered_edge
        def filter_layer(connectivity):
            edge = []
            for node in connectivity:
                new_node = []
                for terms in node:
                    if isinstance(terms, tuple):
                        terms = [t for t in terms if t not in EXCLUDED_LAYERS]
                        new_node += [tuple(terms)]
                    else:
                        terms = terms if terms not in EXCLUDED_LAYERS else []
                        new_node += [terms]
                if len(new_node[0]) == 0 and len(new_node[1]) == 0:
                    return []
                elif len(new_node[0]) == 0:
                    new_node = [new_node[1][0], tuple(list(new_node[1])[1:])]
                edge += [tuple(new_node)]
            return tuple(edge)

        self.__connectivities = {}
        for partial_order in partial_order_text.split("\n\n"):
            if "neuronPartialOrder" in partial_order:
                neuron, nested_structure = partial_order.split(
                    "ilxtr:neuronPartialOrder"
                )
                nested_structure = nested_structure.replace(".", "")
                # replace consecutive space with a single space
                nested_structure = re.sub(
                    r"\s+", " ", nested_structure).strip()
                # adding coma
                pattern = r"\[([^]]+)\]"

                def add_comma(match):
                    elements = match.group(1).strip().split()
                    return "[" + ", ".join(elements) + "]"

                nested_structure = re.sub(pattern, add_comma, nested_structure)
                # Quoting ILX and UBERON
                pattern = r"(ILX:\d+|UBERON:\d+)"
                nested_structure = re.sub(pattern, r'"\1"', nested_structure)
                # Specifying tuple
                nested_structure = nested_structure.replace(" )", ", )").replace(
                    " ( ", ", ( "
                )
                # convert to tuple
                conn_structure = ast.literal_eval(nested_structure)
                # parse connectivities
                connectivities = []
                if conn_structure != "blank":
                    if len(conn_structure) > 1:
                        root = (
                            (
                                list(reversed(conn_structure[0]))[0],
                                tuple(list(reversed(conn_structure[0]))[1:]),
                            )
                            if isinstance(conn_structure[0], list)
                            else (conn_structure[0], ())
                        )
                        parse_connectivities(
                            connectivities, conn_structure[1:], root)
                # filter connectivities based on EXCLUDE_LAYERS
                connectivities = [filter_layer(
                    c) for c in connectivities if len(filter_layer(c)) > 0]
                self.__connectivities[neuron.strip()] = connectivities

    def __load_npo_mmset_connectivities(self):
        _, results = self.__select(Query.NPO_PARTIAL_ORDER)
        for rst in results:
            neuron_IRI = rst["Neuron_IRI"]["value"]
            neuron_label = rst.get("Neuron_Label", {}).get("value", "")
            v1 = rst.get("V1", {}).get("value", "")
            v1_label = rst.get("V1_Label", {}).get("value", "")
            v2 = rst.get("V2", {}).get("value", "")
            v2_label = rst.get("V2_Label", {}).get("value", "")
            if v1 != "" or v2 != "":
                if neuron_IRI not in self.__connectivities:
                    self.__connectivities[neuron_IRI] = []
                self.__connectivities[neuron_IRI] += [((v1, ()), (v2, ()))]
                self.__labels[v1] = v1_label
                self.__labels[v2] = v2_label
                self.__labels[neuron_IRI] = neuron_label

    def __load_npo_as_graph(self):
        # this function is prepared to generate npo graph
        # the graph will be useful when the needed information is not available in stardog
        self.__graph = rdflib.Graph()
        for ttl_file in NPO_FILES.values():
            try:
                ttl_url = urljoin(f"{NPO_SOURCE}{NPO_DIR}/", f"{ttl_file}")
                self.__graph.parse(ttl_url, format="turtle")
            except Exception:
                log.error(f"Cannot load {ttl_file}")
        from rdflib.namespace import Namespace

        rdfs = Namespace(Namespace.namespaces["rdfs"])
        for subject, obj in self.__graph.subject_objects(rdfs.label):
            self.__labels[Namespace.curie(str(subject))] = str(obj)

    def __select(self, query):
        data = self.__conn.select(query)
        variables = data["head"]["vars"]
        results = data["results"]["bindings"]
        for rst in results:
            for v in rst.values():
                if v["type"] == "uri":
                    v["value"] = Namespace.curie(v["value"])
        return variables, results

    def __get_connectivity_models(self):
        variables, results = self.__select(Query.MODELS)
        models = {}
        for rst in results:
            value = rst[variables[0]]["value"]
            models[value] = {"label": "", "version": ""}
        return models

    def __get_model_knowledge(self, entity):
        query = Query.MODEL_KNOWLEDGE.format(entity=entity)
        variables, results = self.__select(query)
        paths, references = [], set()
        for rst in results:
            path = rst[variables[0]]["value"]
            paths.append({"id": path, "models": path})
            if variables[1] in rst:
                reference = rst[variables[1]]["value"]
                references.add(reference)
        return {
            "id": entity,
            "label": entity,
            "paths": list(paths),
            "references": list(references),
        }

    def __get_neuron_connectivities(self, entity):
        # this function should be a standard method to get partial connectivity from stardog
        # currently is not used
        query = Query.CONNECTIVITY.format(entity=entity)
        _, results = self.__select(query)
        connectivities = []
        if len(results) > 0:
            self.__labels[results[0]["Region"]["value"]] = (
                results[0]["Region_Label"]["value"]
                if "Region_Label" in results[0]
                else ""
            )
            self.__labels[results[0]["Layer"]["value"]] = (
                results[0]["Layer_Label"]["value"]
                if "Layer_Label" in results[0]
                else ""
            )

            for idx in range(1, len(results)):
                prev_count = int(results[idx - 1]["Count"]["value"])
                count = int(results[idx]["Count"]["value"])
                if count > prev_count:
                    prev_layer = results[idx - 1]["Layer"]["value"]
                    prev_region = results[idx - 1]["Region"]["value"]
                    layer = results[idx]["Layer"]["value"]
                    region = results[idx]["Region"]["value"]
                    connectivities += [
                        (
                            (
                                prev_region,
                                (prev_layer,)
                                if "UBERON:" in prev_layer or "ILX:" in prev_layer
                                else (),
                            ),
                            (
                                region,
                                (layer,)
                                if "UBERON:" in layer or "ILX:" in layer
                                else (),
                            ),
                        )
                    ]
                else:
                    prev_idx = idx - 1
                    prev_count = int(results[prev_idx]["Count"]["value"])
                    while prev_count >= count:
                        prev_idx = prev_idx - 1
                        prev_count = int(results[prev_idx]["Count"]["value"])
                    if prev_idx <= 0:
                        continue
                    else:
                        prev_idx -= 1
                        prev_layer = results[prev_idx]["Layer"]["value"]
                        prev_region = results[prev_idx]["Region"]["value"]
                        layer = results[idx]["Layer"]["value"]
                        region = results[idx]["Region"]["value"]
                        connectivities += [
                            (
                                (
                                    prev_region,
                                    (prev_layer,)
                                    if "UBERON:" in prev_layer or "ILX:" in prev_layer
                                    else (),
                                ),
                                (
                                    region,
                                    (layer,)
                                    if "UBERON:" in layer or "ILX:" in layer
                                    else (),
                                ),
                            )
                        ]

                self.__labels[results[idx]["Region"]["value"]] = (
                    results[idx]["Region_Label"]["value"]
                    if "Region_Label" in results[idx]
                    else ""
                )
                self.__labels[results[idx]["Layer"]["value"]] = (
                    results[idx]["Layer_Label"]["value"]
                    if "Layer_Label" in results[idx]
                    else ""
                )

        return connectivities

    def __get_connectivity_terms(self, entity):
        query = Query.CONNECTIVITY.format(entity=entity)
        _, results = self.__select(query)
        for rst in results:
            if "Region" in rst:
                if rst["Region"]["type"] == "uri":
                    self.__labels[rst["Region"]["value"]] = (
                        rst["Region_Label"]["value"] if "Region_Label" in rst else ""
                    )
            if "Layer" in rst:
                if rst["Layer"]["type"] == "uri":
                    self.__labels[rst["Layer"]["value"]] = (
                        rst["Layer_Label"]["value"] if "Layer_Label" in rst else ""
                    )

    def __get_neuron_knowledge(self, entity):
        query = Query.NEURON.format(entity=entity)
        _, results = self.__select(query)

        if len(results) == 0:
            return {"label": entity}

        def get_node(rst, nodes):
            obj = rst["Object"]["value"]
            if obj not in nodes:
                nodes[obj] = {"region": [], "layer": []}
            if "Region" in rst:
                nodes[obj]["region"] += [rst["Region"]["value"]]

        def combine_layer_regions(nodes):
            combines = []
            for obj, lr in nodes.items():
                node = lr["region"] + [obj] + lr["layer"]
                combines += [
                    (node[0], tuple(node[1:])) if len(
                        node) > 1 else (node[0], ())
                ]
            return combines

        somas, axons, dendrites, vias = {}, {}, {}, {}
        phenotypes, references, taxons, long_label = [], [], [], ""
        for rst in results:
            # get soma
            if rst["Predicate"]["value"] in Query.predicates["SOMA"]:
                get_node(rst, somas)
            # get axon
            elif rst["Predicate"]["value"] in Query.predicates["AXON_TERMINAL"]:
                get_node(rst, axons)
            # get dendrite
            elif rst["Predicate"]["value"] in Query.predicates["DENDRITE"]:
                get_node(rst, dendrites)
            # get vias
            if rst["Predicate"]["value"] in Query.predicates["AXON_VIA"]:
                get_node(rst, vias)
            # get phenotypes
            elif rst["Predicate"]["value"] in Query.predicates["PHENOTYPE"]:
                if (
                    rst["Object"]["value"].replace("phenotype", "type")
                    != rst["Neuron_IRI"]["value"]
                ):
                    phenotypes += [rst["Object"]["value"]]
            # get references
            elif rst["Predicate"]["value"] in Query.predicates["REFERENCE"]:
                references += [[rst["Object"]["value"]]]
            # get taxons
            elif rst["Predicate"]["value"] in Query.predicates["TAXON"]:
                taxons += [[rst["Object"]["value"]]]
            # get label
            elif rst["Predicate"]["value"] in Query.predicates["LABEL"]:
                long_label = rst["Object"]["value"]
            # get all labels
            if "Object" in rst and rst["Object"]["type"] == "uri":
                self.__labels[rst["Object"]["value"]] = (
                    rst["Object_Label"]["value"] if "Object_Label" in rst else ""
                )
            # if 'Region' in rst and rst['Region']['type']=='uri':
            #     self.__labels[rst['Region']['value']] = rst['Region_Label']['value'] if 'Region_Label' in rst else ''
            # if 'Layer' in rst and rst['Layer']['type']=='uri':
            #     self.__labels[rst['Layer']['value']] = rst['Layer_Label']['value'] if 'Layer_Label' in rst else ''

        # set neuron label
        self.__labels[entity] = long_label

        # map connectivity
        somas = combine_layer_regions(somas)
        axons = combine_layer_regions(axons)
        dendrites = combine_layer_regions(dendrites)

        # connectivities = self.__get_neuron_connectivities(entity)
        connectivities = self.__connectivities[entity]

        # get required connectivity terms
        self.__get_connectivity_terms(entity)

        return {
            "soma": somas,
            "axons": axons,
            "connectivity": connectivities,
            "dendrites": dendrites,
            "errors": [],
            "id": entity,
            "label": entity,
            "long-label": long_label,
            "phenotypes": phenotypes,
            "references": references,
            "taxon": taxons,
        }

    def connectivity_models(self):
        return self.__connectivity_models

    def entity_knowledge(self, entity):
        if entity in SCKAN_TO_NPO_MODEL:
            entity = SCKAN_TO_NPO_MODEL[entity]
        entity = Namespace.curie(entity)
        if entity in self.__connectivity_models:
            return self.__get_model_knowledge(entity)
        else:
            return self.__get_neuron_knowledge(entity)

    def labels(self):
        return self.__labels

    def label(self, entity):
        if entity in self.__labels:
            return self.__labels[entity]
        return ""

    def metadata(self, name=None):
        if name is None:
            return self.__metadata
        elif name in self.__metadata:
            return self.__metadata[name]

    def close(self):
        self.__conn.close()


# ===============================================================================
