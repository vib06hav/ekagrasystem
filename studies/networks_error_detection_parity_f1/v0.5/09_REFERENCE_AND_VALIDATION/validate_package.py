#!/usr/bin/env python3
"""Self-contained validation of F1 v0.5 candidate source consistency + mathematical parity invariants.
Requires PyYAML. Does not validate semantic quality of LLM utterances or independent experimental efficacy.
"""
from __future__ import annotations
import sys, yaml, pathlib, itertools, collections, json, importlib.util, hashlib, csv
R=pathlib.Path(__file__).resolve().parent.parent
Y=R/'08_SCIENTIFIC_YAML'; P=R/'07_PROMPT_CONTRACTS'; RE=R/'09_REFERENCE_AND_VALIDATION'
errors=[]; warns=[]; checks=[]
def check(condition,description):
 (checks if condition else errors).append(description)
def warn(condition,description):
 if not condition:warns.append(description)
def ld(name):
 path=Y/name
 if not path.exists():errors.append('missing '+str(path));return {}
 try:return yaml.safe_load(path.read_text(encoding='utf8'))
 except Exception as ex:errors.append('YAML invalid '+name+': '+str(ex));return {}
files=['curriculum.yaml','knowledge.yaml','transitions.yaml','interventions.yaml','subsection_interventions.yaml','conversation_judge.yaml','scenario_rules.yaml','assessment_families.yaml','judge.yaml','protocol.yaml']
data={name:ld(name) for name in files}
check(len([f for f in Y.glob('*.yaml')])==10,'exactly 10 scientific YAMLs')
check(len(list(P.glob('*.md')))==5,'exactly 5 prompt contracts')
check(all(isinstance(v,dict) and v.get('status','').startswith('CANDIDATE_UNAPPROVED') for v in data.values()),'all scientific YAML marked unapproved')

c=data['curriculum.yaml']; subs=c.get('subsections',[]); sections=c.get('sections',[])
expected={'C1':4,'C2':4,'C3':2,'C4':3}
check(len(subs)==13,'exactly 13 locked subsection records')
check(len(sections)==4,'exactly 4 major sections')
check(collections.Counter(s['section_id'] for s in subs)==expected,'subsection counts 4/4/2/3')
submap={s['id']:s for s in subs};secmap={s['id']:s for s in sections}
check(len(submap)==len(subs),'subsection IDs unique')
for s in sections:
 check(s['subsection_ids']==[x['id'] for x in subs if x['section_id']==s['id']],f'{s["id"]} subsection order exactly matches source')
for s in subs:
 refs=[r['id'] for r in s['required_content']]
 check(bool(refs) and len(refs)==len(set(refs)),f'{s["id"]} unique locked bullet IDs')
 check(bool(s['teaching_goal'] and s['title']),f'{s["id"]} has title and goal')
# Verify verbatim markdown required bullets for every subsection, as locked source assurance.
course=(R/'CURRICULUM_SOURCE_LOCKED.md').read_text(encoding='utf8')
for s in subs:
 for item in s['required_content']:
  check(item['required_fact'] in course,f'{item["id"]} bullet occurs verbatim in locked Markdown')
 check(s['teaching_goal'] in course,f'{s["id"]} teaching goal occurs verbatim')

ks=data['knowledge.yaml']; refs={x['id'] for k in ('components','relations','misconceptions') for x in ks.get(k,[])}
check(len(refs)==sum(len(ks.get(k,[])) for k in ('components','relations','misconceptions')),'knowledge IDs unique')
trans=data['transitions.yaml']['transitions']; check(len(trans)==4,'exactly 4 SOLO transitions')
for t in trans:
 for field in ('components','relations','misconceptions'):
  for r in t[field]:check(r in refs,f'{t["id"]} transition {field} ref {r} present')

I=data['interventions.yaml']; S=data['subsection_interventions.yaml']; PIDS=['P1','P2','P3']
check([p['id'] for p in I['pedagogies']]==PIDS,'exactly three ordered global pedagogies')
parent={(x['transition_id'],x['pedagogy_id']):x for x in I['cells']}
check(len(parent)==12 and len(I['cells'])==12,'exactly 12 unique section×pedagogy parent cells')
for sid in expected:
 for pid in PIDS:
  check((sid,pid) in parent,f'parent {sid}-{pid} exists')
