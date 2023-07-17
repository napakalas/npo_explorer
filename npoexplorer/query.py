
class NAMESPACES:
    namespaces = {
        'ilxtr'     : 'http://uri.interlex.org/tgbugs/uris/readable/',
        'ILX'       : 'http://uri.interlex.org/base/ilx_',
        'rdfs'      : 'http://www.w3.org/2000/01/rdf-schema#',
        'UBERON'    : 'http://purl.obolibrary.org/obo/UBERON_',
        'NCBITaxon' : 'http://purl.obolibrary.org/obo/NCBITaxon_',
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
        ?Neuron_ID rdfs:subClassOf {entity} .
        OPTIONAL {{?Neuron_ID ilxtr:reference ?Reference.}}
    }}
    """

    PHENOTYPES = """
        SELECT DISTINCT  ?Phenotype_IDs
            (group_concat(distinct ?Phenotype_ID; separator=",") as ?Phenotype_IDs) 
            WHERE                  
            {{
                VALUES(?Neuron_IRI){{({entity})}}
                ?Neuron_IRI rdfs:subClassOf*/rdfs:label 'Neuron'. #http://uri.neuinfo.org/nif/nifstd/sao1417703748   
                
                ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
                OPTIONAL {{?Neuron_IRI ilxtr:hasAxonLocation ?C_IRI.}}
                ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
                OPTIONAL {{
                    ?Neuron_IRI (
                        ilxtr:hasNeuronalPhenotype | 
                        ilxtr:hasFunctionalCircuitRole |
                        ilxtr:hasCircuitRole |
                        ilxtr:hasProjection  
                    ) ?Phenotype_ID.
                }}
            }}
    """

    # Query: This query is for loading all object related to a subject
    # This is sufficient to obtain information about a population of neurons. 
    # The identification of the next attribute is at the code level.
    NEURON = """
        SELECT DISTINCT ?Neuron_IRI ?Predicate ?Object ?Object_Label ?Region ?Region_Label ?Layer ?Layer_Label {{
            VALUES(?Neuron_IRI){{({entity})}}
            ?Neuron_IRI ?Predicate ?Object.
            OPTIONAL{{?Object rdfs:label ?Object_Label}}
            OPTIONAL{{
                ?_ ?Object ?Region .
                OPTIONAL{{?Region rdfs:label ?Region_Label .}}
            }}
            OPTIONAL{{
                ?Neuron_IRI (
                    ilxtr:hasSomaLocation|
                    ilxtr:hasAxonTerminalLocation|
                    ilxtr:hasAxonSensoryLocation|
                    ilxtr:hasDendriteLocation|
                    ilxtr:hasAxonLocation
                    ) ?Object .
                ?_2 ?Layer ?Object .
                OPTIONAL{{?Layer rdfs:label ?Layer_Label .}}
                FILTER(STRSTARTS(STR(?Layer), STR(UBERON:)) || STRSTARTS(STR(?Layer), STR(ILX:)))
            }}
        }}
    """

    # QUERY: This query is for loading the a-b-via-c results in sckan-explorer.
    # Neuron populations where A projects to B via some Nerve C
    NEURON_CONNECTIVITIES = """
        SELECT DISTINCT ?A_IRI ?A_Label ?B_IRI ?B_Label ?B_Region_IRI ?C_IRI ?C_Label ?Target_Organ_IRI ?Target_Organ_Label
        {{
            VALUES(?Neuron_IRI){{({entity})}}
            ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
            ?A_IRI rdfs:label ?A_Label.
        
            OPTIONAL {{
                ?Neuron_IRI ilxtr:hasAxonLocation ?C_IRI. 
                ?C_IRI rdfs:label ?C_Label.
            }}
            
            ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
            ?B_IRI (rdfs:label) ?B_Label.

            OPTIONAL{{
                ?B_IRI rdfs:subClassOf+ [rdf:type owl:Restriction ;
                                            owl:onProperty partOf: ; 
                                            owl:someValuesFrom ?Target_Organ_IRI].
                ?Target_Organ_IRI rdfs:label ?Target_Organ_Label     
                FILTER (?Target_Organ_Label in ( 'heart', 'ovary', 'brain', 'urethra', 'esophagus', 'skin of body', 'lung', 'liver', 
                                            'lower urinary tract', 'urinary tract', 'muscle organ','gallbladder', 'colon', 'kidney', 
                                            'large intestine' ,'small intestine', 'stomach', 'spleen', 'urinary bladder', 
                                            'penis', 'clitoris', 'pancreas'))
                
            }}

            OPTIONAL{{
                ?_TMP ?B_IRI ?B_Region_IRI .
            }}
        }}
        ORDER BY ?Neuron_IRI ?A_Label ?B_IRI ?C_Label
    """

    NEURON_META = """
        SELECT DISTINCT ?Neuron_IRI ?Neuron_Label ?Neuron_Pref_Label ?Species_IRIs ?Species ?Sex_IRI ?Sex 
                ?Phenotype_IRIs ?Forward_Connections ?Dendrite_Location_IRIs ?Alert ?Reference
        WHERE
        {{
            VALUES(?Neuron_IRI){{({entity})}}
            {{ 
                SELECT DISTINCT  ?Neuron_IRI ?Neuron_Label ?Neuron_Pref_Label ?Sex_IRI ?Sex ?Alert ?Reference
                WHERE                  
                {{
                    OPTIONAL{{?Neuron_IRI rdfs:label ?Neuron_Label.}}
                    OPTIONAL{{?Neuron_IRI skos:prefLabel ?Neuron_Pref_Label.}}
                    ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
                    ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
                    OPTIONAL {{
                        ?Neuron_IRI ilxtr:hasPhenotypicSex/rdfs:label ?Sex.
                        ?Neuron_IRI ilxtr:hasPhenotypicSex ?Sex_IRI.
                    }}
                    OPTIONAL {{?Neuron_IRI ilxtr:reference ?Reference.}}
                    OPTIONAL {{?Neuron_IRI ilxtr:alertNote ?Alert.}}
                }}
            }}
            
            {{ 
                SELECT DISTINCT ?Neuron_IRI
                (group_concat(distinct ?ObservedIn; separator=",") as ?Species) 
                (group_concat(distinct ?Species_IRI; separator=",") as ?Species_IRIs) 
                WHERE                  
                {{
                    ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
                    ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
                    OPTIONAL {{
                        ?Neuron_IRI ilxtr:isObservedInSpecies/rdfs:label ?ObservedIn.
                        ?Neuron_IRI ilxtr:isObservedInSpecies ?Species_IRI
                    }}
                }}
                GROUP BY ?Neuron_IRI
            }}
            {{
                SELECT DISTINCT ?Neuron_IRI
                (group_concat(distinct ?ForwardConnection; separator=",") as ?Forward_Connections)  
                WHERE                  
                {{
                    ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
                    ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
                    OPTIONAL {{?Neuron_IRI ilxtr:hasForwardConnection ?ForwardConnection.}}
                }}
                GROUP BY ?Neuron_IRI
            }}

            {{   
                SELECT DISTINCT ?Neuron_IRI  
                (group_concat(distinct ?Phenotype_IRI; separator=",") as ?Phenotype_IRIs) 
                WHERE                  
                {{
                    ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
                    ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
                    OPTIONAL {{?Neuron_IRI (ilxtr:hasNeuronalPhenotype | 
                                        ilxtr:hasFunctionalCircuitRole |
                                        ilxtr:hasCircuitRole |
                                        ilxtr:hasProjection  
                                        ) ?Phenotype_IRI.}}
                }}
                GROUP BY ?Neuron_IRI
            }}

            {{
                SELECT DISTINCT ?Neuron_IRI 
                (group_concat(distinct ?Dendrite_Location_IRI; separator=",") as ?Dendrite_Location_IRIs) 
                WHERE                  
                {{
                    ?Neuron_IRI ilxtr:hasSomaLocation ?A_IRI.
                    ?Neuron_IRI (ilxtr:hasAxonTerminalLocation | ilxtr:hasAxonSensoryLocation) ?B_IRI.
                    OPTIONAL {{?Neuron_IRI ilxtr:hasDendriteLocation ?Dendrite_Location_IRI}}
                }}
                GROUP BY ?Neuron_IRI
            }}
        }}
    """