from differ import diff, Diff, unchanged, insert, remove, changed

a = 'change1 same change2'
b = 'modify1 same modify2'
d = diff(a, b)

print('---------------------------------------------------------')
print('The full diff\n')
# the displayed diff
print(d)
print('---------------------------------------------------------')

# the whole diff
print('---------------------------------------------------------')
print('can access the full diff\n')
print(''.join([str(i) for i in d.diffs]))
print('---------------------------------------------------------')

print('---------------------------------------------------------')
print('diff item states\n')
# inspect diff item state
print('item {} at index {} is a removal: {}'.format(
    str(d.diffs[0]),
    0,
    d.diffs[0].state == remove)
)
print('---------------------------------------------------------')

print('---------------------------------------------------------')
print('diff item context\n')
print(
    'middle unchanged portion of diff = "{}"'.format(
        ''.join([str(i) for i in d.diffs[13:19]])
    )
)
print('---------------------------------------------------------')
print('use context attribute to slice the data structures\n')
a_start, _, b_start, _ = d.diffs[13].context
_, a_end, _, b_end = d.diffs[18].context
print(
    'a context slice: "{}", b context slice: "{}"'.format(
        a[a_start:a_end], b[b_start:b_end]))
print('---------------------------------------------------------')
print('inspect context blocks\n')
cb1, cb2 = d.context_blocks
a1_start, a1_end, b1_start, b1_end = cb1.context
a2_start, a2_end, b2_start, b2_end = cb2.context
print(
    'first context block: a = "{}", b = "{}"'.format(
        a[a1_start: a1_end], b[b1_start: b1_end]
    )
)
print(
    'last context block: a = "{}", b = "{}"'.format(
        a[a2_start: a2_end], b[b2_start: b2_end]
    )
)
print('---------------------------------------------------------')
print('diff comparison\n')
a = {'a' : 3}
b = {'a' : 4}
d_nested = diff([1, a], [1, b])
d = diff(a, b)
print(d)
print(d_nested)
print(d == d_nested.diffs[1].item)
print('---------------------------------------------------------')
