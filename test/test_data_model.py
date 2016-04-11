import unittest
from collections import OrderedDict
from diffr.data_model import (
    sequences_contain_same_items,
    diffs_are_equal,
    Diff, DiffItem, MappingDiffItem)
from diffr.diff import insert, remove, unchanged, diff


class SequencesContainSameItemsTests(unittest.TestCase):
    def test_sequences_only_out_of_order(self):
        a = [1, 2, 'a', {1: 'e'}]
        b = [{1: 'e'}, 2, 1, 'a']
        self.assertTrue(sequences_contain_same_items(a, b))

    def test_sequences_contain_single_difference(self):
        a = [1, 2, 3]
        b = [2, 3, 4]
        self.assertFalse(sequences_contain_same_items(a, b))

    def test_sequence_a_bigger_than_b(self):
        a = [1, 2, 3]
        b = [2, 3]
        self.assertFalse(sequences_contain_same_items(a, b))

    def test_sequence_b_bigger_than_a(self):
        a = [2, 3]
        b = [2, 3, 4]
        self.assertFalse(sequences_contain_same_items(a, b))


class DiffsAreEqualTests(unittest.TestCase):
    def test_sequence_diffs_are_equal(self):
        diff_a = diff([1, 2, 3], [2, 3, 4])
        diff_b = diff([1, 2, 3], [2, 3, 4])
        self.assertTrue(diffs_are_equal(diff_a, diff_b))

    def test_ordered_dicts_are_equal(self):
        d = {1: 'a', 2: 'b', 7: 'c', 3: 'd'}
        diff_a = diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[0])),
            OrderedDict(sorted(d.items(), key=lambda k: k[0])))
        diff_b = diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[0])),
            OrderedDict(sorted(d.items(), key=lambda k: k[0])))
        self.assertTrue(diffs_are_equal(diff_a, diff_b))

    def test_ordered_dicts_are_out_of_order(self):
        d = {1: 'a', 2: 'b', 7: 'c', 3: 'd'}
        diff_a = diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[0])),
            OrderedDict(sorted(d.items(), key=lambda k: k[0])))
        diff_b = diff(
            OrderedDict(sorted(d.items(), key=lambda k: k[1])),
            OrderedDict(sorted(d.items(), key=lambda k: k[1])))
        self.assertFalse(diffs_are_equal(diff_a, diff_b))

    def test_dict_diffs_are_equal(self):
        # these should get seeded differently, fairly regularly in python 3
        # the diffs will be equivalent, but ordering of DiffItems will differ
        d1 = {-1: 'y', 0: 'z', 1: 'a', 2: 'b', 3: 'c', 4: 'e'}
        d2 = {1: 'a', 2: 'b', 3: 'd', 4: 'f'}
        diff_a = diff(d1, d2)
        diff_b = diff(d1, d2)
        self.assertTrue(diffs_are_equal(diff_a, diff_b))

    def test_dict_diffs_not_equal(self):
        d1 = {1: 'a', 2: 'b', 3: 'c'}
        d2 = {1: 'a', 2: 'b', 3: 'd'}
        d3 = {1: 'a', 2: 'b', 3: 'e'}
        diff_a = diff(d1, d2)
        diff_b = diff(d1, d3)
        self.assertFalse(diffs_are_equal(diff_a, diff_b))


class DiffTests(unittest.TestCase):
    def test_contexts_start_and_end_with_modified_items(self):
        # this constraint could change; people may want more context...
        diffs = [
            DiffItem(unchanged, 1),
            DiffItem(insert, 2),
            DiffItem(insert, 2),
            DiffItem(unchanged, 1)]
        diff_obj = Diff(list, diffs)
        self.assertEqual(
            diff_obj._create_context_markers(), [(1, 3)])

    def test_context_limit_is_adjustable(self):
        '''The default context limit is 3, if we adjust it to 1 we expect a new
           new context to be started if there is a gap of 2'''
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 0),
            DiffItem(unchanged, 0),
            DiffItem(remove, 1)]
        diff_obj = Diff(list, diffs, context_limit=1)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 1), (3, 4)])

    def test_context_limit_max(self):
        '''Once a context is started,so long as the number of contiguous
           unchanged items doesn't exceed the context limit, they remain part of
           the context'''
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 0),
            DiffItem(unchanged, 0),
            DiffItem(remove, 1)]
        diff_obj = Diff(list, diffs, context_limit=2)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 4)])

    def test_context_limit_max_plus_one(self):
        '''Once a context is started if the number of contiguous unchanged items
           exceeds the context limit the context is cut off at the last modified
           item and a new context is started'''
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 0),
            DiffItem(unchanged, 0),
            DiffItem(unchanged, 0),
            DiffItem(remove, 1)]
        diff_obj = Diff(list, diffs, context_limit=2)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 1), (4, 5)])

    def test_context_not_finished_by_end_of_diffs_list(self):
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 0)]
        diff_obj = Diff(list, diffs, context_limit=2)
        self.assertEqual(
            diff_obj._create_context_markers(), [(0, 1)])

    # context block generation
    def test_context_block_generation(self):
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 0),
            DiffItem(unchanged, 0),
            DiffItem(remove, 1)]
        expected = [
            Diff.ContextBlock(list, [diffs[0]]),
            Diff.ContextBlock(list, [diffs[3]])]
        diff_obj = Diff(list, diffs, context_limit=1)
        diff_obj.create_context_blocks()
        self.assertEqual(
            diff_obj.context_blocks, expected)


