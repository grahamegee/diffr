from blessings import Terminal
from collections import Sequence, Mapping, Set, deque, OrderedDict
from copy import deepcopy

term = Terminal()
# FIXME: - what if the users terminal has a white bg?
insert = term.cyan
remove = term.red
unchanged = term.white
changed = term.yellow


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
            for item in self.diffs:
                if item.state is insert:
                    prefix = '+'
                elif item.state is remove:
                    prefix = '-'
                else:
                    prefix = ' '
                output.append(
                    self._indent * self.depth +
                    '{} {}'.format(item.state(prefix), item))
            return '\n'.join(output)

        def __eq__(self, other):
            return (
                self.type == other.type and
                diffs_are_equal(self, other) and
                self.context == other.context and
                self.depth == other.depth)

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
            self.depth == other.depth,
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


class Chunk(list):
    @property
    def states(self):
        return tuple(i.state for i in self)

    def add_diff_item(self, state, item, context):
        self.append(DiffItem(state, item, context))


def _build_lcs_matrix(seq1, seq2):
    '''
    Given two sequences seq1 and seq2:
    Build a matrix of zero's len(seq1) + 1 x len(seq2) + 1 in size which
    provides a numerical map which can be 'backtracked' to  find the largest
    common sub-sequences.

    Matrix build procedure:
        - Leave the first row and collumn as zeros
        - Step through seq1 and seq2:
            -if you find a match:
                Grab the value diagonally backwards from where you are in
                the matrix (left, up) and add 1 to it. (you essentially
                create a representation of the increasing sizes of
                subsequences).
            -else:
                Inspect the values above and to the left of you and pick the
                larger of the two; if they're equal it's an arbitrary
                choice. The subsequence hasn't increased here because there
                is no match, but you want to maintain the size of it so far.

    see https://en.wikipedia.org/wiki/Longest_common_subsequence_problem
    for further details and diagramatic explanations.
    '''
    matrix = [[0 for i in range(len(seq1) + 1)] for i in range(len(seq2) + 1)]
    for i, i_val in enumerate(seq1):
        for j, j_val in enumerate(seq2):
            # matrix indices run from 1 rather than zero to maintain a layer of
            # zero's at the start
            m_i = i + 1
            m_j = j + 1
            if i_val == j_val:
                diagonally_back = matrix[m_j - 1][m_i - 1]
                val = diagonally_back + 1
            else:
                up = matrix[m_j - 1][m_i]
                left = matrix[m_j][m_i - 1]
                val = max(up, left)
            matrix[m_j][m_i] = val
    return matrix


# -----------------------------------------------------------------------------
# When diffing sequences we want to base the diff on the largest common
# subsequence (lcs). However, there is not always such a thing as 'the' lcs;
# there are often several lcs's. 'backtrack' picks only one lcs by design.
# This means that the algorithm is asymmetric w.r.t order ie. diff(seq1, seq2)
# may not be the same as diff(seq2, seq1) when there are several lcs's. This is
# almost unavoidable because if you have several lcs's the choice is arbitrary.
# the referenced wikipedia page provides an algorithm to return the full set of
# lcs's, so we could do some post processing to pick the most central one for
# example, which would make the algorithm symmetric, but for now I can't really
# see the point in adding the extra complication.


def _backtrack(matrix):
    '''
    This generator backtracks through the matrix created by _build_lcs_matrix
    and yields each item of ONE of the possible largest common subsequences
    (LCS) from seq1 and seq2. Each item is a tuple of the form (i, j) It starts
    at the bottom right corner of the matrix and works backwards up to the top
    left.

    This is an interpretation of the algorithm presented on
    https://en.wikipedia.org/wiki/Longest_common_subsequence_problem
    It has been generalised so that it works with lists rather than strings.
    It also uses while loop rather than recursion.
    '''
    j = len(matrix) - 1
    i = len(matrix[0]) - 1
    while i > 0 and j > 0:
        current = matrix[j][i]
        up = matrix[j - 1][i]
        left = matrix[j][i - 1]
        if current == left:
            i -= 1
        elif current == up:
            j -= 1
        else:
            i -= 1
            j -= 1
            yield (i, j)


def find_largest_common_subsequence(seq1, seq2):
    return reversed([i for i in _backtrack(_build_lcs_matrix(seq1, seq2))])


