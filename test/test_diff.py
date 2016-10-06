import unittest
from collections import OrderedDict, namedtuple, deque
from diffr.data_model import Diff, DiffItem, MappingDiffItem
from diffr.patch import patch
from diffr.diff import (
    _backtrack, _build_lcs_matrix,
    Chunk, chunker, diff_item_data_factory,
    insert, remove, changed, unchanged,
    diff, diff_sequence, diff_mapping, diff_set, diff_ordered_mapping)


class ChunkTests(unittest.TestCase):
    def test_diff_block_states_attribute(self):
        chunk = Chunk([
            DiffItem(unchanged, 1),
            DiffItem(remove, 1),
            DiffItem(insert, 1)
        ])
        self.assertEqual(
            chunk.states,
            (unchanged, remove, insert))


class BacktrackTests(unittest.TestCase):
    def test_lcs_is_contiguous(self):
        seq1 = '-abc-'
        seq2 = '.abc.'
        expected_lcs = [(1, 1), (2, 2), (3, 3)]
        lcs_gen = _backtrack(_build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_lcs_is_not_contiguous(self):
        seq1 = '-a-b-c-'
        seq2 = '.a.b.c.'
        expected_lcs = [(1, 1), (3, 3), (5, 5)]
        lcs_gen = _backtrack(_build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_lcs_is_not_aligned(self):
        seq1 = '---a-bc'
        seq2 = 'ab.c..'
        expected_lcs = [(3, 0), (5, 1), (6, 3)]
        lcs_gen = _backtrack(_build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_more_than_one_possible_lcs(self):
        '''When there is a choice only one value should be returned'''
        # IMPORTANT if we swap in a different lcs function this test may have
        # to change because it may choose a different one.
        seq1 = 'aabb'
        seq2 = 'bbaa'
        expected_lcs = [(0, 2), (1, 3)]
        lcs_gen = _backtrack(_build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_no_lcs(self):
        seq1 = 'abc'
        seq2 = 'xyz'
        expected_lcs = []
        lcs_gen = _backtrack(_build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])


class ChunkerTests(unittest.TestCase):
    def test_empty_diff_block(self):
        chunks = chunker(
            diff_item_data_factory(deque([]), deque([]), ())
        )
        self.assertEqual(next(chunks), Chunk())

    def test_only_inserts(self):
        q1 = deque([])
        q2 = deque([1, 2])
        lcs_marker = ()
        expected_diff_block = Chunk([
            DiffItem(insert, 1, (0, 0, 0, 1)),
            DiffItem(insert, 2, (0, 0, 1, 2))
        ])
        chunks = chunker(
            diff_item_data_factory(q1, q2, lcs_marker)
        )
        self.assertEqual(next(chunks), expected_diff_block)

    def test_only_removals(self):
        q1 = deque([1, 2])
        q2 = deque([])
        lcs_marker = ()
        expected_diff_block = Chunk([
            DiffItem(remove, 1, (0, 1, 0, 0)),
            DiffItem(remove, 2, (1, 2, 0, 0))
        ])
        chunks = chunker(
            diff_item_data_factory(q1, q2, lcs_marker)
        )
        self.assertEqual(next(chunks), expected_diff_block)

    def test_only_unchanged(self):
        q1 = deque([1, 2])
        q2 = deque([1, 2])
        lcs_markers = ((0, 0), (1, 1))
        chunk_1 = Chunk([
            DiffItem(unchanged, 1, (0, 1, 0, 1))
        ])
        chunk_2 = Chunk([
            DiffItem(unchanged, 2, (1, 2, 1, 2))
        ])
        chunks = chunker(
            diff_item_data_factory(q1, q2, lcs_markers)
        )
        self.assertEqual(next(chunks), chunk_1)
        self.assertEqual(next(chunks), chunk_2)

    def test_some_changes_after_an_unchanged_item(self):
        q1 = deque([0, 1, 2])
        q2 = deque([0, 3, 4])
        lcs_marker = ((0, 0),)
        chunk_1 = Chunk([
            DiffItem(unchanged, 0, (0, 1, 0, 1))
        ])
        chunk_2 = Chunk([
            DiffItem(remove, 1, (1, 2, 1, 1)),
            DiffItem(remove, 2, (2, 3, 1, 1)),
            DiffItem(insert, 3, (3, 3, 1, 2)),
            DiffItem(insert, 4, (3, 3, 2, 3))
        ])
        chunks = chunker(
            diff_item_data_factory(q1, q2, lcs_marker)
        )
        self.assertEqual(next(chunks), chunk_1)
        self.assertEqual(next(chunks), chunk_2)

    def test_changes_before_the_first_unchanged_item(self):
        q1 = deque([1, 4])
        q2 = deque([2, 4])
        lcs_markers = ((1, 1),)
        chunk = Chunk([
            DiffItem(remove, 1, (0, 1, 0, 0)),
            DiffItem(insert, 2, (1, 1, 0, 1)),
            DiffItem(unchanged, 4, (1, 2, 1, 2))
        ])
        chunks = chunker(
            diff_item_data_factory(q1, q2, lcs_markers)
        )
        self.assertEqual(next(chunks), chunk)


class DiffSequenceTest(unittest.TestCase):
    def test_empty_diff(self):
        seq = []
        diff_obj = diff_sequence(seq, seq)
        expected_diff = Diff(list, seq)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq, diff_obj), seq)

    def test_no_differences(self):
        seq = [1, 2]
        diff_obj = diff_sequence(seq, seq)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(unchanged, 2, (1, 2, 1, 2))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq, diff_obj), seq)

    # --------------------------------------------------------------------------
    # This block of tests is a bit vague, but is designed to give us confidence
    # that the returned diff generally looks right.
    # --------------------------------------------------------------------------
    def test_mainly_removals(self):
        seq1 = 'hello'
        seq2 = 'hi'
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 'h', (0, 1, 0, 1)),
            DiffItem(remove, 'e', (1, 2, 1, 1)),
            DiffItem(remove, 'l', (2, 3, 1, 1)),
            DiffItem(remove, 'l', (3, 4, 1, 1)),
            DiffItem(remove, 'o', (4, 5, 1, 1)),
            DiffItem(insert, 'i', (5, 5, 1, 2))]
        expected_diff = Diff(str, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_mainly_unchanged(self):
        seq1 = (1, 2, 3, 4, 5, 6, 7)
        seq2 = (0, 1, 2, 0, 4, 5, 6)
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(insert, 0, (0, 0, 0, 1)),
            DiffItem(unchanged, 1, (0, 1, 1, 2)),
            DiffItem(unchanged, 2, (1, 2, 2, 3)),
            DiffItem(remove, 3, (2, 3, 3, 3)),
            DiffItem(insert, 0, (3, 3, 3, 4)),
            DiffItem(unchanged, 4, (3, 4, 4, 5)),
            DiffItem(unchanged, 5, (4, 5, 5, 6)),
            DiffItem(unchanged, 6, (5, 6, 6, 7)),
            DiffItem(remove, 7, (6, 7, 7, 7))]
        expected_diff = Diff(tuple, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_mainly_inserts(self):
        seq1 = 'hi'
        seq2 = 'hello'
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 'h', (0, 1, 0, 1)),
            DiffItem(remove, 'i', (1, 2, 1, 1)),
            DiffItem(insert, 'e', (2, 2, 1, 2)),
            DiffItem(insert, 'l', (2, 2, 2, 3)),
            DiffItem(insert, 'l', (2, 2, 3, 4)),
            DiffItem(insert, 'o', (2, 2, 4, 5))]
        expected_diff = Diff(str, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_no_recursion_insert_remove_counts_not_equal_1(self):
        # nested_diff_input is None
        seq1 = [1, (1, 2), 0]
        seq2 = [1, (2, 3), 2]
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(remove, (1, 2), (1, 2, 1, 1)),
            DiffItem(remove, 0, (2, 3, 1, 1)),
            DiffItem(insert, (2, 3), (3, 3, 1, 2)),
            DiffItem(insert, 2, (3, 3, 2, 3))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_no_recursion_item_not_diffable(self):
        '''seq1[1] and seq2[2] would be subject to a recursive diff if they
           were diffable'''
        seq1 = [1, 2, 5]
        seq2 = [1, 3, 5]
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(remove, 2, (1, 2, 1, 1)),
            DiffItem(insert, 3, (2, 2, 1, 2)),
            DiffItem(unchanged, 5, (2, 3, 2, 3))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_no_recursion_removal_and_insert_not_same_type(self):
        '''seq1[1] and seq2[1] would be subject to a recursive diff if they
           were the same type'''
        seq1 = [1, (1, 2), 3]
        seq2 = [1, [1, 2], 3]
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(remove, (1, 2), (1, 2, 1, 1)),
            DiffItem(insert, [1, 2], (2, 2, 1, 2)),
            DiffItem(unchanged, 3, (2, 3, 2, 3))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_dont_try_recursive_diff_if_sequences_are_different_lengths(self):
        seq1 = (1, 'ab', 2, 3)
        seq2 = (1, 'bc', 2)
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(remove, 'ab', (1, 2, 1, 1)),
            DiffItem(insert, 'bc', (2, 2, 1, 2)),
            DiffItem(unchanged, 2, (2, 3, 2, 3)),
            DiffItem(remove, 3, (3, 4, 3, 3))]
        expected_diff = Diff(tuple, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_successful_recursive_diff(self):
        # _nested_diff_input matches (unchanged, insert, remove)
        seq1 = (1, 'ab', 2)
        seq2 = (1, 'bc', 2)
        diff_obj = diff_sequence(seq1, seq2)
        nested_diffs = [
            DiffItem(remove, 'a', (0, 1, 0, 0)),
            DiffItem(unchanged, 'b', (1, 2, 0, 1)),
            DiffItem(insert, 'c', (2, 2, 1, 2))]
        nested_diff = Diff(str, nested_diffs, depth=1)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(changed, nested_diff, (1, 2, 1, 2)),
            DiffItem(unchanged, 2, (2, 3, 2, 3))]
        expected_diff = Diff(tuple, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_recursive_diff_before_first_unchanged_item(self):
        seq1 = [[1], 2]
        seq2 = [[0], 2]
        diff_obj = diff_sequence(seq1, seq2)
        nested_diffs = [
            DiffItem(remove, 1, (0, 1, 0, 0)),
            DiffItem(insert, 0, (1, 1, 0, 1))
        ]
        nested_diff = Diff(list, nested_diffs, depth=1)
        diffs = [
            DiffItem(changed, nested_diff, (0, 1, 0, 1)),
            DiffItem(unchanged, 2, (1, 2, 1, 2))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_depth_is_adjustable(self):
        diff_obj = diff_sequence([1, 2], [1, 2], depth=4)
        self.assertEqual(diff_obj.depth, 4)

    def test_single_char_edgecase_in_list(self):
        seq1 = [1, 2, 'a']
        seq2 = [1, 2, 'b']
        diff_obj = diff_sequence(seq1, seq2)
        nested_diffs = [
            DiffItem(remove, 'a', (0, 1, 0, 0)),
            DiffItem(insert, 'b', (1, 1, 0, 1))
        ]
        nested_diff = Diff(str, nested_diffs, depth=1)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(unchanged, 2, (1, 2, 1, 2)),
            DiffItem(changed, nested_diff, (2, 3, 2, 3)),
        ]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)

    def test_single_char_edgecase_in_str(self):
        # there should be no attempt at recursively diffing the final characters
        # ie the diff should be flat.
        seq1 = 'abc'
        seq2 = 'abd'
        diff_obj = diff_sequence(seq1, seq2)
        diffs = [
            DiffItem(unchanged, 'a', (0, 1, 0, 1)),
            DiffItem(unchanged, 'b', (1, 2, 1, 2)),
            DiffItem(remove, 'c', (2, 3, 2, 2)),
            DiffItem(insert, 'd', (3, 3, 2, 3))
        ]
        expected_diff = Diff(str, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(seq1, diff_obj), seq2)


