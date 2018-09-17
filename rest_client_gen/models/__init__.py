from typing import Dict, Generic, Iterable, List, Set, TypeVar

from ..dynamic_typing import ModelMeta, ModelPtr

Index = str
T = TypeVar('T')


class ListEx(list, Generic[T]):
    """
    Extended list with shortcut methods
    """

    def safe_index(self, value: T):
        try:
            return self.index(value)
        except ValueError:
            return None

    def _safe_indexes(self, *values: T):
        return [i for i in map(self.safe_index, values) if i is not None]

    def insert_before(self, value: T, *before: T):
        ix = self._safe_indexes(*before)
        if not ix:
            raise ValueError
        pos = min(ix)
        self.insert(pos, value)

    def insert_after(self, value: T, *after: T):
        ix = self._safe_indexes(*after)
        if not ix:
            raise ValueError
        pos = max(ix)
        self.insert(pos + 1, value)


def filter_pointers(model: ModelMeta) -> Iterable[ModelPtr]:
    """
    Return iterator over pointers with not None parent
    """
    return (ptr for ptr in model.pointers if ptr.parent)


def extract_root(model: ModelMeta) -> Set[Index]:
    """
    Return set of indexes of root models that are use given ``model`` directly or through another nested model.
    """
    seen: Set[Index] = set()
    nodes: List[ModelPtr] = list(filter_pointers(model))
    roots: Set[Index] = set()
    while nodes:
        node = nodes.pop()
        seen.add(node.type.index)
        filtered = list(filter_pointers(node.parent))
        nodes.extend(ptr for ptr in filtered if ptr.type.index not in seen)
        if not filtered:
            roots.add(node.parent.index)
    return roots


def compose_models(models_map: Dict[str, ModelMeta]):
    root_models = ListEx()
    root_nested_ix = 0
    structure_hash_table: Dict[Index, dict] = {
        key: {
            "model": model,
            "nested": ListEx(),
            "roots": list(extract_root(model))
        } for key, model in models_map.items()
    }

    for key, model in models_map.items():
        pointers = list(filter_pointers(model))
        if len(pointers) == 0:
            # Root level model
            root_models.append(structure_hash_table[key])
        else:
            parents = {ptr.parent.index for ptr in pointers}
            if len(parents) > 1:
                # Model is using by other models
                struct = structure_hash_table[key]
                if len(struct["roots"]) > 1:
                    # Model is using by different root models
                    try:
                        root_models.insert_before(
                            struct,
                            *(structure_hash_table[parent_key] for parent_key in struct["roots"])
                        )
                    except ValueError:
                        root_models.insert(root_nested_ix, struct)
                        root_nested_ix += 1
                else:
                    # Model is using by single root model
                    parent = structure_hash_table[struct["roots"][0]]
                    parent["nested"].insert(0, struct)
            else:
                # Model is using by only one model
                parent = structure_hash_table[next(iter(parents))]
                struct = structure_hash_table[key]
                parent["nested"].append(struct)

    return root_models