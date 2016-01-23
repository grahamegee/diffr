import sys
import unittest
from differ import diff
from collections import OrderedDict, namedtuple, deque


class SequencesContainSameItemsTests(unittest.TestCase):
    def test_sequences_only_out_of_order(self):
        a = [1, 2, 'a', {1: 'e'}]
        b = [{1: 'e'}, 2, 1, 'a']
        self.assertTrue(diff.sequences_contain_same_items(a, b))

    def test_sequences_contain_single_difference(self):
        a = [1, 2, 3]
        b = [2, 3, 4]
        self.assertFalse(diff.sequences_contain_same_items(a, b))

    def test_sequence_a_bigger_than_b(self):
        a = [1, 2, 3]
        b = [2, 3]
        self.assertFalse(diff.sequences_contain_same_items(a, b))

    def test_sequence_b_bigger_than_a(self):
        a = [2, 3]
        b = [2, 3, 4]
        self.assertFalse(diff.sequences_contain_same_items(a, b))


class DiffsAreEqualTests(unittest.TestCase):
    def test_sequence_diffs_are_equal(self):
        diff_a = diff.diff([1, 2, 3], [2, 3, 4])
        diff_b = diff.diff([1, 2, 3], [2, 3, 4])
        self.assertTrue(diff.diffs_are_equal(diff_a, diff_b))

    def test_ordered_dicts_are_equal(self):
        d = {1: 'a', 2: 'b', 7: 'c', 3: 'd'}
        diff_a = diff.diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[0])),
            OrderedDict(sorted(d.items(), key=lambda k: k[0])))
        diff_b = diff.diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[0])),
            OrderedDict(sorted(d.items(), key=lambda k: k[0])))
        self.assertTrue(diff.diffs_are_equal(diff_a, diff_b))

    def test_ordered_dicts_are_out_of_order(self):
        d = {1: 'a', 2: 'b', 7: 'c', 3: 'd'}
        diff_a = diff.diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[0])),
            OrderedDict(sorted(d.items(), key=lambda k: k[0])))
        diff_b = diff.diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[1])),
            OrderedDict(sorted(d.items(), key=lambda k: k[1])))
        self.assertFalse(diff.diffs_are_equal(diff_a, diff_b))

    def test_dict_diffs_are_equal(self):
        # these should get seeded differently, fairly regularly in python 3
        # the diffs will be equivalent, but ordering of DiffItems will differ
        d1 = {-1: 'y', 0: 'z', 1: 'a', 2: 'b', 3: 'c', 4: 'e'}
        d2 = {1: 'a', 2: 'b', 3: 'd', 4: 'f'}
        diff_a = diff.diff(d1, d2)
        diff_b = diff.diff(d1, d2)
        self.assertTrue(diff.diffs_are_equal(diff_a, diff_b))

    def test_dict_diffs_not_equal(self):
        d1 = {1: 'a', 2: 'b', 3: 'c'}
        d2 = {1: 'a', 2: 'b', 3: 'd'}
        d3 = {1: 'a', 2: 'b', 3: 'e'}
        diff_a = diff.diff(d1, d2)
        diff_b = diff.diff(d1, d3)
        self.assertFalse(diff.diffs_are_equal(diff_a, diff_b))


class DiffTests(unittest.TestCase):
    def test_contexts_start_and_end_with_modified_items(self):
        # this constraint could change; people may want more context...
        diffs = [
            diff.DiffItem(diff.unchanged, 1),
            diff.DiffItem(diff.insert, 2),
            diff.DiffItem(diff.insert, 2),
            diff.DiffItem(diff.unchanged, 1)]
        diff_obj = diff.Diff(list, diffs)
        self.assertEqual(
            diff_obj._create_context_markers(), [(1, 3)])

    def test_context_limit_is_adjustable(self):
        '''The default context limit is 3, if we adjust it to 1 we expect a new
           new context to be started if there is a gap of 2'''
        diffs = [
            diff.DiffItem(diff.insert, 1),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.remove, 1)]
        diff_obj = diff.Diff(list, diffs, context_limit=1)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 1), (3, 4)])

    def test_context_limit_max(self):
        '''Once a context is started,so long as the number of contiguous
           unchanged items doesn't exceed the context limit, they remain part of
           the context'''
        diffs = [
            diff.DiffItem(diff.insert, 1),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.remove, 1)]
        diff_obj = diff.Diff(list, diffs, context_limit=2)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 4)])

    def test_context_limit_max_plus_one(self):
        '''Once a context is started if the number of contiguous unchanged items
           exceeds the context limit the context is cut off at the last modified
           item and a new context is started'''
        diffs = [
            diff.DiffItem(diff.insert, 1),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.remove, 1)]
        diff_obj = diff.Diff(list, diffs, context_limit=2)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 1), (4, 5)])

    def test_context_not_finished_by_end_of_diffs_list(self):
        diffs = [
            diff.DiffItem(diff.insert, 1),
            diff.DiffItem(diff.unchanged, 0)]
        diff_obj = diff.Diff(list, diffs, context_limit=2)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 1)])

    # context block generation
    def test_context_block_generation(self):
        diffs = [
            diff.DiffItem(diff.insert, 1),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.unchanged, 0),
            diff.DiffItem(diff.remove, 1)]
        expected = [
            diff.Diff.ContextBlock(list, [diffs[0]]),
            diff.Diff.ContextBlock(list, [diffs[3]])]
        diff_obj = diff.Diff(list, diffs, context_limit=1)
        diff_obj.create_context_blocks()
        self.assertEqual(
            diff_obj.context_blocks, expected)