def diff_item_data_factory(from_, to, lcs):
    '''
    This generator yields the parameters required to create DiffItem's for each
    of the items in the input sequences. The indices of all items are compared
    agains the lcs (largest common subsequence) indices to decide whether a
    DiffItem is an insertion, removal or unchanged item.
    '''
    t = f = 0
    for m_f, m_t in lcs:
        while f < m_f:
            yield remove, from_.popleft(), (f, f+1, t, t)
            f += 1
        while t < m_t:
            yield insert, to.popleft(), (f, f, t, t+1)
            t += 1
        # its an arbitrary choice whether to extract the item from from_ or to,
        # but both must be consumed.
        item = from_.popleft()
        to.popleft()
        yield unchanged, item, (f, f+1, t, t+1)
        f += 1
        t += 1
    # clean up any removals or inserts after the last lcs marker.
    while from_:
        yield remove, from_.popleft(), (f, f+1, t, t)
        f += 1
    while to:
        yield insert, to.popleft(), (f, f, t, t+1)
        t += 1


def chunker(diff_item_data_stream):
    '''
    Chunker yields small chunks of the DiffItems; each chunk is terminated with
    an unchanged item if there is one. The final chunk may not be terminated by
    an unchanged item because sequences can diverge after the final item in
    their largest common subsequence. These chunks are used in diff_sequence
    to determine whether or not to carry out a recursive diff.
    '''
    chunk = Chunk()
    for params in diff_item_data_stream:
        state, _, _ = params
        chunk.add_diff_item(*params)
        if state is unchanged:
            yield chunk
            chunk = Chunk()
    yield chunk


def _nested_diff_input(chunk):
    if chunk.states == (remove, insert, unchanged):
        removal, insertion, unchanged_item = chunk
    elif chunk.states == (remove, insert):
        unchanged_item = None
        removal, insertion = chunk
    else:
        removal = insertion = unchanged_item = None
    return removal, insertion, unchanged_item


def diff_sequence(from_, to, context_limit=3, depth=0):
    '''
    Return a Diff object of two sequence types. If the sequences are the same
    length a recursive call may be attempted to find diffs in nested
    structures. If they are different lengths only a top-layer diff is
    provided because it is not clear how to pair up the items between the
    sequences for a deeper comparison.

    :parameter from_: first sequence
    :parameter to: second sequence
    :parameter context_limit: Controls how many unchanged items can be part of a
        block of change (a Diff.ContextBlock). Default is 3.
    :private parameter _depth: Keeps track of level of nesting during
        recursive calls, DO NOT USE.

    A generator pipeline consisting of diff_item_data_factory followed by
    chunker is used to provide chunks (small subsets of the diff) to work on.
    nested diffing is only worth bothering with when a chunk contains a single
    insert paired with a single remove (and optionally and unchaged item).
    '''
    chunks = chunker(
        diff_item_data_factory(
            deque(from_), deque(to),
            find_largest_common_subsequence(from_, to)
        )
    )
    nested_information_wanted = (
        len(from_) == len(to) and not isinstance(from_, str))
    diffs = []
    for chunk in chunks:
        nesting = False
        if nested_information_wanted:
            removal, insertion, unchanged_item = _nested_diff_input(chunk)
            if removal and insertion:
                try:
                    item = diff(
                        removal.item, insertion.item, context_limit, depth + 1)
                except TypeError:
                    nesting = False
                else:
                    nesting = True
        if nesting:
            f_s, f_e, _, _ = removal.context
            _, _, t_s, t_e = insertion.context
            diffs += [DiffItem(changed, item, (f_s, f_e, t_s, t_e))]
            if unchanged_item:
                diffs += [unchanged_item]
        else:
            diffs += chunk
    seq_diff = Diff(type(from_), diffs, context_limit, depth)
    seq_diff.create_context_blocks()
    return seq_diff


def diff_set(from_, to, context_limit=3, _depth=0):
    '''
    Return a Diff object of two sets.

    :parameter from_: first set
    :paramter to: second set
    :parameter context_limit: Controls how many unchanged items can be part of a
        block of change (a Diff.ContextBlock). Default is 3.
    :private parameter _depth: Keeps track of level of nesting during
    recursive calls, DO NOT USE.
    '''
    insertions = [DiffItem(insert, i) for i in to.difference(from_)]
    removals = [DiffItem(remove, i) for i in from_.difference(to)]
    unchanged_items = [DiffItem(unchanged, i) for i in from_.intersection(to)]
    diffs = removals + unchanged_items + insertions
    set_diff = Diff(type(from_), diffs, context_limit, _depth)
    set_diff.create_context_blocks()
    return set_diff


