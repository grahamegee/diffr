from collections import Sequence, Mapping, Set, OrderedDict
from copy import deepcopy
from diffr.data_model import (
    remove, insert, changed, unchanged,
    Diff)


def patch(obj, diff):
    if type(obj) != diff.type:
        raise TypeError(
            'Patch target type ({}) does not match diff type ({})'.format(
                type(obj), diff.type))
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
        raise TypeError(
            'No mechanism for patching objects of type ({})'.format(type(obj)))


def validate_removal(items):
    '''
    Items subject to removal must exist in the target object at the specific
    index.
    '''
    try:
        item, diff_item = items()
    except IndexError:
        raise IndexError(
            'Item subject to removal does not exist in patch target')
    if item != diff_item.item:
        raise ValueError(
            'Expected item for removal {} does not match item in patch target '
            '{}'.format(item, diff_item.item))


def validate_insertion(start, end, patched_obj):
    '''
    Insertions can only happen just before the beginning of the sequence, just
    after the end of the sequence, or somewhere in the middle of the sequence.
    i.e. it must be in bounds.
    '''
    assert(start == end)
    if not (0 <= start <= len(patched_obj)):
        raise IndexError('Item out of range in patch target')


def validate_change(items):
    '''
    Items subject to change must exist in the target object and must be of the
    correct type
    '''
    try:
        item, diff_item = items()
    except IndexError:
        raise IndexError(
            'Item subject for change does not exist in patch target')
    if not type(item) == diff_item.item.type:
        raise TypeError(
            'Item subject for change is the wrong type in patch target')


def object_constructor(obj):
    if type(obj) is str:
        return lambda x: str(x)
    else:
        return lambda x: type(obj)((x,))


def patch_sequence(obj, diff):
    patched = deepcopy(obj)
    offset = 0
    for diff_item in diff:
        start, end, _, _ = diff_item.context
        if diff_item.state is remove:
            validate_removal(lambda: (obj[start], diff_item))
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
            validate_change(lambda: (obj[start], diff_item))
            patched = (
                patched[:start + offset] +
                object_constructor(obj)(patch(obj[start], diff_item.item)) +
                patched[end + offset:])
    return patched


# namedtuple provides you with a class that inherits from Sequence, but you
# could also legitimately treat a namedtuple as a Mapping. My choice has been to
# treat it like a sequence in the context of diff and patch. This might be a
# source of contention. Take for example:
#    Point = namedtuple('Point', ('x', 'y'))
#    a = Point(1,2), b = Point(2,3)
#    you treat Point as a mapping and say:
#        diff(a,b) = d.x = -1, +2
#                    d.y = -2, +3
#    Or treat Point as a Sequence (which is what it actually inherits from):
#        diff(a,b) = -1, 2, +3
#    Treating as a Sequence gives you a minimal edit and in my opinion is the
#    correct way to go considering that Point is a subclass of Sequence.
def patch_named_tuple(obj, diff):
    return type(obj)._make(patch_sequence(tuple(obj), diff))


def try_get_values(values):
    try:
        return values()
    except KeyError as e:
        raise KeyError(
            'Key {} does not exist in patch target'.format(e))


def validate_mapping_removal(values):
    removal_val, original_val = try_get_values(values)
    if removal_val != original_val:
        raise ValueError(
            'Value subject to removal does not match the value in patch target')


def validate_mapping_change(values):
    removal_val, original_val = try_get_values(values)
    if type(original_val) != removal_val.type:
        raise TypeError(
            ('Type of value subject to change does not match '
             'that in patch target')
        )


def patch_mapping(obj, diff):
    # ordered mapping needs a separate function. you can end up moving a
    # key value pair to a different position which may give you an insert
    # followed by a remove, as it stands this would cause patch to actually
    # remove it completely!
    patched = deepcopy(obj)
    for map_item in diff:
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


def validate_ordered_mapping_change(items):
    try:
        item, diff_item = items()
    except IndexError:
        # hide implementation detail. IndexError doesn't make sense for
        # Mappings
        raise ValueError(
            'Item subject to change does not exist in patch target')
    key, value = item
    if key != diff_item.key:
        raise KeyError(
            'Key "{}" does not exist in patch target'.format(diff_item.key))
    if type(value) != diff_item.value.type:
        raise TypeError(
            'Item subject for change should be type {} but is type {} '
            'in patch target'.format(diff_item.value.type, type(value)))


def patch_ordered_mapping(obj, diff):
    # treated pretty much in the same way as a sequence.
    patched_items = list(obj.items())
    offset = 0
    for i, diff_item in enumerate(diff):
        if diff_item.state is remove:
            validate_removal(lambda: (patched_items[i + offset], diff_item))
            patched_items = (
                patched_items[:i + offset] +
                patched_items[i + 1 + offset:]
            )
            offset -= 1
        elif diff_item.state is insert:
            validate_insertion(i + offset, i + offset, patched_items)
            patched_items = (
                patched_items[:i + offset] +
                [diff_item.item] +
                patched_items[i + offset:]
            )
        elif diff_item.state is changed:
            validate_ordered_mapping_change(
                lambda: (patched_items[i + offset], diff_item))
            patched_items = (
                patched_items[:i + offset] +
                [(
                    diff_item.key,
                    patch(patched_items[i + offset][1], diff_item.value)
                )] +
                patched_items[i + 1 + offset:]
            )
    return type(obj)(patched_items)


def patch_set(obj, diff):
    removals = set([di.item for di in diff if di.state is remove])
    if removals.intersection(obj) != removals:
        raise ValueError(
            'Some items subject to removal do not exist in patch target')
    inserts = set([di.item for di in diff if di.state is insert])
    return type(obj)(obj.difference(removals).union(inserts))