class DiffComparisonTests(unittest.TestCase):
    def setUp(self):
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 2),
            DiffItem(unchanged, 2),
            DiffItem(remove, 3)
        ]
        self.base_diff = Diff(list, diffs, context_limit=1, depth=0)
        self.base_diff.create_context_blocks()
        self.expected_diff = Diff(list, diffs, context_limit=1, depth=0)
        self.expected_diff.create_context_blocks()

    def test_diffs_compare_equal(self):
        self.assertEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_type(self):
        self.expected_diff.type = tuple
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_context_limit(self):
        self.expected_diff.context_limit = 2
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_with_different_depths_compare_equal(self):
        d1 = diff([1, 2, 3], [2, 3])
        d2 = diff({'a': [1, 2, 3]}, {'a': [2, 3]})
        self.assertEqual(d1, d2.diffs[0].value)

    def test_diffs_differ_by_diffs(self):
        self.expected_diff.diffs = []
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_context_blocks(self):
        self.expected_diff.context_blocks = []
        self.assertNotEqual(self.base_diff, self.expected_diff)


class DiffContextBlockTests(unittest.TestCase):
    def setUp(self):
        self.base_context_diffs = [
            DiffItem(insert, 'a', (0, 1, 1, 2)),
            DiffItem(unchanged, 'b', (1, 2, 2, 3)),
            DiffItem(remove, 'c', (2, 3, 3, 4))]
        self.base_context_block = Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs)

    def test_ContextBlock_context_is_correct(self):
        self.assertEqual(self.base_context_block.context, (0, 3, 1, 4))

    # test rich comparison methods
    def test_ContextBlocks_equal(self):
        equal_context_block = Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs)
        self.assertEqual(
            self.base_context_block, equal_context_block)

    def test_ContextBlocks_have_different_diffs(self):
        context_diffs = [
            d for d in self.base_context_diffs if d.state is not unchanged]
        different_context_block = Diff(list, context_diffs).ContextBlock(
            list, context_diffs)
        self.assertNotEqual(
            self.base_context_block, different_context_block)

    def test_ContextBlocks_have_different_contexts(self):
        self.base_context_diffs[0].context = (2, 3, 4, 5)
        different_context_block = Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs)
        self.assertNotEqual(
            self.base_context_block, different_context_block)

    def test_ContextBlocks_have_different_depths(self):
        different_context_block = Diff(
            list, self.base_context_diffs).ContextBlock(
                list, self.base_context_diffs, depth=1)
        self.assertEqual(
            self.base_context_block, different_context_block)


class DiffItemTests(unittest.TestCase):
    def setUp(self):
        self.base_diff_item = DiffItem(insert, 1)

    def test_equal_DiffItems(self):
        self.assertEqual(
            self.base_diff_item, DiffItem(insert, 1))

    def test_diff_items_differ_by_state(self):
        self.assertNotEqual(
            self.base_diff_item, DiffItem(remove, 1))

    def test_diff_items_differ_by_context(self):
        self.assertNotEqual(
            self.base_diff_item, DiffItem(insert, 1, context=1))

    def test_diff_items_differ_by_item(self):
        self.assertNotEqual(
            self.base_diff_item, DiffItem(insert, 2))


class MappingDiffItemTests(unittest.TestCase):
    def setUp(self):
        self.base_diff_item = MappingDiffItem(
            insert, 'a', insert, 1)

    def test_equal_MappingDiffItems(self):
        self.assertEqual(
            self.base_diff_item, MappingDiffItem(
                insert, 'a', insert, 1))

    def test_MappingDiffItems_differ_by_key_state(self):
        self.assertNotEqual(
            self.base_diff_item, MappingDiffItem(
                unchanged, 'a', insert, 1))

    def test_MappingDiffItems_differ_by_key(self):
        self.assertNotEqual(
            self.base_diff_item, MappingDiffItem(
                insert, 'b', insert, 1))

    def test_MappingDiffItems_differ_by_state(self):
        self.assertNotEqual(
            self.base_diff_item, MappingDiffItem(
                insert, 'a', remove, 1))

    def test_MappingDiffItems_differ_by_value(self):
        self.assertNotEqual(
            self.base_diff_item, MappingDiffItem(
                insert, 'a', insert, 2))
