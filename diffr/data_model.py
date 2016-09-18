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


class _Window(object):
    def __init__(self, number, context_limit):
        left_reach = number - context_limit
        self.number = number
        self.left = left_reach if left_reach > 0 else 0
        self.right = number + context_limit + 1

    def __repr__(self):
        return '{}(number={}, left={}, right={})'.format(
            self.__class__.__name__, self.number, self.left, self.right)


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


def _indices_of_changed_items(diff_list, context_limit):
    '''
    return the indexes of the insert|remove|changed DiffItems only. If a
    DiffItem is wrapping a Diff instance call it's context slicer to
    propogate formatting down the nested structure
    '''
    return [
        _Window(i, context_limit) for i, diff_item in enumerate(diff_list)
        if diff_item.state != unchanged]


def _get_context_slice_indices(diff_list, context_limit):
    '''
    From the indices of changed items determine and create non-overlapping
    context slices of the Diff.
    '''
    changed_indices = _indices_of_changed_items(diff_list, context_limit)
    previous = changed_indices[0]
    slices = []
    s = [previous]
    for current in changed_indices[1:]:
        if previous.right >= current.left:
            s.append(current)
            previous = current
        else:
            slices.append(s)
            previous = current
            s = [previous]
    if not slices or slices[-1] != s:
        slices.append(s)
    return [(i[0].left, i[-1].right) for i in slices]


def context_slice(diff_list, context_limit):
    return [
        diff_list[start:end] for start, end in
        _get_context_slice_indices(diff_list, context_limit)]


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
        self.context_limit = context_limit
        self.depth = depth
        self._indent = '   ' * depth
        self.start = unchanged('{}('.format(self.type))
        self.end = unchanged(')')

    def _extract_context(self, context_block):
        if hasattr(context_block[0], 'context') and context_block[0].context:
            from_start, _, to_start, _ = context_block[0].context
            _, from_end, _, to_end = context_block[-1].context
            return (from_start, from_end, to_start, to_end)

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
            self.context_limit == other.context_limit)
        return all(eq)

    def __ne__(self, other):
        return not self == other

    def __format__(self, fmt_spec=''):
        if fmt_spec.endswith('c'):
            context_limit = int(fmt_spec[:-1])
            slices = [s for s in context_slice(self, context_limit)]
            return '\n'.join(str(s) for s in slices)
        else:
            return str(self)

    def _make_context_banner(self, context_block):
        context = self._extract_context(context_block)
        if context:
            f_s, f_e, t_s, t_e = map(str, context)
            return self._indent + '@@ {}{},{} {}{},{} @@'.format(
                    remove('-'), remove(f_s), remove(f_e),
                    insert('+'), insert(t_s), insert(t_e))

    def __str__(self):
        # display a context banner at the top if we have context, ie we are
        # diffing sequences.
        output = [self.start]
        if self.context_limit is not None:
            items_to_display = context_slice(self.diffs, self.context_limit)
        else:
            items_to_display = [self.diffs]

        for context_block in items_to_display:
            banner = self._make_context_banner(context_block)
            if banner:
                output.append(banner)
            if self.type is str:
                self._make_string_diff_output(output, context_block)
            else:
                self._make_diff_output(output, context_block)

        output.append(self._indent + self.end)
        return '\n'.join(output)

    def _make_string_diff_output(self, output, context_block):
        diff_output = []
        line_start = self._indent + ' '
        states = items = line_start
        for i, item in enumerate(context_block):
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

    def _make_diff_output(self, output, context_block):
        for item in context_block:
            prefix = state_to_prefix(item.state)
            output.append(
                self._indent + '{} {}'.format(item.state(prefix), item))
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
