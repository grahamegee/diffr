from differ import diff
from collections import namedtuple, OrderedDict

# lists
print(diff([1, 2, 3], [4]))

# tuples
print(diff((1, 1, 1), (1, 2, 1)))

# strings
print(diff('michael', 'paul'))

# sets (remeber sets are unordered)
print(diff({1, 2, 'a', 'b'}, {'a', 'c', 1, 2}))

# dict
print(diff({'a': 1, 'b': 2}, {'a': 2, 'c': 2}))

# OrderedDict
print(
    diff(OrderedDict((('a', 1), ('b', 2))), OrderedDict((('b', 2), ('a', 1))))
)

#namedtuple
Point = namedtuple('Point', ['x', 'y'])
print(diff(Point(1, 2), Point(0,1)))

#nesting
print(
    diff(
        {1: ['hello', 'there'], 2: {1, 2, 3}},
        {1: ['hi', 'there'], 2: {2, 3, 4}}
    )
)
