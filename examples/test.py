from pprint import pprint
from npoexplorer import NPOExplorer

if __name__ == '__main__':
    explorer = NPOExplorer()
    # pprint(explorer.connectivity_models())
    # pprint(explorer.entity_knowledge('ilxtr:NeuronSparcNlp'))
    # pprint(explorer.entity_knowledge('ilxtr:neuron-type-bromo-6'))
    pprint(explorer.entity_knowledge('ilxtr:neuron-type-aacar-11'))
    # pprint(explorer.entity_knowledge('ilxtr:neuron-type-pancr-4'))
    # pprint(explorer.label('ILX:0793667'))