class DiffComparisonTests(unittest.TestCase):
    bdiffs = [
        diff.DiffItem(diff.insert, 1),
        diff.DiffItem(diff.unchanged, 2),
        diff.DiffItem(diff.unchanged, 2),
        diff.DiffItem(diff.remove, 3)
    ]
    base_diff = diff.Diff(list, bdiffs, context_limit=1, depth=0)
    base_diff.create_context_blocks()
    ediffs = [
        diff.DiffItem(diff.insert, 1),
        diff.DiffItem(diff.unchanged, 2),
        diff.DiffItem(diff.unchanged, 2),
        diff.DiffItem(diff.remove, 3)
    ]
    expected_diff = diff.Diff(list, ediffs, context_limit=1, depth=0)
    expected_diff.create_context_blocks()

    def test_diffs_compare_equal(self):
        self.assertEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_type(self):
        self.expected_diff.type = tuple
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_context_limit(self):
        self.expected_diff.context_limit = 0
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_depth(self):
        self.expected_diff.depth = 1
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_diffs(self):
        self.diffs = []
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_context_blocks(self):
        self.expected_diff.context_blocks = []
        self.assertNotEqual(self.base_diff, self.expected_diff)


class DiffContextBlockTests(unittest.TestCase):
    def setUp(self):
        self.base_context_diffs = [
            diff.DiffItem(diff.insert, 'a', (0, 1, 1, 2)),
            diff.DiffItem(diff.unchanged, 'b', (1, 2, 2, 3)),
            diff.DiffItem(diff.remove, 'c', (2, 3, 3, 4))]
        self.base_context_block = diff.Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs)

    def test_ContextBlock_context_is_correct(self):
        self.assertEqual(self.base_context_block.context, (0, 3, 1, 4))

    # test rich comparison methods
    def test_ContextBlocks_equal(self):
        equal_context_block = diff.Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs)
        self.assertEqual(
            self.base_context_block, equal_context_block)

    def test_ContextBlocks_have_different_diffs(self):
        context_diffs = [
            d for d in self.base_context_diffs if d.state is not diff.unchanged]
        different_context_block = diff.Diff(list, context_diffs).ContextBlock(
            list, context_diffs)
        self.assertNotEqual(
            self.base_context_block, different_context_block)

    def test_ContextBlocks_have_different_contexts(self):
        self.base_context_diffs[0].context = (2, 3, 4, 5)
        different_context_block = diff.Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs)
        self.assertNotEqual(
            self.base_context_block, different_context_block)

    def test_ContextBlocks_have_different_depths(self):
        different_context_block = diff.Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs, depth=1)
        self.assertNotEqual(
            self.base_context_block, different_context_block)


class DiffItemTests(unittest.TestCase):
    def setUp(self):
        self.base_diff_item = diff.DiffItem(diff.insert, 1)

    def test_equal_DiffItems(self):
        self.assertEqual(
            self.base_diff_item, diff.DiffItem(diff.insert, 1))

    def test_diff_items_differ_by_state(self):
        self.assertNotEqual(
            self.base_diff_item, diff.DiffItem(diff.remove, 1))

    def test_diff_items_differ_by_context(self):
        self.assertNotEqual(
            self.base_diff_item, diff.DiffItem(diff.insert, 1, context=1))

    def test_diff_items_differ_by_item(self):
        self.assertNotEqual(
            self.base_diff_item, diff.DiffItem(diff.insert, 2))


class MappingDiffItemTests(unittest.TestCase):
    def setUp(self):
        self.base_diff_item = diff.MappingDiffItem(
            diff.insert, 'a', diff.insert, 1)

    def test_equal_MappingDiffItems(self):
        self.assertEqual(
            self.base_diff_item, diff.MappingDiffItem(
                diff.insert, 'a', diff.insert, 1))

    def test_MappingDiffItems_differ_by_key_state(self):
        self.assertNotEqual(
            self.base_diff_item, diff.MappingDiffItem(
                diff.unchanged, 'a', diff.insert, 1))

    def test_MappingDiffItems_differ_by_key(self):
        self.assertNotEqual(
            self.base_diff_item, diff.MappingDiffItem(
                diff.insert, 'b', diff.insert, 1))

    def test_MappingDiffItems_differ_by_state(self):
        self.assertNotEqual(
            self.base_diff_item, diff.MappingDiffItem(
                diff.insert, 'a', diff.remove, 1))

    def test_MappingDiffItems_differ_by_value(self):
        self.assertNotEqual(
            self.base_diff_item, diff.MappingDiffItem(
                diff.insert, 'a', diff.insert, 2))


class ChunkTests(unittest.TestCase):
    def test_diff_block_states_attribute(self):
        chunk = diff.Chunk([
            diff.DiffItem(diff.unchanged, 1),
            diff.DiffItem(diff.remove, 1),
            diff.DiffItem(diff.insert, 1)
        ])
        self.assertEqual(
            chunk.states,
            (diff.unchanged, diff.remove, diff.insert))