def diff_mapping(from_, to, context_limit=3, _depth=0):
    '''
    Return a Diff object of two mapping types. If the two mapping types
    contain items that have the same key with differen't values a recursive
    call will be attempted to find differences in the values (if they are
    collections).

    :parameter from_: first mapping type
    :parameter to_: second mapping type
    :parameter context_limit: Controls how many unchanged items can be part of a
        block of change (a Diff.ContextBlock). Default is 3.
    :private parameter _depth: Keeps track of level of nesting during
    recursive calls, DO NOT USE.'''
    removals = [
        MappingDiffItem(remove, k, remove, val)
        for k, val in from_.items() if k not in to.keys()
    ]
    insertions = [
        MappingDiffItem(insert, k, insert, val)
        for k, val in to.items() if k not in from_.keys()
    ]
    common_keys = [k for k in from_.keys() if k in to.keys()]
    other = []
    for k in common_keys:
        if from_[k] == to[k]:
            other.append(MappingDiffItem(unchanged, k, unchanged, from_[k]))
        else:
            try:
                val = diff(from_[k], to[k], context_limit, _depth + 1)
            except TypeError:
                other.append(MappingDiffItem(unchanged, k, remove, from_[k]))
                other.append(MappingDiffItem(unchanged, k, insert, to[k]))
            else:
                other.append(MappingDiffItem(unchanged, k, changed, val))
    diffs = removals + other + insertions
    dict_diff = Diff(type(from_), diffs, context_limit, _depth)
    dict_diff.create_context_blocks()
    return dict_diff


def diff_ordered_mapping(from_, to, context_limit=3, _depth=0):
    key_diff_pipeline = diff_item_data_factory(
        deque(from_.keys()), deque(to.keys()),
        find_largest_common_subsequence(from_.keys(), to.keys())
    )
    diffs = []
    for state, key, _ in key_diff_pipeline:
        if state is remove:
            diffs += [MappingDiffItem(remove, key, remove, from_[key])]
        elif state is insert:
            diffs += [MappingDiffItem(insert, key, insert, to[key])]
        else:
            assert(state is unchanged)
            if from_[key] == to[key]:
                diffs += [
                    MappingDiffItem(unchanged, key, unchanged, from_[key])
                ]
            else:
                try:
                    val = diff(from_[key], to[key], context_limit, _depth + 1)
                except TypeError:
                    diffs += [
                        MappingDiffItem(unchanged, key, remove, from_[key])
                    ]
                    diffs += [
                        MappingDiffItem(unchanged, key, insert, to[key])
                    ]
                else:
                    diffs += [
                        MappingDiffItem(unchanged, key, changed, val)
                    ]
    dict_diff = Diff(type(from_), diffs, context_limit, _depth)
    dict_diff.create_context_blocks()
    return dict_diff


def diff(from_, to, context_limit=3, _depth=0):
    '''
    Return a Diff object of two collections. Recursive calls may be
    attempted if it is sensible to do so to provide more detailed diffs of
    nested structures.

    :parameter from_: first collection
    :parameter to: second collection
    :parameter context_limit: Controls how many unchanged items can be part of a
        block of change (a Diff.ContextBlock). Default is 3.
    :private parameter _depth: Keeps track of level of nesting during
    recursive calls, DO NOT USE.'''
    if type(from_) != type(to):
        raise TypeError(
            'diff params are different types {} != {}'.format(
                type(from_), type(to)))
    elif isinstance(from_, Sequence):
        return diff_sequence(from_, to, context_limit, _depth)
    elif isinstance(from_, Set):
        return diff_set(from_, to, context_limit, _depth)
    elif isinstance(from_, OrderedDict):
        return diff_ordered_mapping(from_, to, context_limit, _depth)
    elif isinstance(from_, Mapping):
        return diff_mapping(from_, to, context_limit, _depth)
    else:
        raise TypeError(
            'No mechanism for diffing objects of type {}'.format(
                type(from_)))


def patch(obj, diff):
    if type(obj) != diff.type:
        raise TypeError
    elif isinstance(obj, Sequence):
        return patch_sequence(obj, diff)
    elif isinstance(obj, Set):
        return patch_set(obj, diff)
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
                type(obj)(diff_item.item) +
                patched[end + offset:])
            offset += 1
        elif diff_item.state is changed:
            assert(type(diff_item.item) == Diff)
            validate_change(obj[start], diff_item)
            patched = (
                patched[:start + offset] +
                type(obj)([patch(obj[start], diff_item.item)]) +
                patched[end + offset:])
    return patched


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


def patch_set(obj, diff):
    removals = set([di.item for di in diff.diffs if di.state is remove])
    if removals.intersection(obj) != removals:
        raise ValueError('Diff not compatible with patch target')
    inserts = set([di.item for di in diff.diffs if di.state is insert])
    return type(obj)(obj.difference(removals).union(inserts))
