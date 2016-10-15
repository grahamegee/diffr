# The positive cases of patch are extensively tested in test_diff.py because a
# sensible way to validate a diff of two objects is to check that when you apply
# the patch to the first object you get the second.
# Here the testing mainly focuses on patch operations which would fail and some
# of the obscure positive cases. For example you should be able to apply a patch
# to an object that isn't one of the ones involved in the diff under certain
# conditions.
import unittest
from collections import namedtuple, OrderedDict
from copy import deepcopy
from diffr import diff, patch
from diffr.patch import (
    patch_sequence,
    patch_named_tuple,
    patch_mapping,
    patch_ordered_mapping,
    patch_set)


class PatchSequenceTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        a = [1, 2, 3]
        copy_of_a = deepcopy(a)
        b = [3, 2, 1]
        d = diff(a, b)
        self.assertEqual(patch_sequence(a, d), b)
        self.assertEqual(a, copy_of_a)

    def test_removal_does_not_match(self):
        a = 'abcd'
        b = 'bcd'
        c = 'bcd'
        d = diff(a, b)
        self.assertRaises(ValueError, patch_sequence, c, d)

    def test_removal_does_not_exist(self):
        a = 'abcd'
        b = 'abc'
        c = 'abc'
        d = diff(a, b)
        self.assertRaises(IndexError, patch_sequence, c, d)

    def test_change_is_wrong_type(self):
        a = (1, 'abc')
        b = (1, '123')
        c = (1, ['abc'])
        d = diff(a, b)
        self.assertRaises(TypeError, patch_sequence, c, d)

    def test_change_does_not_exist(self):
        a = (1, 'abc')
        b = (1, '123')
        c = (1,)
        d = diff(a, b)
        self.assertRaises(IndexError, patch_sequence, c, d)

    def test_insert_out_of_range(self):
        a = [1, 2, 3]
        b = [1, 2, 3, 4]
        c = [2, 3]
        d = diff(a, b)
        self.assertRaises(IndexError, patch_sequence, c, d)

    def test_can_apply_patch_to_different_object(self):
        a = [0, 1, 2, 3]
        b = [1, 2, 3, 4]
        c = [0, 2, 2, 2]
        d = diff(a, b)
        self.assertEqual(patch_sequence(c, d), [2, 2, 2, 4])

    def test_another_different_object_case(self):
        a = [0, 0, 0]
        b = [0, 1, 0, 1, 0]
        c = [2, 2, 2]
        d = diff(a, b)
        self.assertEqual(patch_sequence(c, d), [2, 1, 2, 1, 2])


class PatchNamedTupleTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        ThreeDPoint = namedtuple('ThreeDPoint', ('x', 'y', 'z'))
        a = ThreeDPoint(1, 2, 3)
        copy_of_a = deepcopy(a)
        b = ThreeDPoint(2, 3, 4)
        d = diff(a, b)
        self.assertEqual(patch_named_tuple(a, d), b)
        self.assertEqual(a, copy_of_a)


class PatchMappingTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        a = {'a': 1}
        copy_of_a = deepcopy(a)
        b = {'a': 2}
        d = diff(a, b)
        self.assertEqual(patch_mapping(a, d), b)
        self.assertEqual(a, copy_of_a)

    def test_removal_does_not_exist(self):
        a = {'a': 1}
        b = {'b': 1}
        c = {'b': 1}
        d = diff(a, b)
        self.assertRaises(KeyError, patch_mapping, c, d)

    def test_removal_does_not_match(self):
        a = {'a': 1}
        b = {'b': 1}
        c = {'a': 2}
        d = diff(a, b)
        self.assertRaises(ValueError, patch_mapping, c, d)

    def test_change_does_not_exist(self):
        a = {'a': 1}
        b = {'a': 2}
        c = {'b': 1}
        d = diff(a, b)
        self.assertRaises(KeyError, patch_mapping, c, d)

    def test_change_does_not_match(self):
        a = {'a': 'a'}
        b = {'a': 'b'}
        c = {'a': 1}
        d = diff(a, b)
        self.assertRaises(TypeError, patch_mapping, c, d)

    def test_unchanged_items_make_no_difference(self):
        a = {'a': 'a'}
        b = {'a': 'b'}
        c = {'a': 'a', 'b': 1, 'c': (3, 4)}
        d = diff(a, b)
        self.assertEqual(patch_mapping(c, d), {'a': 'b', 'b': 1, 'c': (3, 4)})


class PatchOrderedMappingTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        a = OrderedDict({'a': 1})
        copy_of_a = deepcopy(a)
        b = OrderedDict({'a': 2})
        d = diff(a, b)
        self.assertEqual(patch_ordered_mapping(a, d), b)
        self.assertEqual(a, copy_of_a)

    def test_patch_different_target(self):
        a = OrderedDict((('a', 1), ('b', 2), ('c', 3), ('d', 4)))
        b = OrderedDict((('b', 2), ('a', 1), ('c', 3), ('d', 4)))
        d = diff(a, b)
        c = OrderedDict((('a', 1), ('b', 2), ('e', 9), ('f', 10)))
        self.assertEqual(
            patch(c, d),
            OrderedDict((('b', 2), ('a', 1), ('e', 9), ('f', 10)))
        )

    def test_patch_change_does_not_exist_1(self):
        a = OrderedDict((('a', 'a'), ('b', [1])))
        b = OrderedDict((('a', 'a'), ('b', [2])))
        d = diff(a, b)
        c = OrderedDict((('a', 'a'),))
        self.assertRaises(
            ValueError,
            patch, c, d)

    def test_patch_change_does_not_exist_2(self):
        a = OrderedDict((('a', 'a'),))
        b = OrderedDict((('a', 'b'),))
        d = diff(a, b)
        c = OrderedDict((('b', 'b'),))
        self.assertRaises(
            KeyError,
            patch, c, d)

    def test_patch_change_wrong_type(self):
        a = OrderedDict((('a', 'a'),))
        b = OrderedDict((('a', 'b'),))
        d = diff(a, b)
        c = OrderedDict((('a', [1]),))
        self.assertRaises(
            TypeError,
            patch, c, d)

    def test_patch_removal_does_not_exist_1(self):
        a = OrderedDict((('a', 1), ('b', 2)))
        b = OrderedDict((('b', 2),))
        d = diff(a, b)
        self.assertRaises(
            ValueError,
            patch, b, d)

    def test_patch_removal_does_not_exist_2(self):
        a = OrderedDict((('a', 2),))
        b = OrderedDict()
        d = diff(a, b)
        self.assertRaises(
            IndexError,
            patch, b, d)

    def test_patch_insert_out_of_range(self):
        a = OrderedDict((('a', 1), ('b', 2)))
        b = OrderedDict((('a', 1), ('b', 2), ('c', 3)))
        d = diff(a, b)
        c = OrderedDict((('a', 1),))
        self.assertRaises(
            IndexError,
            patch, c, d)


class PatchSetTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        a = {1, 2, 3}
        copy_of_a = deepcopy(a)
        b = {1, 3, 4}
        d = diff(a, b)
        self.assertEqual(patch_set(a, d), b)
        self.assertEqual(a, copy_of_a)

    def test_removals_dont_exist(self):
        a = {1, 2, 3}
        b = {1, 3, 4}
        c = {1, 3}
        d = diff(a, b)
        self.assertRaises(ValueError, patch_set, c, d)


class PatchTests(unittest.TestCase):
    def test_patch_failure_different_types(self):
        Point = namedtuple('Point', ['x', 'y', 'z'])
        ThreeDPoint = namedtuple('ThreeDPoint', ['x', 'y', 'z'])
        a = Point(0, 1, 1)
        b = Point(0, 1, 2)
        c = ThreeDPoint(0, 1, 1)
        d = diff(a, b)
        # FIXME:
        # try as i might I could not get asserRaisesRegexp to actually work. I
        # even used diff to check that my expected error message was correct,
        # it still thought the messages differed. Oh well... the fact that the
        # error is raised is more important than the message.
        self.assertRaises(TypeError, patch, c, d)

    def test_patch_failure_unpatchable_type(self):
        a = [1]
        b = [2]
        c = 1
        d = diff(a, b)
        d._type = int
        self.assertRaises(TypeError, patch, c, d)