class DiffSetTests(unittest.TestCase):
    def test_no_differences(self):
        test_set = {1, 2, 3, 4, 5}
        diff_obj = diff_set(test_set, test_set)
        diffs = [
            DiffItem(unchanged, i) for i in test_set]
        expected_diff = Diff(set, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(test_set, diff_obj), test_set)

    def test_empty_diff(self):
        set1 = set()
        diff_obj = diff_set(set1, set1)
        expected_diff = Diff(set, [])
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(set1, diff_obj), set1)

    def test_mostly_removals(self):
        set1 = {1, 2, 3, 4}
        set2 = {4}
        diff_obj = diff_set(set1, set2)
        diffs = [
            DiffItem(remove, 1),
            DiffItem(remove, 2),
            DiffItem(remove, 3),
            DiffItem(unchanged, 4)]
        expected_diff = Diff(set, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(set1, diff_obj), set2)

    def test_mostly_insertions(self):
        set1 = {4}
        set2 = {1, 2, 3, 4}
        diff_obj = diff_set(set1, set2)
        diffs = [
            DiffItem(unchanged, 4),
            DiffItem(insert, 1),
            DiffItem(insert, 2),
            DiffItem(insert, 3)]
        expected_diff = Diff(set, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(set1, diff_obj), set2)

    def test_depth_is_adjustable(self):
        diff_obj = diff_set({'a', 'b', 'c'}, {'e'}, _depth=6)
        self.assertEqual(diff_obj.depth, 6)


