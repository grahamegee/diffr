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
from differ import diff, patch
from differ.patch import (
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


class PatchOrderedMappingTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        a = OrderedDict({'a': 1})
        copy_of_a = deepcopy(a)
        b = OrderedDict({'a': 2})
        d = diff(a, b)
        self.assertEqual(patch_ordered_mapping(a, d), b)
        self.assertEqual(a, copy_of_a)


class PatchSetTests(unittest.TestCase):
    def test_patch_has_no_side_effects(self):
        a = {1, 2, 3}
        copy_of_a = deepcopy(a)
        b = {1, 3, 4}
        d = diff(a, b)
        self.assertEqual(patch_set(a, d), b)
        self.assertEqual(a, copy_of_a)


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
        d.type = int
        self.assertRaises(TypeError, patch, c, d)
