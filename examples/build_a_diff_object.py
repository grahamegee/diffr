from differ import unchanged, remove, insert, DiffItem, Diff, patch

d = Diff(
    set,
    [DiffItem(remove, 'a'), DiffItem(unchanged, 'b'), DiffItem(insert, 'c')]
)
print(d)

d = Diff(
    str,
    [
        DiffItem(unchanged, 'h', (0, 1, 0, 1)),
        DiffItem(remove, 'i', (1, 2, 1, 1)),
        DiffItem(insert, 'e', (2, 2, 1, 2)),
        DiffItem(insert, 'l', (2, 2, 2, 3)),
        DiffItem(insert, 'l', (2, 2, 3, 4)),
        DiffItem(insert, 'o', (2, 2, 4, 5))
    ]
)
print(d)
print(patch('hi', d))
