# npo_explorer

This is a similar code to [mapknowledge](https://github.com/AnatomicMaps/map-knowledge/tree/main) but the source is NPO [stardog](https://cloud.stardog.com/) and [repository](https://github.com/SciCrunch/NIF-Ontology/tree/neurons). The source is NPO from Stardog.

This package requires the following variables:

- NPO_USERNAME
- NPO_PASSWORD

The requirements:

* python = ">=3.10,<4.0"
* pystardog = "^0.16.1"
* rdflib = "^6.3.2"

How to use:

```
from npoexplorer import NPOExplorer

store = NPOExplorer()
store.entity_knowledge('https://apinatomy.org/uris/models/keast-bladder')
```

Some neuron connectivities return self loop. The default `NPOExplorer` will remove this loop. To allow loop, set `allow_loop` to `True`:

```
store = NPOExplorer(allow_loop=True)
```

Other than that is just the same as [mapknowledge](https://github.com/AnatomicMaps/map-knowledge/tree/main).
