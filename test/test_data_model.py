import sys
import unittest
from collections import OrderedDict
from diffr.data_model import (
    term,
    sequences_contain_same_items,
    recursively_set_context_limit,
    adjusted_context_limit,
    context_slice,
    diffs_are_equal,
    Diff, DiffItem, MappingDiffItem)
from diffr.diff import insert, remove, unchanged, changed, diff


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
        self.assertEqual(s, Diff(str, d._diffs[1:]))

    def test_diff_index(self):
        d = diff('aabcdef', 'abcdef')
        i = 0
        self.assertEqual(d[i], d._diffs[i])

    def test_getattr_fail(self):
        d = diff('aaa', 'bbb')
        with self.assertRaises(TypeError):
            d['a']

    def test_iterate_over_diff(self):
        d = diff([1, 2, 3, 4], [2, 3, 4, 5])
        diff_items = [di for di in d]
        self.assertEqual(tuple(diff_items), d._diffs)


class DiffDisplayTests(unittest.TestCase):
    def test_context_slice_empty_diff(self):
        d = diff(set(), set())
        self.assertEqual(context_slice(d, 2), [])

    def test_context_slice_no_differences(self):
        d = diff({1, 2, 3}, {1, 2, 3})
        self.assertEqual(context_slice(d._diffs, 2), [])

    def test_context_slice_one_changed_item(self):
        # the loop in get_context_slice_indices is skipped and "not slices"
        # branch is reached
        d = diff('-a', '-')
        self.assertEqual(
            context_slice(d._diffs, 1),
            [(
                DiffItem(unchanged, '-', (0, 1, 0, 1)),
                DiffItem(remove, 'a', (1, 2, 1, 1))
            )])

    def test_context_slice_two_changed_items_with_a_gap(self):
        # the loop in get_context_slice_indices is skipped and "not slices"
        # branch is reached
        d = diff('a--b', '--')
        self.assertEqual(
            context_slice(d._diffs, 0),
            [
                (DiffItem(remove, 'a', (0, 1, 0, 0)),),
                (DiffItem(remove, 'b', (3, 4, 2, 2)),)
            ])

    def test_context_slice_substitution_in_the_middle(self):
        d = diff('---a---', '---b---')
        self.assertEqual(
            context_slice(d._diffs, 1),
            [(
                DiffItem(unchanged, '-', (2, 3, 2, 3)),
                DiffItem(remove, 'a', (3, 4, 3, 3)),
                DiffItem(insert, 'b', (4, 4, 3, 4)),
                DiffItem(unchanged, '-', (4, 5, 4, 5))
            )])

    def test_context_slice_two_substitutions_with_gap(self):
        d = diff('---a---x', '---b---y')
        self.assertEqual(
            context_slice(d._diffs, 1),
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

    def test_diff_item_str(self):
        item = 'a'
        di = DiffItem(remove, item)
        expected_str = remove('{}'.format(item))
        self.assertEqual(str(di), expected_str)

    def test_mapping_diff_item_str(self):
        key = 'a'
        val = [1, 2, 3]
        di = MappingDiffItem(
            unchanged, key, insert, val)
        expected_str = (
            unchanged('{!s}: '.format(key)) +
            insert('{!s}'.format(val)))
        self.assertEqual(str(di), expected_str)

    def test_context_banner_is_correct_for_sequences(self):
        '''
        Context banners should contain the information you need the two original
        sequences such that you only get the items contained within the
        displayed context block.
        '''
        seq1 = [1, 2, 3]
        seq2 = [4, 2, 5]
        # the useful context for this diff is the slice 1:4 in both sequences
        s1_start = s2_start = '0'
        s1_end = s2_end = '3'
        diff_obj = diff(seq1, seq2)
        start = [unchanged('{}('.format(type([]).__name__))]
        expected_banner = [
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove(s1_start), remove(s1_end),
                insert('+'), insert(s2_start), insert(s2_end))
        ]
        expected_diff_items = [
            '{} {}'.format(remove('-'), remove('1')),
            '{} {}'.format(insert('+'), insert('4')),
            '{} {}'.format(unchanged(' '), unchanged('2')),
            '{} {}'.format(remove('-'), remove('3')),
            '{} {}'.format(insert('+'), insert('5'))
        ]
        end = [unchanged(')')]
        expected_diff_output = '\n'.join(
            start + expected_banner + expected_diff_items + end)
        self.assertEqual(
            str(diff_obj), str(expected_diff_output))

    def test_no_context_banner_for_non_sequence(self):
        set1 = {1, 2}
        set2 = {'a', 'b'}
        diff_obj = diff(set1, set2)
        expected_diff_items = [
            '{} {}'.format(remove('-'), remove('1')),
            '{} {}'.format(remove('-'), remove('2')),
            '{} {}'.format(insert('+'), insert('a')),
            '{} {}'.format(insert('+'), insert('b'))
        ]
        # allow the expected output to be unordered
        actual_string = str(diff_obj)
        actual_items = actual_string.split('\n')
        self.assertEqual(
            unchanged('{}('.format(type(set()).__name__)), actual_items[0])
        self.assertEqual(unchanged(')'), actual_items[-1])
        # strip off the type information at the top and bottom
        if sys.version_info.major >= 3:
            self.assertCountEqual(expected_diff_items, actual_items[1:-1])
        else:
            self.assertItemsEqual(expected_diff_items, actual_items[1:-1])

    def test_empty_diff(self):
        set1 = set()
        set2 = set()
        diff_obj = diff(set1, set2)
        expected_diff_output = '{}{}'.format(
            unchanged('{!s}('.format(type(set1).__name__)),
            unchanged(')'))
        self.assertEqual(str(diff_obj), expected_diff_output)

    def test_strings_display_on_single_line(self):
        a = 'this'
        b = 'that'
        d = diff(a, b)
        expected_str = [
            unchanged('{!s}('.format(type(a).__name__)),
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('0'), remove('4'),
                insert('+'), insert('0'), insert('4')),
            ' {}{}{}{}{}{}'.format(
                unchanged(' '), unchanged(' '), remove('-'), remove('-'),
                insert('+'), insert('+')),
            ' {}{}{}{}{}{}'.format(
                unchanged('t'), unchanged('h'), remove('i'), remove('s'),
                insert('a'), insert('t')),
            unchanged(')')
        ]
        self.assertEqual(str(d), '\n'.join(expected_str))

    def test_string_diff_wraps_after_term_width(self):
        a = ''
        b = 'a' * term.width
        d = diff(a, b)
        expected_str = [
            unchanged('{!s}('.format(type(a).__name__)),
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('0'), remove('0'),
                insert('+'), insert('0'), insert('{}'.format(term.width))),
            ' ' + ('{}'.format(insert('+')) * (term.width - 1)),
            ' ' + ('{}'.format(insert('a')) * (term.width - 1)),
            ' {}'.format(insert('+')),
            ' {}'.format(insert('a')),
            unchanged(')')
        ]
        self.assertEqual(str(d), '\n'.join(expected_str))

    def test_string_is_term_width(self):
        a = ''
        b = 'a' * (term.width - 1)
        d = diff(a, b)
        expected_str = [
            unchanged('{!s}('.format(type(a).__name__)),
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('0'), remove('0'),
                insert('+'), insert('0'), insert('{}'.format(term.width - 1))),
            ' ' + ('{}'.format(insert('+')) * (term.width - 1)),
            ' ' + ('{}'.format(insert('a')) * (term.width - 1)),
            unchanged(')')
        ]
        self.assertEqual(str(d), '\n'.join(expected_str))