class BacktrackTests(unittest.TestCase):
    def test_lcs_is_contiguous(self):
        seq1 = '-abc-'
        seq2 = '.abc.'
        expected_lcs = [(1, 1), (2, 2), (3, 3)]
        lcs_gen = diff._backtrack(diff._build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_lcs_is_not_contiguous(self):
        seq1 = '-a-b-c-'
        seq2 = '.a.b.c.'
        expected_lcs = [(1, 1), (3, 3), (5, 5)]
        lcs_gen = diff._backtrack(diff._build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_lcs_is_not_aligned(self):
        seq1 = '---a-bc'
        seq2 = 'ab.c..'
        expected_lcs = [(3, 0), (5, 1), (6, 3)]
        lcs_gen = diff._backtrack(diff._build_lcs_matrix(seq1, seq2))
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
        lcs_gen = diff._backtrack(diff._build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])

    def test_no_lcs(self):
        seq1 = 'abc'
        seq2 = 'xyz'
        expected_lcs = []
        lcs_gen = diff._backtrack(diff._build_lcs_matrix(seq1, seq2))
        self.assertEqual(
            expected_lcs,
            [i for i in reversed([x for x in lcs_gen])])


class ChunkerTests(unittest.TestCase):
    def test_empty_diff_block(self):
        chunks = diff.chunker(
            diff.diff_item_data_factory(deque([]), deque([]), ())
        )
        self.assertEqual(next(chunks), diff.Chunk())

    def test_only_inserts(self):
        q1 = deque([])
        q2 = deque([1, 2])
        lcs_marker = ()
        expected_diff_block = diff.Chunk([
            diff.DiffItem(diff.insert, 1, (0, 0, 0, 1)),
            diff.DiffItem(diff.insert, 2, (0, 0, 1, 2))
        ])
        chunks = diff.chunker(
            diff.diff_item_data_factory(q1, q2, lcs_marker)
        )
        self.assertEqual(next(chunks), expected_diff_block)

    def test_only_removals(self):
        q1 = deque([1, 2])
        q2 = deque([])
        lcs_marker = ()
        expected_diff_block = diff.Chunk([
            diff.DiffItem(diff.remove, 1, (0, 1, 0, 0)),
            diff.DiffItem(diff.remove, 2, (1, 2, 0, 0))
        ])
        chunks = diff.chunker(
            diff.diff_item_data_factory(q1, q2, lcs_marker)
        )
        self.assertEqual(next(chunks), expected_diff_block)

    def test_only_unchanged(self):
        q1 = deque([1, 2])
        q2 = deque([1, 2])
        lcs_markers = ((0, 0), (1, 1))
        chunk_1 = diff.Chunk([
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1))
        ])
        chunk_2 = diff.Chunk([
            diff.DiffItem(diff.unchanged, 2, (1, 2, 1, 2))
        ])
        chunks = diff.chunker(
            diff.diff_item_data_factory(q1, q2, lcs_markers)
        )
        self.assertEqual(next(chunks), chunk_1)
        self.assertEqual(next(chunks), chunk_2)

    def test_some_changes_after_an_unchanged_item(self):
        q1 = deque([0, 1, 2])
        q2 = deque([0, 3, 4])
        lcs_marker = ((0, 0),)
        chunk_1 = diff.Chunk([
            diff.DiffItem(diff.unchanged, 0, (0, 1, 0, 1))
        ])
        chunk_2 = diff.Chunk([
            diff.DiffItem(diff.remove, 1, (1, 2, 1, 1)),
            diff.DiffItem(diff.remove, 2, (2, 3, 1, 1)),
            diff.DiffItem(diff.insert, 3, (3, 3, 1, 2)),
            diff.DiffItem(diff.insert, 4, (3, 3, 2, 3))
        ])
        chunks = diff.chunker(
            diff.diff_item_data_factory(q1, q2, lcs_marker)
        )
        self.assertEqual(next(chunks), chunk_1)
        self.assertEqual(next(chunks), chunk_2)

    def test_changes_before_the_first_unchanged_item(self):
        q1 = deque([1, 4])
        q2 = deque([2, 4])
        lcs_markers = ((1, 1),)
        chunk = diff.Chunk([
            diff.DiffItem(diff.remove, 1, (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 2, (1, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 4, (1, 2, 1, 2))
        ])
        chunks = diff.chunker(
            diff.diff_item_data_factory(q1, q2, lcs_markers)
        )
        self.assertEqual(next(chunks), chunk)


class DiffSequenceTest(unittest.TestCase):
    def test_empty_diff(self):
        seq = []
        diff_obj = diff.diff_sequence(seq, seq)
        expected_diff = diff.Diff(list, seq)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq, diff_obj), seq)

    def test_no_differences(self):
        seq = [1, 2]
        diff_obj = diff.diff_sequence(seq, seq)
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 2, (1, 2, 1, 2))]
        expected_diff = diff.Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq, diff_obj), seq)

    # --------------------------------------------------------------------------
    # This block of tests is a bit vague, but is designed to give us confidence
    # that the returned diff generally looks right.
    # --------------------------------------------------------------------------
    def test_mainly_removals(self):
        seq1 = 'hello'
        seq2 = 'hi'
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 'h', (0, 1, 0, 1)),
            diff.DiffItem(diff.remove, 'e', (1, 2, 1, 1)),
            diff.DiffItem(diff.remove, 'l', (2, 3, 1, 1)),
            diff.DiffItem(diff.remove, 'l', (3, 4, 1, 1)),
            diff.DiffItem(diff.remove, 'o', (4, 5, 1, 1)),
            diff.DiffItem(diff.insert, 'i', (5, 5, 1, 2))]
        expected_diff = diff.Diff(str, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(str, diffs[1:])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_mainly_unchanged(self):
        seq1 = (1, 2, 3, 4, 5, 6, 7)
        seq2 = (0, 1, 2, 0, 4, 5, 6)
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.insert, 0, (0, 0, 0, 1)),
            diff.DiffItem(diff.unchanged, 1, (0, 1, 1, 2)),
            diff.DiffItem(diff.unchanged, 2, (1, 2, 2, 3)),
            diff.DiffItem(diff.remove, 3, (2, 3, 3, 3)),
            diff.DiffItem(diff.insert, 0, (3, 3, 3, 4)),
            diff.DiffItem(diff.unchanged, 4, (3, 4, 4, 5)),
            diff.DiffItem(diff.unchanged, 5, (4, 5, 5, 6)),
            diff.DiffItem(diff.unchanged, 6, (5, 6, 6, 7)),
            diff.DiffItem(diff.remove, 7, (6, 7, 7, 7))]
        expected_diff = diff.Diff(tuple, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(tuple, diffs)]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_mainly_inserts(self):
        seq1 = 'hi'
        seq2 = 'hello'
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 'h', (0, 1, 0, 1)),
            diff.DiffItem(diff.remove, 'i', (1, 2, 1, 1)),
            diff.DiffItem(diff.insert, 'e', (2, 2, 1, 2)),
            diff.DiffItem(diff.insert, 'l', (2, 2, 2, 3)),
            diff.DiffItem(diff.insert, 'l', (2, 2, 3, 4)),
            diff.DiffItem(diff.insert, 'o', (2, 2, 4, 5))]
        expected_diff = diff.Diff(str, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(str, diffs[1:])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_context_blocks_provides_slices(self):
        seq1 = 'um hello there'
        seq2 = 'yo, I mean hello'
        diff_obj = diff.diff_sequence(seq1, seq2)
        cb_1 = diff_obj.context_blocks[0]
        cb_2 = diff_obj.context_blocks[1]
        s1_start, s1_end, s2_start, s2_end = cb_1.context
        self.assertEqual(seq1[s1_start:s1_end], 'um')
        self.assertEqual(seq2[s2_start:s2_end], 'yo, I mean')
        s1_start, s1_end, s2_start, s2_end = cb_2.context
        self.assertEqual(seq1[s1_start:s1_end], ' there')
        self.assertEqual(seq2[s2_start:s2_end], '')

    def test_no_recursion_insert_remove_counts_not_equal_1(self):
        # nested_diff_input is None
        seq1 = [1, (1, 2), 0]
        seq2 = [1, (2, 3), 2]
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.remove, (1, 2), (1, 2, 1, 1)),
            diff.DiffItem(diff.remove, 0, (2, 3, 1, 1)),
            diff.DiffItem(diff.insert, (2, 3), (3, 3, 1, 2)),
            diff.DiffItem(diff.insert, 2, (3, 3, 2, 3))]
        expected_diff = diff.Diff(list, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, diffs[1:])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_no_recursion_item_not_diffable(self):
        '''seq1[1] and seq2[2] would be subject to a recursive diff if they
           were diffable'''
        seq1 = [1, 2, 5]
        seq2 = [1, 3, 5]
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.remove, 2, (1, 2, 1, 1)),
            diff.DiffItem(diff.insert, 3, (2, 2, 1, 2)),
            diff.DiffItem(diff.unchanged, 5, (2, 3, 2, 3))]
        expected_diff = diff.Diff(list, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, diffs[1:3])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_no_recursion_removal_and_insert_not_same_type(self):
        '''seq1[1] and seq2[1] would be subject to a recursive diff if they
           were the same type'''
        seq1 = [1, (1, 2), 3]
        seq2 = [1, [1, 2], 3]
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.remove, (1, 2), (1, 2, 1, 1)),
            diff.DiffItem(diff.insert, [1, 2], (2, 2, 1, 2)),
            diff.DiffItem(diff.unchanged, 3, (2, 3, 2, 3))]
        expected_diff = diff.Diff(list, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, diffs[1:3])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_dont_try_recursive_diff_if_sequences_are_different_lengths(self):
        seq1 = (1, 'ab', 2, 3)
        seq2 = (1, 'bc', 2)
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.remove, 'ab', (1, 2, 1, 1)),
            diff.DiffItem(diff.insert, 'bc', (2, 2, 1, 2)),
            diff.DiffItem(diff.unchanged, 2, (2, 3, 2, 3)),
            diff.DiffItem(diff.remove, 3, (3, 4, 3, 3))]
        expected_diff = diff.Diff(tuple, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(tuple, diffs[1:])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_successful_recursive_diff(self):
        # _nested_diff_input matches (unchanged, insert, remove)
        seq1 = (1, 'ab', 2)
        seq2 = (1, 'bc', 2)
        diff_obj = diff.diff_sequence(seq1, seq2)
        nested_diffs = [
            diff.DiffItem(diff.remove, 'a', (0, 1, 0, 0)),
            diff.DiffItem(diff.unchanged, 'b', (1, 2, 0, 1)),
            diff.DiffItem(diff.insert, 'c', (2, 2, 1, 2))]
        nested_diff = diff.Diff(str, nested_diffs, depth=1)
        nested_diff.context_blocks = [
            nested_diff.ContextBlock(str, nested_diff.diffs, depth=1)]
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.changed, nested_diff, (1, 2, 1, 2)),
            diff.DiffItem(diff.unchanged, 2, (2, 3, 2, 3))]
        expected_diff = diff.Diff(tuple, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(tuple, [diffs[1]])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_recursive_diff_before_first_unchanged_item(self):
        seq1 = [[1], 2]
        seq2 = [[0], 2]
        diff_obj = diff.diff_sequence(seq1, seq2)
        nested_diffs = [
            diff.DiffItem(diff.remove, 1, (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 0, (1, 1, 0, 1))
        ]
        nested_diff = diff.Diff(list, nested_diffs, depth=1)
        nested_diff.context_blocks = [
            nested_diff.ContextBlock(list, nested_diff.diffs, depth=1)]
        diffs = [
            diff.DiffItem(diff.changed, nested_diff, (0, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 2, (1, 2, 1, 2))]
        expected_diff = diff.Diff(list, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, [diffs[0]])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_context_limit_is_adjustable(self):
        seq1 = [2, 3, 4]
        seq2 = [1, 3, 5]
        diff_obj = diff.diff_sequence(seq1, seq2, context_limit=0)
        diffs = [
            diff.DiffItem(diff.remove, 2, (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 1, (1, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 3, (1, 2, 1, 2)),
            diff.DiffItem(diff.remove, 4, (2, 3, 2, 2)),
            diff.DiffItem(diff.insert, 5, (3, 3, 2, 3))]
        expected_diff = diff.Diff(list, diffs, context_limit=0)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, diffs[0:2]),
            expected_diff.ContextBlock(list, diffs[3:5])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_depth_is_adjustable(self):
        diff_obj = diff.diff_sequence([1, 2], [1, 2], depth=4)
        self.assertEqual(diff_obj.depth, 4)

    def test_single_char_edgecase_in_list(self):
        seq1 = [1, 2, 'a']
        seq2 = [1, 2, 'b']
        diff_obj = diff.diff_sequence(seq1, seq2)
        nested_diffs = [
            diff.DiffItem(diff.remove, 'a', (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 'b', (1, 1, 0, 1))
        ]
        nested_diff = diff.Diff(str, nested_diffs, depth=1)
        nested_diff.context_blocks = [
            nested_diff.ContextBlock(str, nested_diffs, depth=1)
        ]
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 2, (1, 2, 1, 2)),
            diff.DiffItem(diff.changed, nested_diff, (2, 3, 2, 3)),
        ]
        expected_diff = diff.Diff(list, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, diffs[2:])
        ]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)

    def test_single_char_edgecase_in_str(self):
        # there should be no attempt at recursively diffing the final characters
        # ie the diff should be flat.
        seq1 = 'abc'
        seq2 = 'abd'
        diff_obj = diff.diff_sequence(seq1, seq2)
        diffs = [
            diff.DiffItem(diff.unchanged, 'a', (0, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 'b', (1, 2, 1, 2)),
            diff.DiffItem(diff.remove, 'c', (2, 3, 2, 2)),
            diff.DiffItem(diff.insert, 'd', (3, 3, 2, 3))
        ]
        expected_diff = diff.Diff(str, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(str, diffs[2:4])
        ]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(seq1, diff_obj), seq2)


class DiffSetTests(unittest.TestCase):
    def test_no_differences(self):
        test_set = {1, 2, 3, 4, 5}
        diff_obj = diff.diff_set(test_set, test_set)
        diffs = [
            diff.DiffItem(diff.unchanged, i) for i in test_set]
        expected_diff = diff.Diff(set, diffs)
        self.assertEqual(diff_obj, expected_diff)

    def test_empty_diff(self):
        diff_obj = diff.diff_set(set(), set())
        expected_diff = diff.Diff(set, [])
        self.assertEqual(diff_obj, expected_diff)

    def test_mostly_removals(self):
        set1 = {1, 2, 3, 4}
        set2 = {4}
        diff_obj = diff.diff_set(set1, set2)
        diffs = [
            diff.DiffItem(diff.remove, 1),
            diff.DiffItem(diff.remove, 2),
            diff.DiffItem(diff.remove, 3),
            diff.DiffItem(diff.unchanged, 4)]
        expected_diff = diff.Diff(set, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(set, diffs[:3])]
        self.assertEqual(diff_obj, expected_diff)

    def test_mostly_insertions(self):
        set1 = {4}
        set2 = {1, 2, 3, 4}
        diff_obj = diff.diff_set(set1, set2)
        diffs = [
            diff.DiffItem(diff.unchanged, 4),
            diff.DiffItem(diff.insert, 1),
            diff.DiffItem(diff.insert, 2),
            diff.DiffItem(diff.insert, 3)]
        expected_diff = diff.Diff(set, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(set, diffs[1:])]
        self.assertEqual(diff_obj, expected_diff)

    def test_context_limit_is_adjustable(self):
        set1 = {1, 2, 3, 4}
        set2 = {0, 2, 3, 6}
        diff_obj = diff.diff_set(set1, set2, context_limit=1)
        # This diff doesn't quite look like you would expect a sequence diff to
        # i,e the first 2 DiffItems might look the wrong way round in sequences
        # diffs removals come before inserts. Sets aren't ordered like
        # sequences (although python displays them sorted), therefore it would
        # be wrong to use the sequence diffing algorithms to diff them. In the
        # case of sets the Diff.diffs list is constructed in the sort order of
        # the union of the two sets being diffed.
        diffs = [
            diff.DiffItem(diff.remove, 1),
            diff.DiffItem(diff.remove, 4),
            diff.DiffItem(diff.unchanged, 2),
            diff.DiffItem(diff.unchanged, 3),
            diff.DiffItem(diff.insert, 0),
            diff.DiffItem(diff.insert, 6)]
        expected_diff = diff.Diff(set, diffs, context_limit=1)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(set, diffs[:2]),
            expected_diff.ContextBlock(set, diffs[4:])]
        self.assertEqual(diff_obj, expected_diff)

    def test_depth_is_adjustable(self):
        diff_obj = diff.diff_set({'a', 'b', 'c'}, {'e'}, _depth=6)
        self.assertEqual(diff_obj.depth, 6)