child={(x['subsection_id'],x['pedagogy_id']):x for x in S['cells']}
check(len(S['cells'])==39 and len(child)==39,'exactly 39 unique subsection×pedagogy child cells')
check(sum(len(x['core_moves']) for x in S['cells'])>=120,'detailed individualized teaching moves exist')
for s in subs:
 for pid in PIDS:
  key=(s['id'],pid)
  if key not in child: errors.append(f'missing child {key}');continue
  x=child[key]; p=parent.get((s['section_id'],pid));
  check(p is not None and x['parent_cell_id']==p['id'],f'{x["id"]} parent correct')
  req=set(x['required_content_refs']); required={r['id'] for r in s['required_content']}
  check(req==required,f'{x["id"]} references exactly locked content requirements')
  cover=set(z for move in x['core_moves'] for z in move['covers_content_refs'])
  check(cover==required,f'{x["id"]} union of core moves covers all required facts')
  check(all(set(m['covers_content_refs'])<=required and len(m['covers_content_refs'])==len(set(m['covers_content_refs'])) for m in x['core_moves']),f'{x["id"]} no out-of-scope or duplicate move refs')
  check(all('unanswered questions are not evidence' in m['completion_evidence'] for m in x['core_moves']),f'{x["id"]} move evidence requires substantive resolved instruction')
  check(len(x['core_moves'])>=3 and all(len(m['instructional_action'])>45 for m in x['core_moves']),f'{x["id"]} substantive authored moves')
  check('PILOT_CALIBRATION_REQUIRED_NOT_APPROVED'==x['candidate_exposure_envelope']['status'],f'{x["id"]} limits unapproved')
  check(x['clarification_policy']['correctness_required_for_closure'] is False,f'{x["id"]} no learner correctness mastery gate')
for parent_cell in I['cells']:
 for r in parent_cell['target_refs']:check(r in refs,f'{parent_cell["id"]} science ref {r} exists')
 check(parent_cell['subsection_order']==secmap[parent_cell['transition_id']]['subsection_ids'],f'{parent_cell["id"]} ordered child trajectory correct')

# All assessment IDs preserved, no C2 prohibited advanced items in positive roles.
a=data['assessment_families.yaml']; blue=a['blueprints'];items=[i for b in blue for i in b['items']]
check(len(blue)==16,'16 assessment blueprints')
check(len(items)==64,'64 assessment slot contracts')
check(sum(i['type']=='MCQ' for i in items)==48 and sum(i['type']=='SUBJECTIVE' for i in items)==16,'48 MCQ + 16 subjective')
check(len(set(i['id'] for i in items))==64,'all item IDs unique')
check(len(set(b['id'] for b in blue))==16,'all blueprint IDs unique')
check(collections.Counter(b['transition_id'] for b in blue)=={'C1':4,'C2':4,'C3':4,'C4':4},'4 blueprints per major section')
for b in blue:
 check(len(b['items'])==4,f'{b["id"]} four item slots')
 check([i['type'] for i in b['items']]==['MCQ','MCQ','MCQ','SUBJECTIVE'],f'{b["id"]} ordered 3+1 slots')
 check(b['curriculum_subsection_refs']==secmap[b['transition_id']]['subsection_ids'],f'{b["id"]} locked section mapping')
 for i in b['items']:
  check(i['id'].startswith(b['id']+'-'),f'{i["id"]} ID belongs to parent blueprint')
  check(i['transition_id']==b['transition_id'],f'{i["id"]} section correct')
  check(i['scenario_family'] in {f['id'] for f in data['scenario_rules.yaml']['families']},f'{i["id"]} scenario family exists')
  check(bool(i.get('mapped_locked_subsections')) and all(s in secmap[b['transition_id']]['subsection_ids'] for s in i['mapped_locked_subsections']),f'{i["id"]} item points to in-scope locked subsection(s)')
  check(bool(i['scientific_purpose'] and i['generation_instruction']),f'{i["id"]} substantive contract')
  if b['transition_id']=='C2':
   involved=(' '.join(str(i.get(k,'')) for k in ['scientific_purpose','generation_instruction','correctness_condition','target_structural_evidence'])).lower()
   check(not any(term in involved for term in ['rectangle','four-corner','three-flip','3-bit mimic','four-data-bit']),f'{i["id"]} does not require C3-only complex patterns')