class DiffMappingTests(unittest.TestCase):
    def test_no_differences(self):
        map1 = {'a': 1}
        diff_obj = diff_mapping(map1, map1)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1)]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map1)

    def test_empty_diff(self):
        map1 = {}
        diff_obj = diff_mapping(map1, map1)
        expected_diff = Diff(dict, [])
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map1)

    def test_mostly_removals(self):
        map1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        map2 = {'c': 3}
        diff_obj = diff_mapping(map1, map2)
        diffs = [
            MappingDiffItem(remove, 'a', remove, 1),
            MappingDiffItem(remove, 'b', remove, 2),
            MappingDiffItem(remove, 'd', remove, 4),
            MappingDiffItem(unchanged, 'c', unchanged, 3)]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)

    def test_mostly_inserts(self):
        map1 = {'c': 3}
        map2 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        diff_obj = diff_mapping(map1, map2)
        diffs = [
            MappingDiffItem(unchanged, 'c', unchanged, 3),
            MappingDiffItem(insert, 'a', insert, 1),
            MappingDiffItem(insert, 'b', insert, 2),
            MappingDiffItem(insert, 'd', insert, 4)]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)

    def test_common_keys_values_not_diffable(self):
        map1 = {'a': 1}
        map2 = {'a': 2}
        diff_obj = diff_mapping(map1, map2)
        diffs = [
            MappingDiffItem(unchanged, 'a', remove, 1),
            MappingDiffItem(unchanged, 'a', insert, 2)]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)

    def test_common_keys_values_different_types(self):
        map1 = {'a': (1, 2)}
        map2 = {'a': '1, 2'}
        diff_obj = diff_mapping(map1, map2)
        diffs = [
            MappingDiffItem(unchanged, 'a', remove, (1, 2)),
            MappingDiffItem(unchanged, 'a', insert, '1, 2')]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)

    def test_common_keys_recursive_diff(self):
        map1 = {'a': {'b': 1}}
        map2 = {'a': {'b': 2}}
        diff_obj = diff_mapping(map1, map2)
        nested_diffs = [
            MappingDiffItem(unchanged, 'b', remove, 1),
            MappingDiffItem(unchanged, 'b', insert, 2)]
        nested_diff = Diff(dict, nested_diffs, depth=1)
        diffs = [
            MappingDiffItem(
                unchanged, 'a', changed, nested_diff)]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)

    def test_depth_is_adjustable(self):
        diff_obj = diff_mapping({'a': 1}, {'b': 2}, _depth=2)
        self.assertEqual(diff_obj.depth, 2)

    def test_single_char_edge_case_in_dict(self):
        map1 = {1: 'a'}
        map2 = {1: 'b'}
        diff_obj = diff_mapping(map1, map2)
        nested_diffs = [
            DiffItem(remove, 'a', (0, 1, 0, 0)),
            DiffItem(insert, 'b', (1, 1, 0, 1))
        ]
        nested_diff = Diff(str, nested_diffs, depth=1)
        diffs = [
            MappingDiffItem(unchanged, 1, changed, nested_diff)
        ]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)