class DiffMappingTests(unittest.TestCase):
    def test_no_differences(self):
        map1 = {'a': 1}
        diff_obj = diff.diff_mapping(map1, map1)
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1)]
        expected_diff = diff.Diff(dict, diffs)
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map1)

    def test_empty_diff(self):
        map1 = {}
        diff_obj = diff.diff_mapping(map1, map1)
        expected_diff = diff.Diff(dict, [])
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map1)

    def test_mostly_removals(self):
        map1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        map2 = {'c': 3}
        diff_obj = diff.diff_mapping(map1, map2)
        diffs = [
            diff.MappingDiffItem(diff.remove, 'a', diff.remove, 1),
            diff.MappingDiffItem(diff.remove, 'b', diff.remove, 2),
            diff.MappingDiffItem(diff.remove, 'd', diff.remove, 4),
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 3)]
        expected_diff = diff.Diff(dict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs[0:3])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)

    def test_mostly_inserts(self):
        map1 = {'c': 3}
        map2 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        diff_obj = diff.diff_mapping(map1, map2)
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 3),
            diff.MappingDiffItem(diff.insert, 'a', diff.insert, 1),
            diff.MappingDiffItem(diff.insert, 'b', diff.insert, 2),
            diff.MappingDiffItem(diff.insert, 'd', diff.insert, 4)]
        expected_diff = diff.Diff(dict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs[1:])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)

    def test_common_keys_values_not_diffable(self):
        map1 = {'a': 1}
        map2 = {'a': 2}
        diff_obj = diff.diff_mapping(map1, map2)
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.remove, 1),
            diff.MappingDiffItem(diff.unchanged, 'a', diff.insert, 2)]
        expected_diff = diff.Diff(dict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs)]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)

    def test_common_keys_values_different_types(self):
        map1 = {'a': (1, 2)}
        map2 = {'a': '1, 2'}
        diff_obj = diff.diff_mapping(map1, map2)
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.remove, (1, 2)),
            diff.MappingDiffItem(diff.unchanged, 'a', diff.insert, '1, 2')]
        expected_diff = diff.Diff(dict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs)]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)

    def test_common_keys_recursive_diff(self):
        map1 = {'a': {'b': 1}}
        map2 = {'a': {'b': 2}}
        diff_obj = diff.diff_mapping(map1, map2)
        nested_diffs = [
            diff.MappingDiffItem(diff.unchanged, 'b', diff.remove, 1),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.insert, 2)]
        nested_diff = diff.Diff(dict, nested_diffs, depth=1)
        nested_diff.context_blocks = [
            nested_diff.ContextBlock(dict, nested_diff.diffs, depth=1)]
        diffs = [
            diff.MappingDiffItem(
                diff.unchanged, 'a', diff.changed, nested_diff)]
        expected_diff = diff.Diff(dict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs)]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)

    def test_context_limit_is_adjustable(self):
        map1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        map2 = {'a': 2, 'b': 2, 'c': 3, 'e': 4}
        diff_obj = diff.diff_mapping(map1, map2, context_limit=1)
        diffs = [
            diff.MappingDiffItem(diff.remove, 'd', diff.remove, 4),
            diff.MappingDiffItem(diff.unchanged, 'a', diff.remove, 1),
            diff.MappingDiffItem(diff.unchanged, 'a', diff.insert, 2),
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 3),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.unchanged, 2),
            diff.MappingDiffItem(diff.insert, 'e', diff.insert, 4)]
        expected_diff = diff.Diff(dict, diffs, context_limit=1)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs[:3]),
            expected_diff.ContextBlock(dict, diffs[5:])]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)

    def test_depth_is_adjustable(self):
        diff_obj = diff.diff_mapping({'a': 1}, {'b': 2}, _depth=2)
        self.assertEqual(diff_obj.depth, 2)

    def test_single_char_edge_case_in_dict(self):
        map1 = {1: 'a'}
        map2 = {1: 'b'}
        diff_obj = diff.diff_mapping(map1, map2)
        nested_diffs = [
            diff.DiffItem(diff.remove, 'a', (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 'b', (1, 1, 0, 1))
        ]
        nested_diff = diff.Diff(str, nested_diffs, depth=1)
        nested_diff.context_blocks = [
            nested_diff.ContextBlock(str, nested_diffs, depth=1)
        ]
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 1, diff.changed, nested_diff)
        ]
        expected_diff = diff.Diff(dict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs)
        ]
        self.assertEqual(diff_obj, expected_diff)
        self.assertEqual(diff.patch(map1, diff_obj), map2)


