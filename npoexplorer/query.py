class Namespace:
    namespaces = {
        "mmset1": "http://uri.interlex.org/tgbugs/uris/readable/sparc-nlp/mmset1/",
        "mmset2cn": "http://uri.interlex.org/tgbugs/uris/readable/sparc-nlp/mmset2cn/",
        "mmset4": "http://uri.interlex.org/tgbugs/uris/readable/sparc-nlp/mmset4/",
        "prostate": "http://uri.interlex.org/tgbugs/uris/readable/sparc-nlp/prostate/",
        "semves": "http://uri.interlex.org/tgbugs/uris/readable/sparc-nlp/semves/",
        "ilxtr": "http://uri.interlex.org/tgbugs/uris/readable/",
        "ILX": "http://uri.interlex.org/base/ilx_",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "UBERON": "http://purl.obolibrary.org/obo/UBERON_",
        "NCBITaxon": "http://purl.obolibrary.org/obo/NCBITaxon_",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }

    @staticmethod
    def uri(curie: str) -> str:
        parts = curie.split(":", 1)
        if len(parts) == 2 and parts[0] in Namespace.namespaces:
            return Namespace.namespaces[parts[0]] + parts[1]
        return curie

    @staticmethod
    def curie(uri: str) -> str:
        uri = Namespace.uri(uri)
        for prefix, ns_uri in Namespace.namespaces.items():
            if uri.startswith(ns_uri):
                return f"{prefix}:{uri[len(ns_uri):]}"
        return uri

    @staticmethod
    def is_curie(curie: str) -> bool:
        if ':' in curie:
            return True
        return False