class DiffOrderedMapping(unittest.TestCase):
    def test_no_difference(self):
        d1 = {'a': 1}
        od = OrderedDict(d1)
        diff_obj = diff_ordered_mapping(od, od)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1)]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(od, diff_obj), od)

    def test_empty_diff(self):
        od = OrderedDict()
        diff_obj = diff_ordered_mapping(od, od)
        expected_diff = Diff(OrderedDict, [])
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(od, diff_obj), od)

    def test_common_keys_values_not_diffable(self):
        d1 = {'a': 1, 'b': 2, 'c': 3}
        d2 = {'a': 1, 'b': 3, 'c': 3}
        od1 = OrderedDict(sorted(d1.items(), key=lambda i: i[0]))
        od2 = OrderedDict(sorted(d2.items(), key=lambda i: i[0]))
        diff_obj = diff_ordered_mapping(od1, od2)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1),
            MappingDiffItem(unchanged, 'b', remove, 2),
            MappingDiffItem(unchanged, 'b', insert, 3),
            MappingDiffItem(unchanged, 'c', unchanged, 3)
        ]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(od1, diff_obj), od2)

    def test_common_keys_values_different_types(self):
        d1 = {'a': 1, 'b': ['a'], 'c': 3}
        d2 = {'a': 1, 'b': 'a', 'c': 3}
        od1 = OrderedDict(sorted(d1.items(), key=lambda i: i[0]))
        od2 = OrderedDict(sorted(d2.items(), key=lambda i: i[0]))
        diff_obj = diff_ordered_mapping(od1, od2)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1),
            MappingDiffItem(unchanged, 'b', remove, ['a']),
            MappingDiffItem(unchanged, 'b', insert, 'a'),
            MappingDiffItem(unchanged, 'c', unchanged, 3)
        ]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(od1, diff_obj), od2)

    def test_common_keys_diff_order_matters_1(self):
        '''
        There are two possible lcs's for the keys here. ('a', 'b') and
        ('a', 'c') the lcs algorithm picks only one of them (('a', 'b') in this
        case). We therefore get a recursive diff at key 'b'. and an insert and
        remove on key 'c'. If this were a standard Mapping type key 'c' would
        be unchanged.
        '''
        d1 = OrderedDict(sorted(
            {'a': 1, 'b': 'a', 'c': 3}.items(), key=lambda i: i[0]))
        d2 = OrderedDict(sorted({'a': 1, 'c': 3}.items(), key=lambda i: i[0]))
        d2['b'] = 'b'
        diff_obj = diff_ordered_mapping(d1, d2)
        nested_diffs = [
            DiffItem(remove, 'a', (0, 1, 0, 0)),
            DiffItem(insert, 'b', (1, 1, 0, 1))
        ]
        nested_diff = Diff(str, nested_diffs, depth=1)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1),
            MappingDiffItem(insert, 'c', insert, 3),
            MappingDiffItem(
                unchanged, 'b', changed, nested_diff),
            MappingDiffItem(remove, 'c', remove, 3)
        ]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(d1, diff_obj), d2)

    def test_common_keys_diff_order_matters_2(self):
        '''
        The other possibility from number 1 above wherby we end up with no
        recursive  You actually end up with insert b: b, remove b: b which
        looks odd but is one of the possible minimal edits.
        '''
        d1 = OrderedDict(sorted({'a': 1, 'c': 3}.items(), key=lambda i: i[0]))
        d1['b'] = 'b'
        d2 = OrderedDict(
            sorted({'a': 1, 'b': 'b', 'c': 3}.items(), key=lambda i: i[0]))
        diff_obj = diff_ordered_mapping(d1, d2)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1),
            MappingDiffItem(insert, 'b', insert, 'b'),
            MappingDiffItem(
                unchanged, 'c', unchanged, 3),
            MappingDiffItem(remove, 'b', remove, 'b')
        ]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(d1, diff_obj), d2)

    def test_recursive_diff_when_different_lengths(self):
        '''
        Unlike Sequences, we should still attempt recursive diffs when the
        Ordered Mappings are different sizes.
        '''
        d1 = OrderedDict(
            sorted({'a': 1, 'b': [2]}.items(), key=lambda i: i[0]))
        d2 = OrderedDict(
            sorted({'a': 1, 'b': [3], 'c': 4}.items(), key=lambda i: i[0]))
        diff_obj = diff_ordered_mapping(d1, d2)
        nested_diffs = [
            DiffItem(remove, 2, (0, 1, 0, 0)),
            DiffItem(insert, 3, (1, 1, 0, 1))
        ]
        nested_diff_obj = Diff(list, nested_diffs, depth=1)
        diffs = [
            MappingDiffItem(unchanged, 'a', unchanged, 1),
            MappingDiffItem(
                unchanged, 'b', changed, nested_diff_obj),
            MappingDiffItem(insert, 'c', insert, 4)
        ]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(d1, diff_obj), d2)