class DiffOrderedMapping(unittest.TestCase):
    def test_no_difference(self):
        d1 = {'a': 1}
        diff_obj = diff.diff_ordered_mapping(OrderedDict(d1), OrderedDict(d1))
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1)]
        expected_diff = diff.Diff(OrderedDict, diffs)
        self.assertEqual(diff_obj, expected_diff)

    def test_empty_diff(self):
        diff_obj = diff.diff_ordered_mapping(OrderedDict({}), OrderedDict({}))
        expected_diff = diff.Diff(OrderedDict, [])
        self.assertEqual(diff_obj, expected_diff)

    def test_common_keys_values_not_diffable(self):
        d1 = {'a': 1, 'b': 2, 'c': 3}
        d2 = {'a': 1, 'b': 3, 'c': 3}
        diff_obj = diff.diff_ordered_mapping(
            OrderedDict(sorted(d1.items(), key=lambda i: i[0])),
            OrderedDict(sorted(d2.items(), key=lambda i: i[0]))
        )
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.remove, 2),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.insert, 3),
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 3)
        ]
        expected_diff = diff.Diff(OrderedDict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(OrderedDict, diffs[1:3])
        ]
        self.assertEqual(diff_obj, expected_diff)

    def test_common_keys_values_different_types(self):
        d1 = {'a': 1, 'b': ['a'], 'c': 3}
        d2 = {'a': 1, 'b': 'a', 'c': 3}
        diff_obj = diff.diff_ordered_mapping(
            OrderedDict(sorted(d1.items(), key=lambda i: i[0])),
            OrderedDict(sorted(d2.items(), key=lambda i: i[0]))
        )
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.remove, ['a']),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.insert, 'a'),
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 3)
        ]
        expected_diff = diff.Diff(OrderedDict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(OrderedDict, diffs[1:3])
        ]
        self.assertEqual(diff_obj, expected_diff)

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
        diff_obj = diff.diff_ordered_mapping(d1, d2)
        nested_diffs = [
            diff.DiffItem(diff.remove, 'a', (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 'b', (1, 1, 0, 1))
        ]
        nested_diff = diff.Diff(str, nested_diffs, depth=1)
        nested_diff.context_blocks = [
            nested_diff.ContextBlock(str, nested_diffs, depth=1)
        ]
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1),
            diff.MappingDiffItem(diff.insert, 'c', diff.insert, 3),
            diff.MappingDiffItem(
                diff.unchanged, 'b', diff.changed, nested_diff),
            diff.MappingDiffItem(diff.remove, 'c', diff.remove, 3)
        ]
        expected_diff = diff.Diff(OrderedDict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(OrderedDict, diffs[1:])
        ]
        self.assertEqual(diff_obj, expected_diff)

    def test_common_keys_diff_order_matters_2(self):
        '''
        The other possibility from number 1 above wherby we end up with no
        recursive diff. You actually end up with insert b: b, remove b: b which
        looks odd but is one of the possible minimal edits.
        '''
        d1 = OrderedDict(sorted({'a': 1, 'c': 3}.items(), key=lambda i: i[0]))
        d1['b'] = 'b'
        d2 = OrderedDict(
            sorted({'a': 1, 'b': 'b', 'c': 3}.items(), key=lambda i: i[0]))
        diff_obj = diff.diff_ordered_mapping(d1, d2)
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1),
            diff.MappingDiffItem(diff.insert, 'b', diff.insert, 'b'),
            diff.MappingDiffItem(
                diff.unchanged, 'c', diff.unchanged, 3),
            diff.MappingDiffItem(diff.remove, 'b', diff.remove, 'b')
        ]
        expected_diff = diff.Diff(OrderedDict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(OrderedDict, diffs[1:])
        ]
        self.assertEqual(diff_obj, expected_diff)

    def test_recursive_diff_when_different_lengths(self):
        '''
        Unlike Sequences, we should still attempt recursive diffs when the
        Ordered Mappings are different sizes.
        '''
        d1 = OrderedDict(
            sorted({'a': 1, 'b': [2]}.items(), key=lambda i: i[0]))
        d2 = OrderedDict(
            sorted({'a': 1, 'b': [3], 'c': 4}.items(), key=lambda i: i[0]))
        diff_obj = diff.diff_ordered_mapping(d1, d2)
        nested_diffs = [
            diff.DiffItem(diff.remove, 2, (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 3, (1, 1, 0, 1))
        ]
        nested_diff_obj = diff.Diff(list, nested_diffs, depth=1)
        nested_diff_obj.context_blocks = [
            nested_diff_obj.ContextBlock(list, nested_diffs, depth=1)
        ]
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'a', diff.unchanged, 1),
            diff.MappingDiffItem(
                diff.unchanged, 'b', diff.changed, nested_diff_obj),
            diff.MappingDiffItem(diff.insert, 'c', diff.insert, 4)
        ]
        expected_diff = diff.Diff(OrderedDict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(OrderedDict, diffs[1:])
        ]
        self.assertEqual(diff_obj, expected_diff)


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
        diff_obj = diff.diff(od1, od2)
        diffs = [
            diff.MappingDiffItem(diff.unchanged, 'd', diff.unchanged, 1),
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 2),
            diff.MappingDiffItem(diff.remove, 'b', diff.remove, 3),
            diff.MappingDiffItem(diff.insert, 'a', diff.insert, 3)]
        expected_diff = diff.Diff(OrderedDict, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(OrderedDict, diffs[2:])]
        self.assertEqual(diff_obj, expected_diff)

    def test_can_diff_sequence_type(self):
        ThreeDPoint = namedtuple('ThreeDPoint', ['x', 'y', 'z'])
        p1 = ThreeDPoint(0, 0, 0)
        p2 = ThreeDPoint(0, 0, 1)
        diff_obj = diff.diff(p1, p2)
        diffs = [
            diff.DiffItem(diff.unchanged, 0, (0, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 0, (1, 2, 1, 2)),
            diff.DiffItem(diff.remove, 0, (2, 3, 2, 2)),
            diff.DiffItem(diff.insert, 1, (3, 3, 2, 3))]
        expected_diff = diff.Diff(type(p1), diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(type(p1), diffs[2:])]
        self.assertEqual(diff_obj, expected_diff)

    def test_can_diff_set_type(self):
        fs1 = frozenset([1, 2, 3])
        fs2 = frozenset([2, 3, 4])
        diff_obj = diff.diff(fs1, fs2)
        diffs = [
            diff.DiffItem(diff.remove, 1),
            diff.DiffItem(diff.unchanged, 2),
            diff.DiffItem(diff.unchanged, 3),
            diff.DiffItem(diff.insert, 4)]
        expected_diff = diff.Diff(frozenset, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(frozenset, diffs)]
        self.assertEqual(diff_obj, expected_diff)

    def test_recursive_diff(self):
        struct1 = [1, {'a': {'a', 'b'}}]
        struct2 = [1, {'a': {'b'}}]
        diff_obj = diff.diff(struct1, struct2)
        depth_2_diffs = [
            diff.DiffItem(diff.remove, 'a'),
            diff.DiffItem(diff.unchanged, 'b')]
        diff_depth_2 = diff.Diff(set, depth_2_diffs, depth=2)
        diff_depth_2.context_blocks = [
            diff_depth_2.ContextBlock(set, [diff_depth_2.diffs[0]], depth=2)]
        depth_1_diffs = [
            diff.MappingDiffItem(
                diff.unchanged, 'a', diff.changed, diff_depth_2)]
        diff_depth_1 = diff.Diff(dict, depth_1_diffs, depth=1)
        diff_depth_1.context_blocks = [
            diff_depth_1.ContextBlock(dict, diff_depth_1.diffs, depth=1)]
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.changed, diff_depth_1, (1, 2, 1, 2))]
        expected_diff = diff.Diff(list, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(list, [diffs[1]])]
        self.assertEqual(diff_obj, expected_diff)

    def test_no_differences(self):
        diff_obj = diff.diff([1, 2, 3], [1, 2, 3])
        diffs = [
            diff.DiffItem(diff.unchanged, 1, (0, 1, 0, 1)),
            diff.DiffItem(diff.unchanged, 2, (1, 2, 1, 2)),
            diff.DiffItem(diff.unchanged, 3, (2, 3, 2, 3))]
        expected_diff = diff.Diff(list, diffs)
        self.assertEqual(diff_obj, expected_diff)

    def test_empty_diff(self):
        diff_obj = diff.diff((), ())
        self.assertEqual(diff_obj, diff.Diff(tuple, []))

    def test_context_limit_is_adjustable(self):
        map1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        map2 = {'a': 2, 'b': 2, 'c': 3, 'e': 4}
        diff_obj = diff.diff(map1, map2, context_limit=1)
        diffs = [
            diff.MappingDiffItem(diff.remove, 'd', diff.remove, 4),
            diff.MappingDiffItem(diff.unchanged, 'a', diff.remove, 1),
            diff.MappingDiffItem(diff.unchanged, 'a', diff.insert, 2),
            diff.MappingDiffItem(diff.unchanged, 'c', diff.unchanged, 3),
            diff.MappingDiffItem(diff.unchanged, 'b', diff.unchanged, 2),
            diff.MappingDiffItem(diff.insert, 'e', diff.insert, 4)]
        expected_diff = diff.Diff(dict, diffs, context_limit=1)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(dict, diffs[0:3]),
            expected_diff.ContextBlock(dict, diffs[5:])]
        self.assertEqual(diff_obj, expected_diff)

    def test_depth_is_adjustable(self):
        diff_obj = diff.diff([1, 2], [2, 3, 4], _depth=3)
        self.assertEqual(diff_obj.depth, 3)

    def test_diff_fail_different_types(self):
        self.assertRaisesRegexp(
            TypeError,
            "diff params are different types {} != {}".format(
                type([]), type('')),
            diff.diff, [], '')

    def test_diff_fail_not_a_diffable_type(self):
        self.assertRaisesRegexp(
            TypeError,
            "No mechanism for diffing objects of type {}".format(type(0)),
            diff.diff, 1, 2)

    def test_single_char_edge_case(self):
        d1 = 'a'
        d2 = 'b'
        diff_obj = diff.diff(d1, d2)
        diffs = [
            diff.DiffItem(diff.remove, 'a', (0, 1, 0, 0)),
            diff.DiffItem(diff.insert, 'b', (1, 1, 0, 1)),
        ]
        expected_diff = diff.Diff(str, diffs)
        expected_diff.context_blocks = [
            expected_diff.ContextBlock(str, diffs)
        ]
        self.assertEqual(diff_obj, expected_diff)


