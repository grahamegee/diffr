from blessings import Terminal
from collections import Sequence, OrderedDict
from numbers import Integral


term = Terminal()
# FIXME: - what if the users terminal has a white bg? It would be nice to work
# out what color the users terminal is at import time and choose a sensible
# color scheme.
insert = term.green
remove = term.red
unchanged = lambda string: term.normal + string
changed = term.yellow


def state_to_prefix(state):
    if state is insert:
        prefix = '+'
    elif state is remove:
        prefix = '-'
    else:
        prefix = ' '
    return prefix


def is_ordered(collection):
    return any((issubclass(collection, c) for c in (Sequence, OrderedDict)))


def sequences_contain_same_items(a, b):
    for item in a:
        try:
            i = b.index(item)
        except ValueError:
            return False
        b = b[:i] + b[i+1:]
    return not b


def diffs_are_equal(diff_a, diff_b):
    # somone is bound to try and use this library with an implementation of
    # ordered set, I can only deal with the ones I know about.
    if is_ordered(diff_a.type):
        return diff_a.diffs == diff_b.diffs
    else:
        return sequences_contain_same_items(diff_a.diffs, diff_b.diffs)


class Diff(object):
    '''
    A collection of DiffItems.
    It can also can be wrapped in a DiffItem as an item of a higher level Diff
    ie the objects being diffed are nested.

    :attribute type: The type of the objects being diffed
    :attribute diffs: A list containing all of the DiffItems including an
        unchanged ones.
    :attribute context_blocks: A list containing slices of the diffs list which
        have changes. Each slice is contained in a ContextBlock object.
    :attribute context_limit: Determines how many unchanged items can be
        included within a context block.
    :attribute depth: Indicates how deep this diff is in a nested diff.

    Diffs are uniquely identified by the values of their attributes.

    :method create_context_blocks: Should be used after the Diff is fully
        populated; running this method completes the diff making it usable
        programmatically as well as making it display correctly.
    '''
    def __init__(self, obj_type, diffs, context_limit=3, depth=0):
        self.type = obj_type
        self.diffs = tuple(diffs)
        self.context_blocks = []
        self.context_limit = context_limit
        self.depth = depth
        self._indent = '   '
        self.start = unchanged('{}('.format(self.type))
        self.end = unchanged(')')

    @property
    def context(self):
        if hasattr(self.diffs[0], 'context') and self.diffs[0].context:
            from_start, _, to_start, _ = self.diffs[0].context
            _, from_end, _, to_end = self.diffs[-1].context
            return (from_start, from_end, to_start, to_end)
        return ()

    def _indices_of_changed_items(self, context_limit):
        '''
        return the indexes of the insert|remove|changed DiffItems only. If a
        DiffItem is wrapping a Diff instance call it's context slicer to
        propogate formatting down the nested structure
        '''
        indexes = []
        for i, diff_item in self.diffs:
            if diff_item.state != unchanged:
                indexes.append(i)
                if isinstance(diff_item.item, Diff):
                    diff_item.item._create_context_slice_indices(context_limit)
        return indexes

    def _create_context_slice_indices(self, context_limit):
        changed_indices = self._indices_of_changed_items(context_limit)
        previous = changed_indices
        s = [previous, previous]
        slices = []
        for current in changed_indices[1:]:
            if (previous + context_limit) >= (current - context_limit):
                s[1] = current
            else:
                slices.append(s)
                previous = current
                s = [previous, previous]
        slices.append(s)
        return slices

    def __len__(self):
        return len(self.diffs)

    def __bool__(self):
        if self.diffs:
            return any(d.state != unchanged for d in self.diffs)
        return False

    def __nonzero__(self):
        # python 2.7
        return self.__bool__()

    def __iter__(self):
        return iter(self.diffs)

    def __getitem__(self, index):
        cls = type(self)
        if isinstance(index, slice):
            return cls(
                self.type, self.diffs[index], self.context_limit, self.depth)
        elif isinstance(index, Integral):
            return self.diffs[index]
        else:
            msg = '{.__name__} indices must be integers'
            raise TypeError(msg.format(cls))

    def __eq__(self, other):
        eq = (
            self.type == other.type,
            diffs_are_equal(self, other),
            self.context_blocks == other.context_blocks,
            self.context_limit == other.context_limit)
        context_blocks = 2
        if is_ordered(self.type):
            return all(eq)
        else:
            return all(eq[:context_blocks] + eq[context_blocks + 1:])

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        # display a context banner at the top if we have context, ie we are
        # diffing sequences.
        output = []
        if self.context:
            f_s, f_e, t_s, t_e = map(str, self.context)
            output.append(
                self._indent * self.depth + '@@ {}{},{} {}{},{} @@'.format(
                    remove('-'), remove(f_s), remove(f_e),
                    insert('+'), insert(t_s), insert(t_e)))
        if self.type is str:
            return '\n'.join(self._make_string_diff_output(output))
        else:
            return '\n'.join(self._make_diff_output(output))

    def _make_string_diff_output(self, output):
        diff_output = []
        line_start = self._indent * self.depth + ' '
        states = items = line_start
        for i, item in enumerate(self.diffs):
            states += item.state(state_to_prefix(item.state))
            items += str(item)
            if (len(line_start) + i) % (term.width - 1):
                line_in_progress = True
            else:
                diff_output.extend([states, items])
                states = items = line_start
                line_in_progress = False
        if line_in_progress:
            diff_output.extend([states, items])
        output.extend(diff_output)
        return output

    def _make_diff_output(self, output):
        for item in self.diffs:
            prefix = state_to_prefix(item.state)
            output.append(
                self._indent * self.depth +
                '{} {}'.format(item.state(prefix), item))
        return output


class DiffItem(object):
    '''
    A light-weight wrapper around non-collection python objects for use in
    diffing.

    :attribute state: choice of remove|insert|unchanged|changed.
    :attribute item: The original unwrapped object.
    :attribute context: Only populated for sequences; a tuple of the form:
        (f_start, f_end, t_start, t_end) where f_start:f_end is the slice of the
        first object in the diff and t_start:t_end is the slice of the second
        object in the diff that this DiffItem contains. context is used to
        populate Diff.ContextBlock.context it is a more useful concept in the
        context of Diff.context_blocks than on a per DiffItem bases.
    '''
    def __init__(self, state, item, context=None):
        self.state = state
        self.item = item
        self.context = context

    def __str__(self):
        return self.state('{!s}'.format(self.item))

    def __eq__(self, other):
        return (
            self.state == other.state and
            self.item == other.item and
            self.context == other.context)

    def __ne__(self, other):
        return not self == other


class MappingDiffItem(DiffItem):
    '''
    A special case of DiffItem because they have keys and values which may be in
    different states independently.

    :attribute key_state: Choice of remove|insert|unchanged|changed.
    :attribute key: The key from the original unwrapped item.
    :attribute state: Value state; choice of remove|insert|unchanged|changed.
    :attribute value: The value from the original unwrapped item.
    '''
    def __init__(self, key_state, key, value_state, value):
        self.key_state = key_state
        self.key = key
        self.state = value_state
        self.value = value
        self.item = (key, value)

    def __str__(self):
        key_repr = '{!s}: '.format(self.key)
        val_repr = '{!s}'.format(self.value)
        return self.key_state(key_repr) + self.state(val_repr)

    def __eq__(self, other):
        return (
            self.key_state == other.key_state and
            self.key == other.key and
            self.state == other.state and
            self.value == other.value)

    def __ne__(self, other):
        return not self == other
