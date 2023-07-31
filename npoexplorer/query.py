class NAMESPACES:
    namespaces = {
        'ilxtr'     : 'http://uri.interlex.org/tgbugs/uris/readable/',
        'ILX'       : 'http://uri.interlex.org/base/ilx_',
        'rdfs'      : 'http://www.w3.org/2000/01/rdf-schema#',
        'UBERON'    : 'http://purl.obolibrary.org/obo/UBERON_',
        'NCBITaxon' : 'http://purl.obolibrary.org/obo/NCBITaxon_',
        'rdf'       : 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    }

    @staticmethod
    def uri(curie: str) -> str:
        parts = curie.split(':', 1)
        if len(parts) == 2 and parts[0] in NAMESPACES.namespaces:
            return NAMESPACES.namespaces[parts[0]] + parts[1]
        return curie

    @staticmethod
    def curie(uri: str) -> str:
        for prefix, ns_uri in NAMESPACES.namespaces.items():
            if uri.startswith(ns_uri):
                return f'{prefix}:{uri[len(ns_uri):]}'
        return uri

class QUERIES:

    PREDICATES = {
        'SOMA'          : ['ilxtr:hasSomaLocation'],
        'AXON_TERMINAL' : ['ilxtr:hasAxonTerminalLocation', 'ilxtr:hasAxonSensoryLocation'],
        'DENDRITE'      : ['ilxtr:hasDendriteLocation'],
        'AXON_VIA'      : ['ilxtr:hasAxonLocation'],
        'PHENOTYPE'     : ['ilxtr:hasNeuronalPhenotype', 'ilxtr:hasFunctionalCircuitRole',
                           'ilxtr:hasCircuitRole', 'ilxtr:hasProjection'],
        'REFERENCE'     : ['ilxtr:reference'],
        'TAXON'         : ['ilxtr:isObservedInSpecies'],
        'LABEL'         : ['rdfs:label'],
    }

    PREFIXES = '\n'.join([f'PREFIX {pref}: <{link}>' for pref, link in NAMESPACES.namespaces.items()]) + '\n'

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

    # Query: This query is for loading all object related to a subject
    # This is sufficient to obtain information about a population of neurons. 
    # The identification of the next attribute is at the code level.
    # NEURON = """
    #     SELECT DISTINCT ?Neuron_IRI ?Predicate ?Object ?Object_Label ?Region ?Region_Label ?Layer ?Layer_Label {{
    #         VALUES(?Neuron_IRI){{({entity})}}
    #         ?Neuron_IRI ?Predicate ?Object.
    #         OPTIONAL{{?Object rdfs:label ?Object_Label}}
    #         OPTIONAL{{
    #             ?_1 ?Object ?Region .
    #             OPTIONAL{{?Region rdfs:label ?Region_Label .}}
    #         }}
    #         OPTIONAL{{
    #             ?Neuron_IRI (
    #                 ilxtr:hasSomaLocation|
    #                 ilxtr:hasAxonTerminalLocation|
    #                 ilxtr:hasAxonSensoryLocation|
    #                 ilxtr:hasDendriteLocation|
    #                 ilxtr:hasAxonLocation
    #                 ) ?Object .
    #             ?_2 ?Layer ?Object .
    #             OPTIONAL{{?Layer rdfs:label ?Layer_Label .}}
    #             FILTER(STRSTARTS(STR(?Layer), STR(UBERON:)) || STRSTARTS(STR(?Layer), STR(ILX:)))
    #         }}
    #     }}
    # """
    NEURON = """
        SELECT DISTINCT ?Neuron_IRI ?Predicate ?Object ?Object_Label {{
            VALUES(?Neuron_IRI){{({entity})}}
            ?Neuron_IRI ?Predicate ?Object.
            OPTIONAL{{?Object rdfs:label ?Object_Label}}
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
    