# All five prompt names and critical role isolation phrases
for name in ['TUTOR_PROMPT.md','CONVERSATION_JUDGE_PROMPT.md','ASSESSMENT_GENERATION_PROMPT.md','SEMANTIC_REVIEW_PROMPT.md','SUBJECTIVE_JUDGE_PROMPT.md']:
 check((P/name).exists(),f'{name} exists')
if (P/'CONVERSATION_JUDGE_PROMPT.md').exists():
 check('NOT the formal Subjective Judge' in (P/'CONVERSATION_JUDGE_PROMPT.md').read_text(encoding='utf8'), 'Conversation Judge excludes formal scoring')
if (P/'SUBJECTIVE_JUDGE_PROMPT.md').exists():
 check('Do NOT receive' in (P/'SUBJECTIVE_JUDGE_PROMPT.md').read_text(encoding='utf8'), 'Formal Judge treatment isolation')


# New course-source hash and human-readable move alignment audit are reproducible in the package.
assert hashlib.sha256(course.encode('utf8')).hexdigest()==(RE/'SOURCE_SHA256.txt').read_text(encoding='utf8').strip(), 'Locked course content checksum mismatch'
with (RE/'MOVE_CONTENT_ALIGNMENT_AUDIT.csv').open(encoding='utf8',newline='') as _f:
 _audit=list(csv.DictReader(_f))
check(len(_audit)==sum(len(x['core_moves']) for x in S['cells']),'alignment audit covers every teaching move')
_by_id={r['move_id']:r for r in _audit}
for x in S['cells']:
 for m in x['core_moves']:
  r=_by_id.get(m['id'])
  check(bool(r) and r['aligned_content_refs'].split(';')==m['covers_content_refs'] and r['instructional_action']==m['instructional_action'],f'{m["id"]} audit row matches resolved move')
check(not any('signature' in (item.get('scientific_purpose','')+' '+item.get('correctness_condition','')+' '+item.get('target_structural_evidence','')).lower() for b in blue if b['id']=='C4-A2' for item in b['items']), 'C4-A2 no formal membership-signature requirement')

# Index generated from actual assessment slots: reject stale evidence after edits.
with (RE/'ASSESSMENT_ALIGNMENT_INDEX.csv').open(encoding='utf8',newline='') as _f:
 _assess_rows=list(csv.DictReader(_f))
check(len(_assess_rows)==64,'assessment index contains all current slots')
_assess_lookup={r['item_id']:r for r in _assess_rows}
for _b in blue:
 for _i in _b['items']:
  _r=_assess_lookup.get(_i['id'])
  check(bool(_r) and _r['scientific_purpose']==_i['scientific_purpose'] and _r['mapped_locked_subsections'].split(';')==_i['mapped_locked_subsections'],f'{_i["id"]} assessment index matches revised YAML')

# Mathematical oracle all 2D small grids incl checkbit/corner and all 2-flip combinations; 3-mimic/rectangles.
spec=importlib.util.spec_from_file_location('v04_oracle',RE/'v04_reference_parity_oracle.py')
o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
casecounts=collections.Counter()
for data_len in range(1,6):
 for vals in itertools.product((0,1),repeat=data_len):
  for convention in ['even','odd']:
   frame=o.make_frame(vals,convention)
   check(o.receiver_pass(frame,convention),'valid 1D '+convention+' '+str(vals))
   for k in range(len(frame)+1):
    for positions in itertools.combinations(range(len(frame)),k):
     passed=o.receiver_pass(o.flip_positions(frame,positions),convention)
     if passed != (k%2==0): errors.append('1D parity law false at '+str((vals,convention,positions)))
     casecounts['1D']+=1
