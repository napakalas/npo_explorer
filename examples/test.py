from pprint import pprint

from npoexplorer import NPOExplorer

if __name__ == "__main__":
    explorer = NPOExplorer()
    pprint(explorer.connectivity_models())
    pprint(explorer.entity_knowledge("ilxtr:NeuronKblad"))
    pprint(explorer.entity_knowledge("https://apinatomy.org/uris/models/keast-bladder"))
    pprint(explorer.entity_knowledge("ilxtr:neuron-type-keast-10"))
    pprint(explorer.entity_knowledge("mmset1:12"))
    pprint(explorer.entity_knowledge("ilxtr:neuron-type-aacar-13"))
    explorer.close()