class Query:
    predicates = {
        "SOMA": ["ilxtr:hasSomaLocation"],
        "AXON_TERMINAL": [
            "ilxtr:hasAxonTerminalLocation",
            "ilxtr:hasAxonSensoryLocation",
        ],
        "DENDRITE": ["ilxtr:hasDendriteLocation"],
        "AXON_VIA": ["ilxtr:hasAxonLocation"],
        "PHENOTYPE": [
            "ilxtr:hasNeuronalPhenotype",
            "ilxtr:hasFunctionalCircuitRole",
            "ilxtr:hasCircuitRole",
            "ilxtr:hasProjection",
        ],
        "REFERENCE": ["ilxtr:reference"],
        "TAXON": ["ilxtr:isObservedInSpecies"],
        "LABEL": ["rdfs:label"],
    }

    prefixes = (
        "\n".join(
            [f"PREFIX {pref}: <{link}>" for pref, link in Namespace.namespaces.items()]
        )
        + "\n"
    )

    MODELS = """
        SELECT DISTINCT ?Model_ID WHERE{
            ?Model_ID rdfs:subClassOf ilxtr:NeuronEBM .
            ?Neuron_ID rdfs:subClassOf ?Model_ID
            FILTER (
                ?Model_ID != ilxtr:NeuronApinatSimple &&
                    STRSTARTS(STR(?Neuron_ID), STR(ilxtr:))
            )
            FILTER NOT EXISTS {
                ?Model_ID rdfs:subClassOf ilxtr:NeuronApinatSimple .
            }
        }
    """

    MODEL_KNOWLEDGE = """
        SELECT DISTINCT ?Neuron_ID ?Reference WHERE{{   
            {{
                SELECT ?Neuron_ID ?Reference {{
                    VALUES(?entity){{({entity})}}
                    ?Neuron_ID rdfs:subClassOf ?entity .
                    OPTIONAL {{?Neuron_ID ilxtr:reference ?Reference.}}
                }}
            }}
            UNION
            {{
                SELECT ?Neuron_ID ?Reference {{
                    VALUES(?entity){{({entity})}}
                    ?Super_Neuron rdfs:subClassOf ?entity .
                    ?Neuron_ID rdfs:subClassOf ?Super_Neuron .
                    ?Neuron_ID rdfs:subClassOf ilxtr:NeuronEBM .
                    OPTIONAL {{?Neuron_ID ilxtr:reference ?Reference.}}
                }}
            }}
        }}
    """

    NEURON = """
        SELECT * WHERE {{
        {{
            SELECT DISTINCT ?Neuron_IRI ?Predicate ?Object ?Object_Label {{
                VALUES(?Neuron_IRI){{({entity})}}
                ?Neuron_IRI ?Predicate ?Object.
                OPTIONAL{{?Object rdfs:label ?Object_Label}}
            }}
        }}
        UNION
        {{
            SELECT DISTINCT ?Neuron_IRI ?Predicate ?Object ?Object_Label {{
                VALUES(?Neuron_IRI){{({entity})}}
                ?Neuron_IRI ?Predicate ?Phenotype.
                ?Phenotype rdfs:subClassOf ?Object.
                OPTIONAL{{?Object rdfs:label ?Object_Label}}
                FILTER (
                ?Predicate IN (
                    ilxtr:hasNeuronalPhenotype,
                    ilxtr:hasFunctionalCircuitRole,
                    ilxtr:hasCircuitRole,ilxtr:hasProjection
                )
                )
            }}
        }}
        }}
    """

    CONNECTIVITY = """
        SELECT ?Layer ?Layer_Label ?Region ?Region_Label (COUNT(?d) AS ?Count) WHERE{{
            VALUES(?Neuron_IRI){{({entity})}}
            ?Neuron_IRI ilxtr:neuronPartialOrder ?o.
            ?o (rdf:first|rdf:rest)* ?d .
            ?d (rdf:first|rdf:rest)* ?e .
            ?e ?Layer ?Region .
            OPTIONAL{{?Layer rdfs:label ?Layer_Label}}
            OPTIONAL{{?Region rdfs:label ?Region_Label}}
            FILTER (REGEX(STR(?Region), STR(ILX:)) || REGEX(STR(?Region), STR(UBERON:)))
            FILTER (?Layer=rdf:first || REGEX(STR(?Layer), STR(ILX:)) || REGEX(STR(?Layer), STR(UBERON:)))
        }} GROUP BY ?Region ?Layer ?Region_Label ?Layer_Label ?e
    """

    DB_VERSION = """
        PREFIX TTL: <https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/neurons/ttl/>
        SELECT DISTINCT ?NPO ?SimpleSCKAN WHERE{{
            OPTIONAL{{TTL:npo.ttl owl:versionInfo ?NPO.}}
            OPTIONAL{{TTL:simple-sckan.ttl owl:versionInfo ?SimpleSCKAN.}}
        }}
    """

    # Query: This query is to extract all partial order useful to construct connectivity models
    # Limitation: Only partial orders in nlp mmset are available
    NPO_PARTIAL_ORDER = """
        SELECT DISTINCT
        ?Neuron_IRI ?Neuron_Label ?V1 ?V1_Label ?V2 ?V2_Label
        WHERE
        {
            ?Neuron_IRI ilxtr:neuronPartialOrder ?o .
            ?o (rdf:rest|rdf:first)* ?r1 .
            ?o (rdf:rest|rdf:first)* ?r2 .
            ?r1 rdf:rest|rdf:first ?V1 .
            ?r2 rdf:rest|rdf:first ?V2 .
            ?V1 rdf:type owl:Class .
            ?V2 rdf:type owl:Class .
            ?mediator rdf:first ?V1 .  # car
            ?mediator rdf:rest*/rdf:first/rdf:first ?V2 .  # caadr
            ?V1 rdfs:label ?V1_Label.
            ?V2 rdfs:label ?V2_Label.
            OPTIONAL {?Neuron_IRI rdfs:label ?Neuron_Label.}

        FILTER (?V1 != ?V2) .
        FILTER (CONTAINS(STR(?Neuron_IRI), 'sparc-nlp')) .
        } 
        ORDER BY ?Neuron_IRI 
        limit 100000
    """
