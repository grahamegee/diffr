from collections import Sequence, Mapping, Set, OrderedDict
from copy import deepcopy
from differ.data_model import (
    remove, insert, changed, unchanged,
    Diff)


def patch(obj, diff):
    if type(obj) != diff.type:
        raise TypeError
    elif isinstance(obj, Sequence) and hasattr(obj, '_make'):  # FIXME: ugh :(
        return patch_named_tuple(obj, diff)
    elif isinstance(obj, Sequence):
        return patch_sequence(obj, diff)
    elif isinstance(obj, Set):
        return patch_set(obj, diff)
    elif isinstance(obj, OrderedDict):
        return patch_ordered_mapping(obj, diff)
    elif isinstance(obj, Mapping):
        return patch_mapping(obj, diff)
    else:
        raise TypeError


def validate_removal(item, diff_item):
    '''
    Items subject to removal must exist in the target object at the specific
    index.
    '''
    if item != diff_item.item:
        raise ValueError('Diff not compatible with patch target')


def validate_insertion(start, end, patched_obj):
    '''
    Insertions can only happen just before the beginning of the sequence, just
    after the end of the sequence, or somewhere in the middle of the sequence.
    so basically anywhere then you fucking muppet?!..
    '''
    assert(start == end)
    if not (0 <= start <= len(patched_obj)):
        raise ValueError('Diff not compatible with patch target')


def validate_change(item, diff_item):
    '''
    Items subject to change must exist in the target object and must be of the
    correct type
    '''
    if not(item) or (not type(item) == diff_item.item.type):
        raise ValueError('Diff not compatible with patch target')


def object_constructor(obj):
    if type(obj) is str:
        return lambda x: str(x)
    else:
        return lambda x: type(obj)((x,))


def patch_sequence(obj, diff):
    patched = deepcopy(obj)
    offset = 0
    for diff_item in diff.diffs:
        start, end, _, _ = diff_item.context
        if diff_item.state is remove:
            validate_removal(obj[start], diff_item)
            patched = patched[:start + offset] + patched[end + offset:]
            offset -= 1
        elif diff_item.state is insert:
            validate_insertion(start + offset, end + offset, patched)
            patched = (
                patched[:start + offset] +
                object_constructor(obj)(diff_item.item) +
                patched[end + offset:])
            offset += 1
        elif diff_item.state is changed:
            assert(type(diff_item.item) == Diff)
            validate_change(obj[start], diff_item)
            patched = (
                patched[:start + offset] +
                object_constructor(obj)(patch(obj[start], diff_item.item)) +
                patched[end + offset:])
    return patched


def patch_named_tuple(obj, diff):
    return type(obj)._make(patch_sequence(tuple(obj), diff))


def try_get_values(values):
    try:
        return values()
    except KeyError:
        raise ValueError('Diff not compatible with patch target')


def validate_mapping_removal(values):
    removal_val, original_val = try_get_values(values)
    if removal_val != original_val:
        raise ValueError('Diff not compatible with patch target')


def validate_mapping_change(values):
    removal_val, original_val = try_get_values(values)
    if type(original_val) != removal_val.type:
        raise ValueError('Diff not compatible with patch target')


def patch_mapping(obj, diff):
    # ordered mapping needs a separate function. you can end up moving a
    # key value pair to a different position which may give you an insert
    # followed by a remove, as it stands this would cause patch to actually
    # remove it completely!
    patched = deepcopy(obj)
    for map_item in diff.diffs:
        if map_item.state is remove:
            validate_mapping_removal(
                lambda: (map_item.value, patched[map_item.key]))
            del patched[map_item.key]
        elif map_item.state is insert:
            patched[map_item.key] = map_item.value
        elif map_item.state is changed:
            assert(type(map_item.value) == Diff)
            validate_mapping_change(
                lambda: (map_item.value, patched[map_item.key]))
            patched[map_item.key] = patch(obj[map_item.key], map_item.value)
    return patched


def patch_ordered_mapping(obj, diff):
    patched_items = []
    for map_item in diff.diffs:
        if map_item.state is remove:
            validate_mapping_removal(
                lambda: (map_item.value, obj[map_item.key]))
        elif map_item.state is unchanged:
            patched_items.append((map_item.key, map_item.value))
        elif map_item.state is changed:
            assert(type(map_item.value) == Diff)
            validate_mapping_change(
                lambda: (map_item.value, obj[map_item.key]))
            patched_items.append(
                (map_item.key, patch(obj[map_item.key], map_item.value)))
        else:
            assert(map_item.state is insert)
            patched_items.append((map_item.key, map_item.value))
    return type(obj)(patched_items)


def patch_set(obj, diff):
    removals = set([di.item for di in diff.diffs if di.state is remove])
    if removals.intersection(obj) != removals:
        raise ValueError('Diff not compatible with patch target')
    inserts = set([di.item for di in diff.diffs if di.state is insert])
    return type(obj)(obj.difference(removals).union(inserts))
