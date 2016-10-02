from collections import Sequence, Mapping, Set, deque, OrderedDict
from diffr.data_model import(
    insert, remove, unchanged, changed,
    Diff, DiffItem, MappingDiffItem)


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


def diff_sequence(from_, to, depth=0):
    '''
    Return a Diff object of two sequence types. If the sequences are the same
    length a recursive call may be attempted to find diffs in nested
    structures. If they are different lengths only a top-layer diff is
    provided because it is not clear how to pair up the items between the
    sequences for a deeper comparison.

    :parameter from_: first sequence
    :parameter to: second sequence
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
                    item = diff(removal.item, insertion.item, depth + 1)
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
    seq_diff = Diff(type(from_), diffs, depth)
    return seq_diff


def diff_set(from_, to, _depth=0):
    '''
    Return a Diff object of two sets.

    :parameter from_: first set
    :paramter to: second set
    :private parameter _depth: Keeps track of level of nesting during
    recursive calls, DO NOT USE.
    '''
    insertions = [DiffItem(insert, i) for i in to.difference(from_)]
    removals = [DiffItem(remove, i) for i in from_.difference(to)]
    unchanged_items = [DiffItem(unchanged, i) for i in from_.intersection(to)]
    diffs = removals + unchanged_items + insertions
    set_diff = Diff(type(from_), diffs, _depth)
    return set_diff


def diff_mapping(from_, to, _depth=0):
    '''
    Return a Diff object of two mapping types. If the two mapping types
    contain items that have the same key with differen't values a recursive
    call will be attempted to find differences in the values (if they are
    collections).

    :parameter from_: first mapping type
    :parameter to_: second mapping type
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
                val = diff(from_[k], to[k], _depth + 1)
            except TypeError:
                other.append(MappingDiffItem(unchanged, k, remove, from_[k]))
                other.append(MappingDiffItem(unchanged, k, insert, to[k]))
            else:
                other.append(MappingDiffItem(unchanged, k, changed, val))
    diffs = removals + other + insertions
    dict_diff = Diff(type(from_), diffs, _depth)
    return dict_diff


def diff_ordered_mapping(from_, to, _depth=0):
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
                    val = diff(from_[key], to[key], _depth + 1)
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
    dict_diff = Diff(type(from_), diffs, _depth)
    return dict_diff


def diff(from_, to, _depth=0):
    '''
    Return a Diff object of two collections. Recursive calls may be
    attempted if it is sensible to do so to provide more detailed diffs of
    nested structures.

    :parameter from_: first collection
    :parameter to: second collection
    :private parameter _depth: Keeps track of level of nesting during
    recursive calls, DO NOT USE.'''
    if type(from_) != type(to):
        raise TypeError(
            'diff params are different types {} != {}'.format(
                type(from_), type(to)))
    elif isinstance(from_, Sequence):
        return diff_sequence(from_, to, _depth)
    elif isinstance(from_, Set):
        return diff_set(from_, to, _depth)
    elif isinstance(from_, OrderedDict):
        return diff_ordered_mapping(from_, to, _depth)
    elif isinstance(from_, Mapping):
        return diff_mapping(from_, to, _depth)
    else:
        raise TypeError(
            'No mechanism for diffing objects of type {}'.format(
                type(from_)))