class DiffFormattingTests(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.nested_a = [0, 0, 0, '---a---', 0, 0, 0, 1, 0]
        self.nested_b = [0, 0, 0, '---x---', 0, 0, 0, 2, 0]
        self.diff_obj = diff(self.nested_a, self.nested_b)

    def test_valid_format_spec_adjusts_diff_display(self):
        '''
        When we specify a context specifier with 'cn' where n is an int, the
        the diff should focus display on only the changes. Allowing only n
        unchanged items to be displaye either side of a remove or insert.
        The context banners should be updated (and inserted) to make it clear
        that we have broken up the diff into chunks that focus around change.
        '''
        indent = '   '
        outer_start = [unchanged('{}('.format(type([]).__name__))]
        outer_banner_1 = [
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('2'), remove('5'),
                insert('+'), insert('2'), insert('5'))
        ]
        inner_start = [unchanged('{}('.format(type('').__name__))]
        inner_banner = [
            indent + '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('2'), remove('5'),
                insert('+'), insert('2'), insert('5'))
        ]
        inner_items = [
            indent + ' {}{}{}{}'.format(
                unchanged(' '), remove('-'), insert('+'), unchanged(' ')),
            indent + ' {}{}{}{}'.format(
                unchanged('-'), remove('a'), insert('x'), unchanged('-'))
        ]
        inner_end = [indent + unchanged(')')]
        outer_items_1 = [
            '{} {}'.format(unchanged(' '), unchanged('0')),
            '{} {}'.format(
                changed(' '),
                changed(
                    '\n'.join(
                        inner_start + inner_banner + inner_items + inner_end))),
            '{} {}'.format(unchanged(' '), unchanged('0'))
        ]
        outer_banner_2 = [
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('6'), remove('9'),
                insert('+'), insert('6'), insert('9'))
        ]
        outer_items_2 = [
            '{} {}'.format(unchanged(' '), unchanged('0')),
            '{} {}'.format(remove('-'), remove('1')),
            '{} {}'.format(insert('+'), insert('2')),
            '{} {}'.format(unchanged(' '), unchanged('0'))
        ]
        outer_end = [unchanged(')')]
        expected_display = '\n'.join(
            outer_start + outer_banner_1 + outer_items_1 + outer_banner_2 +
            outer_items_2 + outer_end)
        self.assertEqual(str(format(self.diff_obj, '1c')), expected_display)

    def test_no_format_specifier_displays_full_diff(self):
        self.assertEqual(str(self.diff_obj), format(self.diff_obj))

    def test_invalid_format_spec_reverts_to_full_diff(self):
        self.assertEqual(str(self.diff_obj), format(self.diff_obj, '%d'))

    def test_format_a_diff_slice(self):
        outer_start = [unchanged('{}('.format(type([]).__name__))]
        outer_banner = [
            '@@ {}{},{} {}{},{} @@'.format(
                remove('-'), remove('3'), remove('4'),
                insert('+'), insert('3'), insert('4'))
        ]
        slice_output = [
            '{} {}'.format(
                changed(' '),
                changed(format(diff('---a---', '---x---', _depth=1), '1c'))
            )
        ]
        outer_end = [unchanged(')')]
        expected_display = '\n'.join(
            outer_start + outer_banner + slice_output + outer_end)
        self.assertEqual(format(self.diff_obj[3:4], '1c'), expected_display)

    def test_format_diff_index(self):
        expected_display = changed(
            format(diff('---a---', '---x---', _depth=1), '1c'))
        self.assertEqual(format(self.diff_obj[3], '1c'), expected_display)


