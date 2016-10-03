import unittest
from collections import OrderedDict
from diffr.data_model import (
    sequences_contain_same_items,
    recursively_set_context_limit,
    adjusted_context_limit,
    context_slice,
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
    def test_len_diff(self):
        self.assertEqual(len(diff([1, 2], [1, 2])), 2)

    def test_diff_evaluates_false_when_empty(self):
        self.assertFalse(bool(Diff(set, [])))

    def test_diff_evaluates_true_when_contain_non_unchanged_items(self):
        self.assertTrue(bool(diff('baaaaaaa', 'aaaaaaaa')))

    def test_diff_evaluates_false_when_all_items_are_unchanged(self):
        self.assertFalse(bool(diff({1: [1, 2]}, {1: [1, 2]})))

    def test_diff_slicing(self):
        d = diff('aabcdef', 'abcdef')
        s = d[1:]
        self.assertEqual(s, Diff(str, d.diffs[1:]))

    def test_diff_index(self):
        d = diff('aabcdef', 'abcdef')
        i = 0
        self.assertEqual(d[i], d.diffs[i])

    def test_getattr_fail(self):
        d = diff('aaa', 'bbb')
        with self.assertRaises(TypeError):
            d['a']

    def test_iterate_over_diff(self):
        d = diff([1, 2, 3, 4], [2, 3, 4, 5])
        diff_items = [di for di in d]
        self.assertEqual(tuple(diff_items), d.diffs)


class DiffDisplayTests(unittest.TestCase):
    def test_context_slice_empty_diff(self):
        d = diff(set(), set())
        self.assertEqual(context_slice(d, 2), [])

    def test_context_slice_no_differences(self):
        d = diff({1, 2, 3}, {1, 2, 3})
        self.assertEqual(context_slice(d.diffs, 2), [])

    def test_context_slice_one_changed_item(self):
        # the loop in get_context_slice_indices is skipped and "not slices"
        # branch is reached
        d = diff('-a', '-')
        self.assertEqual(
            context_slice(d.diffs, 1),
            [(
                DiffItem(unchanged, '-', (0, 1, 0, 1)),
                DiffItem(remove, 'a', (1, 2, 1, 1))
            )])

    def test_context_slice_two_changed_items_with_a_gap(self):
        # the loop in get_context_slice_indices is skipped and "not slices"
        # branch is reached
        d = diff('a--b', '--')
        self.assertEqual(
            context_slice(d.diffs, 0),
            [
                (DiffItem(remove, 'a', (0, 1, 0, 0)),),
                (DiffItem(remove, 'b', (3, 4, 2, 2)),)
            ])

    def test_context_slice_substitution_in_the_middle(self):
        d = diff('---a---', '---b---')
        self.assertEqual(
            context_slice(d.diffs, 1),
            [(
                DiffItem(unchanged, '-', (2, 3, 2, 3)),
                DiffItem(remove, 'a', (3, 4, 3, 3)),
                DiffItem(insert, 'b', (4, 4, 3, 4)),
                DiffItem(unchanged, '-', (4, 5, 4, 5))
            )])

    def test_context_slice_two_substitutions_with_gap(self):
        d = diff('---a---x', '---b---y')
        self.assertEqual(
            context_slice(d.diffs, 1),
            [
                (
                    DiffItem(unchanged, '-', (2, 3, 2, 3)),
                    DiffItem(remove, 'a', (3, 4, 3, 3)),
                    DiffItem(insert, 'b', (4, 4, 3, 4)),
                    DiffItem(unchanged, '-', (4, 5, 4, 5))
                ),
                (
                    DiffItem(unchanged, '-', (6, 7, 6, 7)),
                    DiffItem(remove, 'x', (7, 8, 7, 7)),
                    DiffItem(insert, 'y', (8, 8, 7, 8))
                ),
            ])


class AdjustContextLimitTests(unittest.TestCase):
    def test_recursively_setting_context(self):
        a = [0, 0, {1: 'aa', 2: 2}]
        b = [0, 0, {1: 'ab', 2: 2}]
        d = diff(a, b)
        self.assertEqual(d.context_limit, None)
        self.assertEqual(d[2].item.context_limit, None)
        self.assertEqual(d[2].item[0].value.context_limit, None)
        recursively_set_context_limit(d, 0)
        self.assertEqual(d.context_limit, 0)
        self.assertEqual(d[2].item.context_limit, 0)
        self.assertEqual(d[2].item[0].value.context_limit, 0)

    def test_adjusted_context_limit(self):
        # Yeah possibly unnecessary. check that a context manager behaves like
        # a context manager, but no harm in more tests
        a = '---a---'
        b = '---b---'
        d = diff(a, b)
        self.assertEqual(d.context_limit, None)
        with adjusted_context_limit(d, 2):
            self.assertEqual(d.context_limit, 2)
        self.assertEqual(d.context_limit, None)


class DiffComparisonTests(unittest.TestCase):
    def setUp(self):
        diffs = [
            DiffItem(insert, 1),
            DiffItem(unchanged, 2),
            DiffItem(unchanged, 2),
            DiffItem(remove, 3)
        ]
        self.base_diff = Diff(list, diffs, depth=0)
        self.expected_diff = Diff(list, diffs, depth=0)

    def test_diffs_compare_equal(self):
        self.assertEqual(self.base_diff, self.expected_diff)

    def test_diffs_differ_by_type(self):
        self.expected_diff.type = tuple
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_with_different_depths_compare_equal(self):
        d1 = diff([1, 2, 3], [2, 3])
        d2 = diff({'a': [1, 2, 3]}, {'a': [2, 3]})
        self.assertEqual(d1, d2.diffs[0].value)

    def test_diffs_differ_by_diffs(self):
        self.expected_diff.diffs = []
        self.assertNotEqual(self.base_diff, self.expected_diff)


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
