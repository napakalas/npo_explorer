from pprint import pprint
from npoexplorer import NPOExplorer

KEAST_MODEL = 'https://apinatomy.org/uris/models/keast-bladder'

def KEAST_NEURON(n):
    return f'ilxtr:neuron-type-keast-{n}'

def print_knowledge(store, entity):
    print(f'{entity}:')
    pprint(store.entity_knowledge(entity))
    print()

def print_phenotypes(store, entity):
    print("Querying", entity)
    knowledge = store.entity_knowledge(entity)
    print(f'{entity}: {knowledge.get("phenotypes", [])}')

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    print('Production:')
    store = NPOExplorer()
    print_knowledge(store, KEAST_MODEL)
    print_knowledge(store, KEAST_NEURON(9))
    store.close()

if __name__ == '__main__':
    explorer = NPOExplorer()
