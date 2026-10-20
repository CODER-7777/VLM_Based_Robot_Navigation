"""Read-only case adapter. Reviewer judgments live separately from authored data."""
from __future__ import annotations
import csv
import hashlib
import json
import random
import re
from pathlib import Path

SCENE = '2azQ1b91cZZ'
DAYS = ['D0 Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
TYPES = {
    'S1': ('Spatial relation', 'Does the landmark relation select exactly one object? Check every nearby look-alike.'),
    'S2': ('Nearest to a named place', 'Compare walking distances from the named place, not the robot. Is the winner clearly nearer?'),
    'S3': ('Floor or position', 'Check upstairs/downstairs and the named room or landmark in the actual building.'),
    'C1': ('Avoid a room', 'Can you reach the destination without entering the forbidden room? Check the whole detour.'),
    'C2': ('Exclusion or negation', 'Find every acceptable destination. Reject the excluded place; do not require one arbitrary answer.'),
    'C3': ('Household state', 'At the request time, does the current household state select the destination? Check later overrides.'),
    'M1': ('Ordered stops', 'Visit every stop in the stated order. Is each stop and the transition understandable?'),
    'M2': ('Search with fallback', 'The item must be absent at the first stop and visible at the fallback. Check both places.'),
    'M3': ('Implied pickup', 'Can the reviewer infer the pickup from memory, then identify where to deliver it? Inspect both legs.'),
    'T1': ('Newer memory overrides older', 'Do two dated memories disagree, and does the appropriate newer one clearly win?'),
    'T2': ('Time anchor or event order', 'Does the specified time or before/after relation select exactly the intended memory?'),
    'T3': ('Routine by day or time', 'Is the routine actually taught by the supplied memories, and does it apply now?'),
    'L1': ('Nickname or alias', 'Does an earlier memory teach the nickname and tie it to a recognizable place?'),
    'L2': ('Reference or omitted noun', 'Resolve there, our room, and similar references without reading the answer.'),
    'L3': ('Speaker-relative name', 'Resolve Mom, Dad, my, and our using the speaker and earlier memories.'),
    'K1': ('Function of a place', 'Does the requested activity fit the intended place? Could another place fit equally well?'),
    'K2': ('Where things are kept', 'Does memory support this household location, beyond a generic assumption?'),
    'K3': ('Social norm or privacy', 'Check the stopping boundary. An outside-door request must not require entering the private room.'),
    'P1': ('Ownership', 'Do earlier memories identify the owner and distinguish their object or place from others?'),
    'V1': ('Image reference', 'Is a real image attached, readable, and sufficient to distinguish the intended object or place?'),
}
DIMENSIONS = {
    'instruction': 'Instruction is clear and natural',
    'memory': 'Memories are clear and sufficient',
    'grounding': 'Names, references and times resolve',
    'navigation': 'Destination and stopping point work',
    'alternatives': 'No unintended acceptable interpretation',
    'form': 'All stops, exclusions and conditions work',
    'visuals': 'Photos and scene match the words',
    'props': 'Required props are visible and consistent',
}
RATINGS = {'pass', 'minor', 'major', 'fail', 'unsure', 'na'}

def when(m):
    return DAYS.index(m['day']), m['time']

def review_props(case, variant):
    if variant == 'level2':
        return []
    forms = case['forms']
    selected = forms[int(variant[4:])] if variant.startswith('form') else None
    form_only = {p['item'] for f in forms if f['text'] != case['levels']['3']['text'] for p in f.get('props', [])}
    selected_items = {p['item'] for p in (selected or {}).get('props', [])}
    return [p for p in case['props'] if p['item'] not in form_only or p['item'] in selected_items]

def types_for(c):
    description = c['levels']['3']['phenomenon']
    explicit = re.match(r'^([SCMTLKPV][123])\b', description)
    if explicit:
        return explicit[1], [], 'authored taxonomy'
    s = description.lower()
    candidates = []
    for needle, code in [('image', 'V1'), ('two names', 'L1'), ('newer overrides', 'T1'),
                         ('nickname', 'L1'), ('person', 'P1'), ('whose', 'P1'), ('habit', 'T3')]:
        if needle in s and code not in candidates:
            candidates.append(code)
    return (candidates or ['P1'])[0], (candidates or [])[1:], 'mapped from authored phenomenon'

class Catalog:
    def __init__(self, source):
        self.source = Path(source)
        self.cases = json.loads((self.source / f'cases_{SCENE}.json').read_text())
        self.week = json.loads((self.source / f'week_log_{SCENE}.json').read_text())
        self.inventory = json.loads((self.source / f'inventory_{SCENE}.json').read_text())
        self.family = json.loads((self.source / f'family_{SCENE}.json').read_text())
        self.places = {p['id']: p for p in self.inventory['places']}
        self.by_id = {c['case_id']: c for c in self.cases}
        self.fingerprint = hashlib.sha256(json.dumps([self.cases, self.week], sort_keys=True).encode()).hexdigest()
        self.verify = self.source / 'verify' / SCENE
        self.naturalness = sorted({t for c in self.cases for t in
                                  ([c['levels']['2']['text']] if c['levels']['2'] else []) +
                                  [c['levels']['3']['text']] + [f['text'] for f in c['forms']]})
        random.Random(0).shuffle(self.naturalness)

    def room_memories(self, c, form):
        if form['form'] != 'off_limits':
            return []
        room = form['room'][4:]
        names = [re.sub(r'^the\s+', '', n.lower()) for n in self.family['rooms'][room]['names']]
        for m in sorted(self.week['moments'], key=when):
            if when(m) >= when(c['start']) or not m.get('view_pose') or not m.get('view'):
                continue
            view = m['view']
            viewed_room = view[4:] if view.startswith('room') else str(self.places[view]['room'])
            if viewed_room == room and any(n in m['quote'].lower() for n in names):
                return [m['id']]
        return []

    def first_stop_memories(self, c, form):
        target = form.get('goal1') or form.get('first')
        if not target:
            return [], False
        earlier = [m for m in sorted(self.week['moments'], key=when)
                   if when(m) < when(c['start']) and m.get('view_pose') and m.get('view')]
        direct = [m['id'] for m in earlier if m['view'] == target]
        if direct:
            return direct[:1], True
        room = target[4:] if target.startswith('room') else str(self.places[target]['room'])
        area = [m['id'] for m in earlier if m['view'] == f'room{room}']
        return area[:1], False

    def memories(self, c, blind=False):
        roles = {}
        for role, ids in c['levels']['3']['records'].items():
            for mid in ids:
                roles.setdefault(mid, []).append(role)
        for f in c['forms']:
            for mid in f.get('key', []):
                roles.setdefault(mid, []).append('form key')
            for mid in self.room_memories(c, f):
                roles.setdefault(mid, []).append('room to avoid')
            mids, direct = self.first_stop_memories(c, f)
            for mid in mids:
                roles.setdefault(mid, []).append('first stop' if direct else 'first stop area')
        out = []
        for m in sorted(self.week['moments'], key=when):
            if when(m) >= when(c['start']):
                continue
            d = {k: m[k] for k in ('id', 'day', 'time', 'who', 'mode', 'quote')}
            d['photo'] = f'memory_{m["id"]}.jpg' if m.get('view_pose') else None
            if not blind:
                d.update(view=m.get('view'), roles=roles.get(m['id'], []))
            out.append(d)
        return out

    def case(self, cid, blind=False):
        c = self.by_id[cid]
        l3 = c['levels']['3']
        out = dict(id=cid, number=self.cases.index(c)+1, start={k: c['start'][k] for k in ('speaker', 'day', 'time', 'story', 'label', 'room')},
                   instruction=l3['text'], need=c['levels']['2']['text'] if c['levels']['2'] else None,
                   forms=[dict(index=i, text=f['text']) for i, f in enumerate(c['forms'])],
                   image_description=l3.get('image'),
                   image=(f'image_case{self.cases.index(c)+1:02}.jpg' if l3.get('image_view') or self.cases.index(c)==6 else None),
                   memories=self.memories(c, blind))
        if blind:
            return out
        primary, secondary, origin = types_for(c)
        form_codes = {'multi_goal':'M1','next_place':'M2','off_limits':'C1'}
        secondary = list(dict.fromkeys(secondary + [form_codes[f['form']] for f in c['forms'] if form_codes[f['form']] != primary]))
        out.update(batch='General pilot' if out['number']<=20 else 'Difficulty types', primary=primary, secondary=secondary,
                   type_origin=origin, phenomenon=l3['phenomenon'], length=c['length_m'], tier=c['tier'],
                   level1=c['levels']['1']['text'], props=c['props'],
                   expected=self.answer(c), flags=self.flags(c), forms=[dict(index=i, **f, room_memory_ids=self.room_memories(c,f),
                   first_stop_memory_ids=self.first_stop_memories(c,f)[0], first_stop_direct=self.first_stop_memories(c,f)[1],
                   room_name=self.family['rooms'][f['room'][4:]]['names'][0] if f['form']=='off_limits' else None) for i,f in enumerate(c['forms'])])
        return out

    def answer(self, c):
        l3 = c['levels']['3']
        ids = l3.get('valid_ids') or [c['goal']]
        return dict(level2=c['levels']['2']['valid_places'] if c['levels']['2'] else None,
                    level3=[dict(id=x, name=self.name(x)) for x in ids],
                    selected_route_goal=c['goal'], competitor=dict(id=c['competitor'], name=c['competitor_name']))

    def name(self, x):
        if x.startswith('room'):
            return self.family.get('rooms', {}).get(x[4:], {}).get('use', self.inventory['rooms'][x[4:]]['label']+x[4:])
        p = self.places[x]
        return f'{p["raw"]} ({self.inventory["rooms"][str(p["room"])]["label"]}{p["room"]})'

    def flags(self, c):
        flags = []
        if c['props']:
            flags.append('Requires explicit scene props; confirm their appearance and placement before passing.')
        if c['levels']['3'].get('valid_ids'):
            flags.append('Several destinations are allowed. The old blind key lists only one; use the full valid set shown here.')
        if c['levels']['3'].get('image') and not c['levels']['3'].get('image_view'):
            flags.append('Case 7 reference image is newly rendered from the cleat model; verify that it matches the request.')
        if any(s in c['levels']['3']['text'].lower() for s in ('outside', "don't go in", 'nightstand', 'fireplace', 'table in here')):
            flags.append('Inspect the exact object or stopping boundary; a nearby point is not sufficient evidence.')
        if c['case_id'].endswith(('case06','case32')):
            flags.append('Level 2 says make coffee, but its valid set lists ovens/range/grill. Review the activity and accepted destinations.')
        if c['case_id'].endswith('case25'):
            flags.append('p42 is described in earlier notes as a sideboard with a tea set. Check whether calling it an eating table is valid.')
        if c['case_id'].endswith('case07'):
            flags.append('S01 says the soccer bag is on the bench, but does not explicitly put the missing cleat there. Check whether this inference is sufficient.')
        if c['case_id'].endswith('case16'):
            flags.append('The shared primary bedroom has two nightstands. Check whether any earlier memory identifies which one is Megan’s.')
        if c['case_id'].endswith('case34'):
            flags.append('N03 describes a Monday nap. The request is on Saturday; check whether earlier memories establish a daily routine.')
        if c['case_id'].endswith('case40'):
            flags.append('The goal is a room ID; the instruction requires stopping outside the bathroom. Confirm the endpoint is outside.')
        return flags

    def listing(self, blind=False):
        return [dict(id=c['case_id'], number=i+1, **({} if blind else dict(batch='General pilot' if i<20 else 'Difficulty types', primary=types_for(c)[0], length=c['length_m'], variant_count=1+bool(c['levels']['2'])+len(c['forms'])))) for i,c in enumerate(self.cases)]

    def props(self):
        out = {}
        for c in self.cases:
            for p in c['props']:
                d = out.setdefault(p['item'], dict(p, cases=[]))
                d['cases'].append(c['case_id'])
        return list(out.values())

    def export_index(self, destination):
        with Path(destination).open('w') as f:
            writer=csv.writer(f);writer.writerow(['case','batch','primary_type','type_name','secondary_types','length_m','request'])
            for c in self.cases:
                d=self.case(c['case_id']);writer.writerow([d['number'],d['batch'],d['primary'],TYPES[d['primary']][0],';'.join(d['secondary']),d['length'],d['instruction']])
