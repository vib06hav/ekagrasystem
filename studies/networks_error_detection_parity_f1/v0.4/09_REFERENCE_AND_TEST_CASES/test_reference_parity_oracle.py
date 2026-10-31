"""Exhaustive and invariant tests; run with python directly; no pytest dependency."""
import itertools, random
from reference_parity_oracle import *

def test_reference():
    checks=0
    # All data payloads and all error subsets for shorter frames, both conventions
    for n in range(3,8):
        for bits in itertools.product([0,1], repeat=n):
            for convention in ('even','odd'):
                frm=make_frame(bits, convention)
                assert len(frm)<=8 and receiver_pass(frm,convention)
                for count in range(min(len(frm),3)+1):
                    for e in itertools.combinations(range(len(frm)),count):
                        passed=receiver_pass(flip_positions(frm,e),convention)
                        assert passed == (len(e)%2==0)
                        checks+=1
    # exhaustive small full 2D grid: 2x2 data, 3x3 transmitted
    for data_flat in itertools.product([0,1],repeat=4):
        g=full_grid([data_flat[:2],data_flat[2:]])
        assert grid_syndrome(g)['passes']
        coords=list(itertools.product(range(3),range(3)))
        for p in coords:
            s=grid_syndrome(g,[p]);assert s['failing_rows']==(p[0],) and s['failing_cols']==(p[1],)
            checks+=1
        for a,b in itertools.combinations(coords,2):
            s=grid_syndrome(g,[a,b]);assert not s['passes']
            checks+=1
        assert grid_syndrome(g,[(0,0),(0,1),(1,0),(1,1)])['passes']
        checks+=1
    # explicit 3x4 historical reference construction (not compulsory runtime)
    g=full_grid([[0,1,0,1],[1,0,0,0],[1,1,0,1]])
    assert len(g)==4 and len(g[0])==5
    assert grid_syndrome(g,[(0,0),(0,2),(2,0),(2,2)])['passes']
    checks+=1
    # all grouped memberships of three data positions with 2 nonempty group checks
    n=3
    subsets=[set(s) for count in range(1,n+1) for s in itertools.combinations(range(n),count)]
    for g1,g2 in itertools.product(subsets,repeat=2):
        groups=[g1,g2]
        for count in range(n+1):
            for e in itertools.combinations(range(n),count):
                s=group_syndrome(n,groups,e)
                assert s['passes']== all(len(set(e)&set(group))%2==0 for group in groups)
                checks+=1
        all_two=all(not group_syndrome(n,groups,pair)['passes'] for pair in itertools.combinations(range(n),2))
        assert detectable_every_two_data_flips(n,groups)==all_two
        checks+=1
    return checks

if __name__=='__main__':
    c=test_reference()
    print(f'PASS: {c} independent parity test assertions / cases (including exhaustive small-case enumeration)')
