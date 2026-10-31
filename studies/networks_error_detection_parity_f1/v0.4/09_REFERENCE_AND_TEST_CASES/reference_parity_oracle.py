"""Reference F1 parity verifiers, purely mathematical, not a learner grader.

These functions prove facts about each GENERATED INSTANCE. They do not decide
whether natural-language wording is semantically equivalent or how SOLO is scored.
"""
from itertools import combinations

def parity(bits):
    bits = tuple(bits)
    if not all(v in (0, 1) for v in bits):
        raise ValueError("binary bits only")
    return sum(bits) % 2

def sender_bit(data_bits, convention="even"):
    if convention not in ("even", "odd"):
        raise ValueError("unknown parity convention")
    return parity(data_bits) ^ (convention == "odd")

def make_frame(data_bits, convention="even"):
    return tuple(data_bits) + (int(sender_bit(data_bits, convention)),)

def receiver_pass(received_frame, convention="even"):
    if convention not in ("even", "odd"):
        raise ValueError("unknown convention")
    return parity(received_frame) == int(convention == "odd")

def flip_positions(bits, positions):
    result=list(bits)
    if len(set(positions))!=len(tuple(positions)):
        raise ValueError("no repeated flip coordinates")
    for i in positions:
        if not 0<=i<len(result): raise ValueError("bad position")
        result[i] ^= 1
    return tuple(result)

def full_grid(data):
    """Full row/column even-parity construction, including bottom-right corner."""
    if not data or not data[0] or len(set(map(len,data)))!=1:
        raise ValueError("rectangular nonempty grid needed")
    data=[list(row) for row in data]
    for row in data:parity(row)
    extended=[row+[parity(row)] for row in data]
    bottom=[parity([row[c] for row in extended]) for c in range(len(extended[0]))]
    return tuple(tuple(row) for row in extended+[bottom])

def grid_syndrome(block, flipped_positions=()):
    """Calculate all failing row/column IDs of a VALID full 2D block after flips."""
    rows=len(block);cols=len(block[0])
    if not all(len(r)==cols for r in block): raise ValueError("ragged grid")
    if any(parity(r) for r in block): raise ValueError("base must satisfy row checks")
    if any(parity([block[r][c] for r in range(rows)]) for c in range(cols)):
        raise ValueError("base must satisfy column checks")
    actual=[list(row) for row in block]
    flips=list(flipped_positions)
    if len(set(flips))!=len(flips):raise ValueError("duplicate coordinates")
    for r,c in flips:
        if not (0<=r<rows and 0<=c<cols):raise ValueError("bad coordinate")
        actual[r][c]^=1
    failing_rows=tuple(r for r in range(rows) if parity(actual[r]))
    failing_cols=tuple(c for c in range(cols) if parity([actual[r][c] for r in range(rows)]))
    return {'failing_rows':failing_rows,'failing_cols':failing_cols,'passes':not(failing_rows or failing_cols)}

def group_syndrome(data_len, groups, flipped_data_positions):
    """Group parity for data-only flips. Check-bit errors are excluded by assumption."""
    if not 1<=data_len<=8: raise ValueError("outside configured group data limit")
    e=set(flipped_data_positions)
    if not e.issubset(set(range(data_len))):raise ValueError("error outside data")
    if len(e)!=len(tuple(flipped_data_positions)):raise ValueError("duplicate positions")
    failures=[]
    for j,g in enumerate(groups):
        g=set(g)
        if not g or not g.issubset(set(range(data_len))):raise ValueError("invalid group")
        if len(g&e)%2: failures.append(j)
    return {'failed_groups':tuple(failures),'passes':not failures}

def signature(data_len, groups, data_position):
    if not 0<=data_position<data_len:raise ValueError("invalid position")
    return tuple(int(data_position in g) for g in groups)

def detectable_every_two_data_flips(data_len,groups):
    """All 2-data-bit errors detectable iff all membership signatures differ."""
    signatures=[signature(data_len,groups,i) for i in range(data_len)]
    return len(set(signatures))==data_len
