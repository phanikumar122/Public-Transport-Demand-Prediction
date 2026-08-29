"""Fix all Unicode box-drawing characters across the project to ASCII equivalents."""
import pathlib

FILES = [
    r'src\warehouse\load.py',
    r'src\ml\tune.py',
    r'src\etl\railways.py',
    r'src\etl\pipeline.py',
    r'src\etl\flights.py',
    r'src\mining\clustering.py',
    r'src\mining\anomaly_detection.py',
]

REPLACEMENTS = [
    ('\u2550', '='),
    ('\u2554', '+'), ('\u2557', '+'), ('\u255a', '+'), ('\u255d', '+'),
    ('\u2551', '|'), ('\u2560', '+'), ('\u2563', '+'), ('\u2566', '+'),
    ('\u2569', '+'), ('\u256c', '+'), ('\u2588', '#'),
    ('\u2192', '->'), ('\u2190', '<-'),
    ('\u2713', 'OK'), ('\u2717', 'FAIL'),
    ('\u2014', '--'), ('\u2013', '-'),
    ('\u00d7', 'x'),
    ('\u2500', '-'), ('\u2502', '|'),
    ('\u250c', '+'), ('\u2510', '+'), ('\u2514', '+'), ('\u2518', '+'),
    ('\u251c', '+'), ('\u2524', '+'), ('\u252c', '+'), ('\u2534', '+'),
    ('\u253c', '+'), ('\u2605', '*'), ('\u2606', '*'), ('\u2022', '-'),
    ('\u25ba', '>'),
    ('\u2019', "'"), ('\u2018', "'"),
    ('\u201c', '"'), ('\u201d', '"'),
]

for rel in FILES:
    p = pathlib.Path(rel)
    if not p.exists():
        print(f'MISSING: {rel}')
        continue
    text = p.read_text(encoding='utf-8')
    new_text = text
    for bad, good in REPLACEMENTS:
        new_text = new_text.replace(bad, good)
    if new_text != text:
        p.write_text(new_text, encoding='utf-8')
        print(f'Fixed: {rel}')
    else:
        print(f'Clean: {rel}')

print('Done.')