class DiffFunctionTests(unittest.TestCase):
    '''
    Many of the built in types have been tested extensively at the lower
    levels so I will test some of the slightly lesser known types here:
        e.g. OrderedDict, namedtuple, frozenset
    '''
    def test_can_diff_mapping_type(self):
        d1 = {'d': 1, 'c': 2, 'b': 3}
        d2 = {'d': 1, 'c': 2, 'a': 3}
        # sort by values
        od1 = OrderedDict(sorted(d1.items(), key=lambda i: i[1]))
        od2 = OrderedDict(sorted(d2.items(), key=lambda i: i[1]))
        diff_obj = diff(od1, od2)
        diffs = [
            MappingDiffItem(unchanged, 'd', unchanged, 1),
            MappingDiffItem(unchanged, 'c', unchanged, 2),
            MappingDiffItem(remove, 'b', remove, 3),
            MappingDiffItem(insert, 'a', insert, 3)]
        expected_diff = Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(od1, diff_obj), od2)

    def test_can_diff_sequence_type(self):
        ThreeDPoint = namedtuple('ThreeDPoint', ['x', 'y', 'z'])
        p1 = ThreeDPoint(0, 0, 0)
        p2 = ThreeDPoint(0, 0, 1)
        diff_obj = diff(p1, p2)
        diffs = [
            DiffItem(unchanged, 0, (0, 1, 0, 1)),
            DiffItem(unchanged, 0, (1, 2, 1, 2)),
            DiffItem(remove, 0, (2, 3, 2, 2)),
            DiffItem(insert, 1, (3, 3, 2, 3))]
        expected_diff = Diff(type(p1), diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(p1, diff_obj), p2)

    def test_can_diff_set_type(self):
        fs1 = frozenset([1, 2, 3])
        fs2 = frozenset([2, 3, 4])
        diff_obj = diff(fs1, fs2)
        diffs = [
            DiffItem(remove, 1),
            DiffItem(unchanged, 2),
            DiffItem(unchanged, 3),
            DiffItem(insert, 4)]
        expected_diff = Diff(frozenset, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(fs1, diff_obj), fs2)

    def test_recursive_diff(self):
        struct1 = [1, {'a': {'a', 'b'}}]
        struct2 = [1, {'a': {'b'}}]
        diff_obj = diff(struct1, struct2)
        depth_2_diffs = [
            DiffItem(remove, 'a'),
            DiffItem(unchanged, 'b')]
        diff_depth_2 = Diff(set, depth_2_diffs, depth=2)
        depth_1_diffs = [
            MappingDiffItem(
                unchanged, 'a', changed, diff_depth_2)]
        diff_depth_1 = Diff(dict, depth_1_diffs, depth=1)
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(changed, diff_depth_1, (1, 2, 1, 2))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(struct1, diff_obj), struct2)

    def test_no_differences(self):
        diff_obj = diff([1, 2, 3], [1, 2, 3])
        diffs = [
            DiffItem(unchanged, 1, (0, 1, 0, 1)),
            DiffItem(unchanged, 2, (1, 2, 1, 2)),
            DiffItem(unchanged, 3, (2, 3, 2, 3))]
        expected_diff = Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)

    def test_empty_diff(self):
        diff_obj = diff((), ())
        self.assertEqual(diff_obj, Diff(tuple, []))

        map1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        map2 = {'a': 2, 'b': 2, 'c': 3, 'e': 4}
        diff_obj = diff(map1, map2)
        diffs = [
            MappingDiffItem(remove, 'd', remove, 4),
            MappingDiffItem(unchanged, 'a', remove, 1),
            MappingDiffItem(unchanged, 'a', insert, 2),
            MappingDiffItem(unchanged, 'c', unchanged, 3),
            MappingDiffItem(unchanged, 'b', unchanged, 2),
            MappingDiffItem(insert, 'e', insert, 4)]
        expected_diff = Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(map1, diff_obj), map2)

    def test_depth_is_adjustable(self):
        diff_obj = diff([1, 2], [2, 3, 4], _depth=3)
        self.assertEqual(diff_obj.depth, 3)

    def test_diff_fail_different_types(self):
        self.assertRaisesRegexp(
            TypeError,
            "diff params are different types {} != {}".format(
                type([]), type('')),
            diff, [], '')

    def test_diff_fail_not_a_diffable_type(self):
        self.assertRaisesRegexp(
            TypeError,
            "No mechanism for diffing objects of type {}".format(type(0)),
            diff, 1, 2)

    def test_single_char_edge_case(self):
        d1 = 'a'
        d2 = 'b'
        diff_obj = diff(d1, d2)
        diffs = [
            DiffItem(remove, 'a', (0, 1, 0, 0)),
            DiffItem(insert, 'b', (1, 1, 0, 1)),
        ]
        expected_diff = Diff(str, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(patch(d1, diff_obj), d2)