class AdjustContextLimitTests(unittest.TestCase):
    def test_recursively_setting_context(self):
        a = [0, 0, {1: 'aa', 2: 2}]
        b = [0, 0, {1: 'ab', 2: 2}]
        d = diff(a, b)
        self.assertEqual(d._context_limit, None)
        self.assertEqual(d[2].item._context_limit, None)
        self.assertEqual(d[2].item[0].value._context_limit, None)
        recursively_set_context_limit(d, 0)
        self.assertEqual(d._context_limit, 0)
        self.assertEqual(d[2].item._context_limit, 0)
        self.assertEqual(d[2].item[0].value._context_limit, 0)

    def test_adjusted_context_limit(self):
        # Yeah possibly unnecessary. check that a context manager behaves like
        # a context manager, but no harm in more tests
        a = '---a---'
        b = '---b---'
        d = diff(a, b)
        self.assertEqual(d._context_limit, None)
        with adjusted_context_limit(d, 2):
            self.assertEqual(d._context_limit, 2)
        self.assertEqual(d._context_limit, None)


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
        self.expected_diff._type = tuple
        self.assertNotEqual(self.base_diff, self.expected_diff)

    def test_diffs_with_different_depths_compare_equal(self):
        d1 = diff([1, 2, 3], [2, 3])
        d2 = diff({'a': [1, 2, 3]}, {'a': [2, 3]})
        self.assertEqual(d1, d2[0].value)

    def test_diffs_differ_by_diffs(self):
        self.expected_diff._diffs = []
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

    def test_format_a_diff_item_containing_a_diff(self):
        d = diff('--a--', '--b--')
        diff_item = DiffItem(changed, d)
        self.assertEqual(
            format(diff_item, '1c'), changed(format(d, '1c')))

    def test_format_a_diff_item_not_containing_a_diff(self):
        diff_item = DiffItem(insert, 0)
        self.assertRaises(
            ValueError, format, diff_item, '1c')


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

    def test_format_a_diff_item_containing_a_diff(self):
        d = diff('--a--', '--b--')
        diff_item = MappingDiffItem(unchanged, 1, changed, d)
        self.assertEqual(
            format(diff_item, '1c'),
            '{}: {}'.format(unchanged(str(1)), changed(format(d, '1c'))))

    def test_format_a_diff_item_not_containing_a_diff(self):
        diff_item = MappingDiffItem(insert, 1, insert, 'a')
        self.assertRaises(
            ValueError, format, diff_item, '1c')

    def test_dont_use_context_format_specifier(self):
        d = diff('--a--', '--b--')
        diff_item = MappingDiffItem(unchanged, 1, changed, d)
        self.assertEqual(
            format(diff_item, '2f'),
            '{}: {}'.format(unchanged(str(1)), changed(str(d))))