class DiffStringTests(unittest.TestCase):
    '''
    Ultimately the printed diff output will probably be the most useful part of
    this library. Here we tests the Diff.__str__ correctly represents the Diff.
    '''
    # FIXME: As the printable output is so important, every test which creates a
    # Diff object should probably also test that its str is as expected.
    def test_diff_item_str(self):
        item = 'a'
        di = diff.DiffItem(diff.remove, item)
        expected_str = diff.remove('{}'.format(item))
        self.assertEqual(di.__str__(), expected_str)

    def test_mapping_diff_item_str(self):
        key = 'a'
        val = [1, 2, 3]
        di = diff.MappingDiffItem(
            diff.unchanged, key, diff.insert, val)
        expected_str = (
            diff.unchanged('{!s}: '.format(key)) +
            diff.insert('{!s}'.format(val)))
        self.assertEqual(di.__str__(), expected_str)

    # ContextBlock tests, the diff output is just a chain of ContextBlocks, the
    # bulk of output creation is carried out within the ContextBlock.
    def test_context_banner_is_correct_for_sequences(self):
        '''
        Context banners should contain the information you need the two original
        sequences such that you only get the items contained within the
        displayed context block.
        '''
        seq1 = [0, 1, 2, 3, 0]
        seq2 = [0, 4, 2, 5, 0]
        # the useful context for this diff is the slice 1:4 in both sequences
        s1_start = s2_start = '1'
        s1_end = s2_end = '4'
        diff_obj = diff.diff(seq1, seq2)
        expected_banner = [
            '@@ {}{},{} {}{},{} @@'.format(
                diff.remove('-'), diff.remove(s1_start), diff.remove(s1_end),
                diff.insert('+'), diff.insert(s2_start), diff.insert(s2_end))
        ]
        expected_diff_items = [
            '{} {}'.format(diff.remove('-'), diff.remove('1')),
            '{} {}'.format(diff.insert('+'), diff.insert('4')),
            '{} {}'.format(diff.unchanged(' '), diff.unchanged('2')),
            '{} {}'.format(diff.remove('-'), diff.remove('3')),
            '{} {}'.format(diff.insert('+'), diff.insert('5'))
        ]
        expected_diff_output = '\n'.join(expected_banner + expected_diff_items)
        # expected_diff_output is unicode type, convert to str for comparison
        self.assertEqual(
            diff_obj.context_blocks[0].__str__(), str(expected_diff_output))

    def test_no_context_banner_for_non_sequence(self):
        set1 = {1, 2}
        set2 = {'a', 'b'}
        diff_obj = diff.diff(set1, set2)
        expected_diff_items = [
            '{} {}'.format(diff.remove('-'), diff.remove('1')),
            '{} {}'.format(diff.remove('-'), diff.remove('2')),
            '{} {}'.format(diff.insert('+'), diff.insert('a')),
            '{} {}'.format(diff.insert('+'), diff.insert('b'))
        ]
        # allow the expected output to be unordered
        actual_string = diff_obj.context_blocks[0].__str__()
        actual_items = actual_string.split('\n')
        if sys.version_info.major >= 3:
            self.assertCountEqual(expected_diff_items, actual_items)
        else:
            self.assertItemsEqual(expected_diff_items, actual_items)

    def test_diff_item_is_a_nested_diff(self):
        dict1 = {1: 'ab'}
        dict2 = {1: 'bc'}
        diff_obj = diff.diff(dict1, dict2)
        nested_diff = diff.diff('ab', 'bc', _depth=1)
        diff_item = diff.MappingDiffItem(
            diff.unchanged, 1, diff.changed, nested_diff)
        expected_diff_output = '{} {}'.format(diff.changed(' '), diff_item)
        self.assertEqual(
            diff_obj.context_blocks[0].__str__(), expected_diff_output)

    def test_empty_diff(self):
        set1 = set()
        set2 = set()
        diff_obj = diff.diff(set1, set2)
        expected_diff_output = '{}\n{}'.format(
            diff.unchanged('{!s}('.format(type(set1))),
            diff.unchanged(')'))
        self.assertEqual(diff_obj.__str__(), expected_diff_output)

    # Diff tests
    def test_only_context_blocks_are_displayed(self):
        a = [1, 0, 0, 0, 0, 1]
        b = [2, 0, 0, 0, 0, 2]
        diff_obj = diff.diff(a, b)
        expected_diff_output = [
            diff.unchanged('{!s}('.format(type(a))),
            '@@ {}{},{} {}{},{} @@'.format(
                diff.remove('-'), diff.remove('0'), diff.remove('1'),
                diff.insert('+'), diff.insert('0'), diff.insert('1')),
            '{} {}'.format(diff.remove('-'), diff.remove('1')),
            '{} {}'.format(diff.insert('+'), diff.insert('2')),
            '@@ {}{},{} {}{},{} @@'.format(
                diff.remove('-'), diff.remove('5'), diff.remove('6'),
                diff.insert('+'), diff.insert('5'), diff.insert('6')),
            '{} {}'.format(diff.remove('-'), diff.remove('1')),
            '{} {}'.format(diff.insert('+'), diff.insert('2')),
            diff.unchanged(')')
        ]
        self.assertEqual(diff_obj.__str__(), '\n'.join(expected_diff_output))
