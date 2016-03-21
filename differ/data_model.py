from blessings import Terminal
from collections import Sequence, OrderedDict


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

    class ContextBlock(object):
        '''
        Sub-collection of Diff items.

        :attribute diffs: The list of DiffItems which are a part of this
            context.
        :attribute context: Only populated for sequences; a tuple of the form:
            (f_start, f_end, t_start, t_end) where f_start:f_end is the slice
            of the first object in the diff and t_start:t_end is the slice of
            the second object in the diff that this ContextBlock contains.
        :attribute depth: Depth of this context block in a nested diff.

        ContextBlocks are uniquely identified by these attributes.
        '''
        def __init__(self, obj_type, diffs, depth=0):
            self.type = obj_type
            self.diffs = diffs
            self._indent = ' '*3
            self.depth = depth
            self.context = ()
            if hasattr(self.diffs[0], 'context') and self.diffs[0].context:
                from_start, _, to_start, _ = self.diffs[0].context
                _, from_end, _, to_end = self.diffs[-1].context
                self.context = (from_start, from_end, to_start, to_end)

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

        def __eq__(self, other):
            return (
                self.type == other.type and
                diffs_are_equal(self, other) and
                self.context == other.context)

        def __ne__(self, other):
            return not self == other

    def __init__(self, obj_type, diffs, context_limit=3, depth=0):
        self.type = obj_type
        self.diffs = diffs
        self.context_blocks = []
        self.context_limit = context_limit
        self.depth = depth
        self.indent = '   '
        self.start = unchanged('{}('.format(self.type))
        self.end = unchanged(')')
        self.create_context_blocks()

    def _create_context_markers(self):
        # FIXME: I suspect this can be simplified, but spent a good day getting
        # nowhere trying... Also it is breaking MappingDiffItems up into context
        # blocks which doesn't make much sense as they should not really be part
        # of a sequence (same for sets). However a context banner is not
        # displayed in these cases and I think the output is still useful and
        # not too confusing.
        context_markers = []
        context_started = False
        context_started_at = None
        gap_between_change = 0
        i = 0
        for diff in self.diffs:
            if diff.state is unchanged:
                if context_started:
                    if gap_between_change == self.context_limit:
                        context_markers.append(
                            (context_started_at, i-self.context_limit))
                        context_started = False
                        gap_between_change = 0
                    else:
                        gap_between_change += 1
            # insert, removal or changed
            else:
                if context_started:
                    gap_between_change = 0
                else:
                    context_started_at = i
                    context_started = True
            i += 1
        # clean up the end if necessary
        if context_started:
            context_markers.append((context_started_at, i - gap_between_change))
        return context_markers

    def create_context_blocks(self):
        self.context_blocks = [
            self.ContextBlock(self.type, self.diffs[start:end], self.depth)
            for start, end in self._create_context_markers()]

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
        output = [self.start] + [
            '{!s}'.format(cb) for cb in self.context_blocks] + [
                self.indent * self.depth + self.end]
        return '\n'.join(output)


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