# use distinct grid sizes including cells devoted to checkbits
for rows,cols in [(1,1),(2,2),(2,3),(3,4)]:
 for bitvalues in itertools.product((0,1),repeat=rows*cols):
  if rows*cols>6 and bitvalues!=tuple(0 for _ in bitvalues):continue
  data=[bitvalues[r*cols:(r+1)*cols] for r in range(rows)]
  grid=o.full_grid(data)
  R=len(grid);C=len(grid[0]);places=list(itertools.product(range(R),range(C)))
  syndrome=o.grid_syndrome(grid)
  if not syndrome['passes']:errors.append('initial grid invalid')
  for pos in places:
   actual=o.grid_syndrome(grid,[pos]);casecounts['2D_one']+=1
   if actual['failing_rows']!=(pos[0],) or actual['failing_cols']!=(pos[1],):errors.append('one flip location violation')
  for pair in itertools.combinations(places,2):
   actual=o.grid_syndrome(grid,pair);casecounts['2D_two']+=1
   if actual['passes']:errors.append('two flip undetected '+str(pair))
  if rows>=2 and cols>=2:
   for ra,rb in itertools.combinations(range(rows),2):
    for ca,cb in itertools.combinations(range(cols),2):
     rect=[(ra,ca),(ra,cb),(rb,ca),(rb,cb)]
     if not o.grid_syndrome(grid,rect)['passes']:errors.append('rectangle not undetected')
     mimic=[(ra,cb),(rb,ca),(rb,cb)]
     one=[(ra,ca)]
     a1=o.grid_syndrome(grid,mimic);a2=o.grid_syndrome(grid,one)
     if (a1['failing_rows'],a1['failing_cols'])!=(a2['failing_rows'],a2['failing_cols']):errors.append('L shape mimic false')
     casecounts['rectangle_and_mimic']+=1
# General grouped parity data-only and checkbit flips tested against the complete checked groups.
for data_len in range(2,6):
 group_pool=[set(i for i in range(data_len) if (bits>>i)&1) for bits in range(1,1<<data_len)]
 for ga in group_pool:
  for gb in group_pool:
   if len(ga^gb)==0:continue
   groups=[ga,gb]
   # transmitted positions: data 0..n-1, associated checking bits n and n+1
   complete_groups=[g|{data_len+j} for j,g in enumerate(groups)]
   base_data=[0]*data_len;check_values=[0,0];transmitted=base_data+check_values
   for k in range(min(len(transmitted),4)+1):
    for flips in itertools.combinations(range(len(transmitted)),k):
     observed=[int(sum(p in complete_group for p in flips)%2) for complete_group in complete_groups]
     outcome=all(v==0 for v in observed)
     actual=list(transmitted)
     for pos in flips:actual[pos]^=1
     verified=all(sum(actual[p] for p in group)%2==0 for group in complete_groups)
     if outcome!=verified:errors.append('group check law failed')
     casecounts['grouped_including_checkbits']+=1
   for flips in itertools.combinations(range(data_len),2):
    casecounts['grouped_two_signature']+=1
    expected=o.group_syndrome(data_len,groups,flips)['passes']
    if expected!=(o.signature(data_len,groups,flips[0])==o.signature(data_len,groups,flips[1])):
     errors.append('two-data-flip group signature theorem failed')

check(not errors,'no structural/scientific validation errors accumulated')
report={'status':'PASS' if not errors else 'FAIL','structural_checks':len(checks),'math_cases':dict(casecounts),
 'errors':errors,'warnings':warns,
 'limitations':['Automated structure and parity identities do NOT validate pedagogical effectiveness.',
 'Coverage refs were semantically remapped and audited as candidate authoring, but generated dialogue STILL requires transcript-based evidence and expert review.',
 'Old inherited assessment slots and new prompts still require human semantic/scientific audit.',
 'Candidate numerical limits and LLM monitor reliability require calibration and explicit researcher approval.',
 'Package is not drop-in compatible with v0.4; service code was not modified.']}
(RE/'VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
(RE/'VALIDATION_REPORT.txt').write_text('STATUS: '+report['status']+'\nSTRUCTURAL CHECKS: '+str(len(checks))+'\nMATHEMATICAL CASES: '+str(dict(casecounts))+'\nERRORS:\n'+('\n'.join(errors) or 'None')+'\nWARNINGS:\n'+('\n'.join(warns) or 'None')+'\n',encoding='utf8')
print('STATUS:',report['status'])
print('structural checks:',len(checks))
print('math case counts:',dict(casecounts))
print('errors:',errors[:15])
sys.exit(0 if not errors else 1)
