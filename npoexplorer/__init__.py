#===============================================================================

import stardog
import requests
import os

#===============================================================================

NPO_API_ENDPOINT = 'https://stardog.scicrunch.io:5821'
NPO_USERNAME = os.environ.get('NPO_USERNAME')
NPO_PASSWORD = os.environ.get('NPO_PASSWORD')

#===============================================================================

from npoexplorer.query import QUERIES, NAMESPACES

#===============================================================================

class NPOExplorer():
    def __init__(self) -> None:
        connection_details = {
            'endpoint': NPO_API_ENDPOINT,
            'username': NPO_USERNAME,
            'password': NPO_PASSWORD,
        }
        database_name = 'NPO'
        self.__conn = stardog.Connection(database_name, **connection_details)
        self.__conn.begin()
        self.__connectivity_models = self.__get_connectivity_models()
        self.__labels = {}

    def __select(self, query):
        data = self.__conn.select(query)
        variables = data['head']['vars']
        results = data['results']['bindings']
        for rst in results:
            for k, v in rst.items():
                if v['type'] == 'uri':
                    v['value'] = NAMESPACES.curie(v['value'])
        return variables, results

    def __get_connectivity_models(self):
        variables, results = self.__select(QUERIES.MODELS)
        models = {}
        for result in results:
            value = result[variables[0]]['value']
            models[value] = {'label':'', 'version':''}
        return models

    def __get_model_knowledge(self, entity):
        query = QUERIES.MODEL_KNOWLEDGE.format(entity=entity)
        variables, results = self.__select(query)
        paths, references = [], set()
        for result in results:
            path = result[variables[0]]['value']
            paths.append({'id':path, 'models':path})
            if variables[1] in result:
                reference = result[variables[1]]['value']
                references.add(reference)
        return {'id':entity, 'label':entity, 'paths':list(paths), 'references':list(references)}

    def __get_neuron_knowledge(self, entity):
        query = QUERIES.NEURON.format(entity=entity)
        _, results = self.__select(query)

        def get_node(rst, nodes):
            obj = rst['Object']['value']
            if obj not in nodes:
                nodes[obj] = {'region':[], 'layer':[]}
            if 'Region' in rst:
                nodes[obj]['region'] += [rst['Region']['value']]
            if 'Layer' in rst:
                nodes[obj]['layer'] = [rst['Layer']['value']] + nodes[obj]['layer']

        def combine_layer_regions(nodes):
            combines = []
            for obj, lr in nodes.items():
                node = lr['region']+[obj]+lr['layer']
                combines += [(node[0], tuple(node[1:])) if len(node)>1 else (node[0], ())]
            return combines


        somas, axons, dendrites, vias = {}, {}, {}, {}
        phenotypes, references, taxons, long_label = [], [], [], ''
        for rst in results:
            # get soma
            if rst['Predicate']['value'] in QUERIES.PREDICATES['SOMA']:
                get_node(rst, somas)
            # get axon
            elif rst['Predicate']['value'] in QUERIES.PREDICATES['AXON_TERMINAL']:
                get_node(rst, axons)
            # get dendrite
            elif rst['Predicate']['value'] in QUERIES.PREDICATES['DENDRITE']:
                get_node(rst, dendrites)
            # get vias
            if rst['Predicate']['value'] in QUERIES.PREDICATES['AXON_VIA']:
                get_node(rst, vias)
            # get phenotypes
            elif rst['Predicate']['value'] in QUERIES.PREDICATES['PHENOTYPE']:
                if rst['Object']['value'].replace('phenotype', 'type') != rst['Neuron_IRI']['value']:
                    phenotypes += [rst['Object']['value']]
            # get references
            elif rst['Predicate']['value'] in QUERIES.PREDICATES['REFERENCE']:
                references += [[rst['Object']['value']]]
            # get taxons
            elif rst['Predicate']['value'] in QUERIES.PREDICATES['TAXON']:
                taxons += [[rst['Object']['value']]]
            # get label
            elif rst['Predicate']['value'] in QUERIES.PREDICATES['LABEL']:
                long_label = rst['Object']['value']
            # get all labels
            if 'Object_Label' in rst and rst['Object']['type']=='uri':
                self.__labels[rst['Object']['value']] = rst['Object_Label']['value']
            if 'Region_Label' in rst and rst['Region']['type']=='uri':
                self.__labels[rst['Region']['value']] = rst['Region_Label']['value']
            if 'Layer_Label' in rst and rst['Layer']['type']=='uri':
                self.__labels[rst['Layer']['value']] = rst['Layer_Label']['value']
        
        # set neuron label
        self.__labels['entity'] = long_label

        # map connectivity
        somas = combine_layer_regions(somas)
        axons = combine_layer_regions(axons)
        dendrites = combine_layer_regions(dendrites)
        vias = combine_layer_regions(vias)
        connectivities = [(soma, axon) for soma in somas for axon in axons]

        return {
            'soma'          : somas,
            'via'           : vias,
            'axons'         : axons,
            'connectivity'  : connectivities,
            'dendrites'     : dendrites,
            'errors'        : [],
            'id'            : entity,
            'label'         : entity,
            'long-label'    : long_label,
            'phenotypes'    : phenotypes,
            'references'    : references,
            'taxon'         : taxons
        }

    
    # def __get_neuron_knowledge(self, entity):
    #     # get connectivities
    #     query = QUERIES.NEURON_CONNECTIVITIES.format(entity=entity)
    #     _, results = self.__select(query)
    #     axons, connectivities = set(), {}
    #     for result in results:
    #         # get axon: (region, axon) if region available; (axon,) if not
    #         if 'B_Region_IRI' in result:
    #             axons.add((NAMESPACES.curie(result['B_Region_IRI']['value']), NAMESPACES.curie(result['B_IRI']['value'])))
    #         else:
    #             axons.add((NAMESPACES.curie(result['B_IRI']['value'],)))
    #         # get connectitity
    #         connect = (NAMESPACES.curie(result['A_IRI']['value']), NAMESPACES.curie(result['B_IRI']['value']))
    #         if connect not in connectivities:
    #             connectivities[connect] = []
    #         if 'C_IRI' in result:
    #             connectivities[connect] += [NAMESPACES.curie(result['C_IRI']['value'])]
    #     # convert connectivities
    #     connectivities= [(a_to_b, tuple(via_c)) for a_to_b, via_c in connectivities.items()]
    #     n_pop = {'axons':list(axons), 'connectivity':connectivities, 
    #              'dendrites':[], 'errors':[], 'id':entity, 'label':entity, 'long-label':'', 
    #              'phenotypes':[], 'references':[], 'taxon':''}

    #     # get metadata
    #     query = QUERIES.NEURON_META.format(entity=entity)
    #     _, results = self.__select(query)
    #     if len(results) > 0:
    #         result = results[0]
    #         if 'Dendrite_Location_IRIs' in result:
    #             n_pop['dendrites'] = [NAMESPACES.curie(dend)for dend in result['Dendrite_Location_IRIs']['value'].split(',')]
    #         n_pop['long-label'] = result['Neuron_Label']['value']
    #         if 'Phenotype_IRIs' in result:
    #             n_pop['phenotypes'] = [NAMESPACES.curie(dend)for dend in result['Phenotype_IRIs']['value'].split(',')]
    #         if 'Reference' in result:
    #             n_pop['references'] = result['Reference']['value']
    #         if 'Species_IRIs' in result:
    #             n_pop['taxon'] = [NAMESPACES.curie(dend)for dend in result['Species_IRIs']['value'].split(',')]

                



    #    return n_pop
        

    def connectivity_models(self):
        return self.__connectivity_models
    
    def entity_knowledge(self, entity):
        entity = NAMESPACES.curie(entity)
        if entity in self.__connectivity_models:
            return self.__get_model_knowledge(entity)
        else:
            return self.__get_neuron_knowledge(entity)
        
    def labels(self):
        return self.__labels
    
    def label(self, entity):
        return self.__labels[entity]
    
    def close(self):
            self.__conn.close()

#===============================================================================
