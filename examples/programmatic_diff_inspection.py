from diffr import diff, Diff, unchanged, insert, remove, changed

a = 'change1 same change2'
b = 'modify1 same modify2'
d = diff(a, b)

print('---------------------------------------------------------')
print('The full diff\n')
# the displayed diff
print(d)
print('---------------------------------------------------------')
# the whole diff
print('can access the full diff\n')
print(''.join([str(i) for i in d]))
print('---------------------------------------------------------')
print('diff item states\n')
# inspect diff item state
print('item {} at index {} is a removal: {}'.format(
    str(d[0]), 0, d[0].state == remove)
)
print('---------------------------------------------------------')
print('Breaking diffs up into managable chunks')
print('diff item context\n')
print(
    'middle unchanged portion of diff = "{}"'.format(
        ''.join([str(i) for i in d[13:19]])
    )
)
print('---------------------------------------------------------')
print('use context attribute to slice the data structures\n')
a_start, _, b_start, _ = d[13].context
_, a_end, _, b_end = d[18].context
print(
    'a context slice: "{}", b context slice: "{}"'.format(
        a[a_start:a_end], b[b_start:b_end]))
print('---------------------------------------------------------')
print('diff comparison\n')
a = {'a': 3}
b = {'a': 4}
d_nested = diff([1, a], [1, b])
d = diff(a, b)
print(d)
print(d_nested)
print('Item 1 of the nested diff == the diff: {}'.format(d == d_nested[1].item))
print('---------------------------------------------------------')
print('filter on inserts')
a = 'a' * 5 + 'b' * 5
b = 'b' * 5 + 'a' * 5
print(''.join([str(i) for i in diff(a, b) if i.state == insert]))
print('filter on removals')
print(''.join([str(i) for i in diff(a, b) if i.state == remove]))
print('---------------------------------------------------------')
print('Diff evaluates false if it\'s empty or if there are no changes')
empty_diff = diff([], [])
diff_with_no_changes = diff('abc', 'abc')
print('bool({}) == {}'.format(empty_diff, bool(empty_diff)))
print('bool({}) == {}'.format(diff_with_no_changes, bool(diff_with_no_changes)))
print('---------------------------------------------------------')
print('Inspecting diff properties')
a = {'a': 3}
b = {'a': 4}
d_nested = diff([1, a], [1, b])
print('Depth of outer diff is {}'.format(d_nested.depth))
print('Depth of inner diff is {}'.format(d_nested[1].item.depth))
print('---------------------------------------------------------')
print('Type of outer diff is {}'.format(d_nested.type))
print('Type of inner diff is {}'.format(d_nested[1].item.type))
