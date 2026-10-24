"""Read the authored Level-3 environment/episode catalog without model inference."""
import copy
import base64
import hashlib
import gzip
import json
import math
import re
from pathlib import Path

DEFAULT_EPISODE = 'QUCTc6BB5sX_8247'


def collection_cases(cases, selection_path, username=None):
    """Limit new collection while retaining all cases for saved-sample review."""
    selection_path = Path(selection_path)
    if not selection_path.is_file():
        return cases
    selection = json.loads(selection_path.read_text())
    account_keys = selection.get('account_episode_keys', {}).get(username)
    if account_keys is not None:
        if not account_keys or len(account_keys) != len(set(account_keys)):
            raise ValueError('Account episode keys must be nonempty and unique.')
        if any(key not in cases for key in account_keys):
            raise ValueError('An account study episode is missing from the catalog.')
        return {key: cases[key] for key in account_keys}
    # username comes from the gateway-owned worker file, never request input.
    full_catalog_users = selection.get('full_catalog_users', [])
    if not isinstance(full_catalog_users, list) or any(not isinstance(user, str) for user in full_catalog_users):
        raise ValueError('Full-catalog users must be an explicit list of account names.')
    if username is not None and username in full_catalog_users:
        return cases
    keys = selection['episode_keys']
    if not keys or len(keys) != len(set(keys)):
        raise ValueError('Collection episode keys must be nonempty and unique.')
    selected = {}
    for key in keys:
        if key not in cases:
            raise ValueError('Unknown collection episode: ' + key)
        route = cases[key]['route']['reference_path']
        if len(route) < 2:
            raise ValueError('Collection requires a reference route: ' + key)
        length = sum(math.dist(a, b) for a, b in zip(route, route[1:]))
        if not math.isfinite(length) or length <= selection['minimum_reference_length_m_exclusive']:
            raise ValueError('Collection route must exceed the minimum length: ' + key)
        selected[key] = cases[key]
    return selected


def load_house_cases(source_root, include_images=True):
    """Adapt the authored three-case household dataset without rewriting sources."""
    root = Path(source_root)
    case_file = root / 'cases_level3.json'
    memory_file = root / 'house_memory_dataset.json'
    raw = case_file.read_bytes()
    records = {record['id']: record for record in json.loads(memory_file.read_text())['records']}
    titles = {'L3_MULTI': 'L3_MULTI · Snacks: kitchen then TV-room couch',
              'L3_ALIAS': 'L3_ALIAS · Blanket to the screen-room couch',
              'L3_SIMPLE': 'L3_SIMPLE · Notebook to the speaker’s desk'}
    cases = {}
    for index, source in enumerate(json.loads(raw), 1):
        key = 'house_first_' + source['case_id']
        memories = []
        for reference in source['memory_records']:
            record = records[reference['id']]
            image_path = (root / reference['image']).resolve()
            if not image_path.is_relative_to(root.resolve()):
                raise ValueError('Authored memory image escapes the source directory.')
            memories.append({'id': record['id'], 'mode': 'annotated_image',
                             'when': record.get('occurred_at') or 'Household memory',
                             'who': record.get('speaker') or 'Household memory',
                             'said': record['annotation'], 'annotation': record['annotation'],
                             'images': [reference['image']], 'original_view_indices': [1],
                             'image_urls': ['data:image/jpeg;base64,' + base64.b64encode(image_path.read_bytes()).decode()] if include_images else []})
        route = {'scene': source['scene'], 'start_position': source['original_start'],
                 'start_rotation_xyzw': source['original_start_rotation'],
                 'reference_path': source['reference_path'],
                 'goals': [{'position': leg['stop'], 'radius': 0.65, 'subject': leg['goal']}
                           for leg in source['legs']],
                 'authored_trajectory': source['trajectory'],
                 'evaluation_scope': source['evaluation_scope']}
        request = source['request']
        cases[key] = {
            'episode_key': key, 'scene': source['scene'], 'title': titles[source['case_id']],
            'index': index, 'group': 'house_first', 'category': source['phenomenon'],
            'environment_label': 'Iyer–Malhotra household · three recording cases',
            'now': request['issued_at'], 'original_request': request['text'], 'default_request': request['text'],
            'default_current_state': 'Speaker: ' + request['speaker'].title() + '.\n' + request['start_story'],
            'memories': memories, 'route': route, 'source_goal_memory_id': None,
            'default_relevant_memory_ids': [], 'source': str(case_file),
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'scenario': source['evaluation_scope'], 'scenario_matches_original_benchmark': False,
            'reasoning_template': 'Need → relevant memory → visible evidence → next decision',
            'voice_examples': {
                'before': 'The speaker asks: ' + request['text'] + ' I will compare the household memories before choosing a destination.',
                'decision': 'I see [actual feature]. I will [action] because [visible evidence and relevant memory].',
                'passing': 'I see [actual room or landmark]. I will continue toward [my intended destination] because [reason].',
                'correction': 'This view differs from what I expected. I will [correction] because [actual evidence].',
                'arrival': 'I see [actual confirming evidence]. This matches the task and relevant memory, so I will stop here.',
            },
        }
        if not route['goals'] or len(route['reference_path']) < 2:
            raise ValueError('Authored case has no usable ordered route: ' + key)
    return cases


def load_cases(source, default_case=None, include_images=True):
    source = Path(source)
    if not source.is_file():
        if default_case is None:
            raise ValueError('The source presentation is required for environment selection.')
        fallback = copy.deepcopy(default_case)
        fallback.setdefault('title', 'Wash and dry school clothes')
        fallback.setdefault('index', 2)
        fallback['default_relevant_memory_ids'] = [fallback['source_goal_memory_id']]
        return {fallback['episode_key']: fallback}
    raw = source.read_bytes()
    match = re.search(r'<script id="presentation-data" type="application/json">(.*?)</script>', raw.decode(), re.S)
    if not match:
        raise ValueError('Source presentation has no embedded episode data.')
    data = json.loads(match.group(1))
    cases = {}
    for episode in data['cases']:
        level = episode['levels']['3']
        primary = level['inputs']['multiple_memories']['primary']
        goal_id = primary['evaluator_rules']['goal_memory_id']
        memories = []
        for memory_id in primary['memory_ids']:
            memory = copy.deepcopy(data['memories'][memory_id])
            memory['id'] = memory_id
            memory['image_urls'] = [data['images'][name]['data_url'] for name in memory['images']] if include_images else []
            memories.append(memory)
        if goal_id not in primary['memory_ids']:
            raise ValueError('The authored relevant memory is not supplied: ' + episode['episode_key'])
        goal = next(memory for memory in memories if memory['id'] == goal_id)
        state = 'It is now ' + level['now'] + '.'
        if level.get('task_context'):
            state += '\n' + level['task_context']
        case = {
            'episode_key': episode['episode_key'], 'scene': episode['route']['scene'],
            'title': episode['title'], 'index': episode['index'], 'group': episode['group'],
            'category': episode['category_level3'], 'now': level['now'],
            'original_request': primary['assigned_task'], 'default_request': primary['assigned_task'],
            'default_current_state': state, 'memories': memories,
            'route': copy.deepcopy(episode['route']), 'source_goal_memory_id': goal_id,
            'default_relevant_memory_ids': [goal_id], 'source': str(source),
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'scenario': 'Original authored Level-3 presentation task; object handling is not simulated.',
            'scenario_matches_original_benchmark': True,
            'reasoning_template': 'Need → relevant memory → visible evidence → next decision',
            'voice_examples': {
                'before': 'My task is: ' + primary['assigned_task'] + ' ' + goal['who'] +
                    ' said, “' + goal['said'] + '” I will use the visible landmarks from that memory to find the destination.',
                'decision': 'I see [actual feature]. This [matches / differs from] the relevant memory. I will [turn left / turn right / move forward] because [visible reason].',
                'passing': 'This appears to be [room type]. It [matches / differs from] the destination memory. I will [next movement] because [visible reason].',
                'correction': 'I expected [feature], but I see [actual evidence]. I will turn around using right turns and return toward [known passage].',
                'arrival': 'I see [actual matching evidence]. This matches the place described in the relevant memory. I will stop here.',
            },
        }
        # Retain the user's established carried-clothes scenario in the laundry
        # episode. All other episodes use their own authored context.
        if case['episode_key'] == DEFAULT_EPISODE and default_case is not None:
            for key in ['default_request', 'default_current_state', 'scenario', 'reasoning_template']:
                case[key] = default_case[key]
            case['scenario_matches_original_benchmark'] = False
            case['voice_examples'].update({
                'before': 'I already have the dirty school clothes with me. Mary said, “This is where I usually do the laundry.” I will use the landmarks from that memory to find the laundry area.',
                'passing': 'This appears to be a bedroom. It is not my laundry destination, but I can pass through it to reach the hallway.',
                'arrival': 'I see [actual matching evidence]. This matches the place Mary showed me for laundry. I will stop here.',
            })
        cases[case['episode_key']] = case
    return cases


def public_case(case):
    private = {'route', 'source_goal_memory_id', 'source', 'source_sha256', 'source_collection',
               'source_folder', 'source_notes', 'admin_notes'}
    return {key: value for key, value in case.items() if key not in private}


def load_house40_cases(source_root, rxr_file, include_images=True):
    """Import the authored forty-case L3 set using its existing routes and photos.

    Source files remain unchanged. Numbered halves are labels, not a claim that
    their research difficulty was independently verified. Actions/props remain
    conversational context in this navigation-only collector.
    """
    root = Path(source_root)
    filename = root / 'cases_2azQ1b91cZZ.json'
    records = json.loads(filename.read_text())
    moments = {m['id']: m for m in json.loads((root / 'week_log_2azQ1b91cZZ.json').read_text())['moments']}
    with gzip.open(rxr_file, 'rt') as stream:
        episodes = json.load(stream)['episodes']
    by_id = {str(ep['episode_id']): ep for ep in episodes}
    encoded = {}

    def image_url(path):
        path = path.resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('A forty-case source image is unavailable.')
        if not include_images:
            return ''
        if path not in encoded:
            encoded[path] = 'data:image/jpeg;base64,' + base64.b64encode(path.read_bytes()).decode()
        return encoded[path]

    cases = {}
    for index, source in enumerate(records, 1):
        candidates = [by_id[str(eid)] for eid in source['episode_ids'] if str(eid) in by_id]
        if not candidates:
            raise ValueError('No source RxR-CE episode for ' + source['case_id'])
        ep = next((e for e in candidates if str(e.get('instruction', {}).get('instruction_id')) ==
                   str(source['level1_instruction_id'])), candidates[0])
        reference = ep['reference_path']
        cut = source.get('sub')
        if cut:
            reference = reference[cut[0]:cut[1] + 1]
        if len(reference) < 2 or math.dist(reference[-1], source['end_xyz']) > .15:
            raise ValueError('Source route endpoint mismatch for ' + source['case_id'])
        rotation = ep['start_rotation']
        if cut and cut[0] > 0:
            delta = next(([b[i] - reference[0][i] for i in range(3)] for b in reference[1:]
                          if math.dist(reference[0], b) > .01), [0, 0, -1])
            yaw = math.atan2(-delta[0], -delta[2])
            rotation = [0, math.sin(yaw / 2), 0, math.cos(yaw / 2)]
        level = source['levels']['3']
        refs = list(dict.fromkeys(source['week_log_ids']))
        memories = []
        for mid in refs:
            m = moments[mid]
            path = root / 'verify/2azQ1b91cZZ' / ('memory_' + mid + '.jpg')
            urls = [image_url(path)] if m.get('view') else []
            memories.append({'id': mid, 'when': m.get('day', '') + ' ' + m.get('time', ''),
                             'who': m['who'], 'said': m['quote'],
                             'annotation': m['who'] + ' says, “' + m['quote'] + '”',
                             'mode': m.get('mode', 'said'), 'images': [path.name] if urls else [],
                             'image_urls': urls if include_images else [], 'original_view_indices': [1] if urls else []})
        request_image = None
        request_view = level.get('image_view')
        if request_view:
            match = next((m for m in moments.values() if m.get('view') == request_view), None)
            path = (root / 'verify/2azQ1b91cZZ' / ('memory_' + match['id'] + '.jpg') if match else
                    root / 'verify/2azQ1b91cZZ' / ('sheet_' + request_view + '.jpg'))
            request_image = image_url(path)
        key = 'house40_' + source['case_id']
        cases[key] = {
            'episode_key': key, 'scene': '2azQ1b91cZZ', 'title': f'House 40 · {index:02d} · ' + level['text'],
            'index': index, 'group': 'house40', 'category': level.get('phenomenon', ''),
            'environment_label': 'House-first · 20 + 20 tasks',
            'now': level.get('day', '') + ' ' + level.get('time', ''),
            'original_request': level['text'], 'default_request': level['text'],
            'default_current_state': 'Speaker: ' + level['speaker'] + '. ' + source['start'].get('story', '') +
                                     ' This is a navigation-only task; object handling and other actions are conversational context.',
            'memories': memories, 'default_relevant_memory_ids': [], 'source_goal_memory_id': None,
            'request_image_url': request_image,
            'route': {'scene': '2azQ1b91cZZ', 'start_position': reference[0],
                      'start_rotation_xyzw': rotation, 'reference_path': reference,
                      'goals': [{'position': reference[-1], 'radius': .65}],
                      'source_episode_id': str(ep['episode_id']), 'source_subroute': cut,
                      'authored_subroute_heading': bool(cut and cut[0] > 0)},
            'source': str(filename), 'source_folder': str(root),
            'source_collection': 'house40_a' if index <= 20 else 'house40_b',
            'ready_for_assignment': not bool(level.get('image') and not request_view),
            'source_notes': ('Missing request photo: ' + level['image'] + '. Admin preview only until supplied. '
                             if level.get('image') and not request_view else '') +
                            'L3 main request only; optional off-limits/multi-goal forms are not imported. Source images reused; independent task/geometry review pending. Props are not inserted.',
            'scenario': 'Authored household request. Navigate to the remembered destination; no manipulation, cleaning or state-change outcome is simulated.',
            'scenario_matches_original_benchmark': False,
            'reasoning_template': 'Task → relevant memory → matching features → general plan → when to stop',
            'voice_examples': {},
        }
    return cases


def load_study_cases(source, default_case, selection, include_images=True):
    """One catalog loader shared by collector workers and the private admin UI."""
    cases = load_cases(source, default_case, include_images=include_images)
    for case in cases.values():
        case['source_collection'] = 'presentation10'
        case['source_folder'] = str(Path(source).parent)
    if selection.get('authored_source_root'):
        added = load_house_cases(selection['authored_source_root'], include_images=include_images)
        for case in added.values():
            case['source_collection'] = 'house3'
            case['source_folder'] = str(selection['authored_source_root'])
        cases.update(added)
    if selection.get('house40_source_root'):
        cases.update(load_house40_cases(selection['house40_source_root'], selection['house40_rxr_file'], include_images=include_images))
    return cases


def environment_catalog(cases, scene_root):
    grouped = {}
    collections = {}
    for case in cases.values():
        scene = case['scene']
        collections.setdefault(scene, set()).add(case.get('source_collection', 'existing'))
        environment = grouped.setdefault(scene, {
            'scene': scene, 'label': case.get('environment_label') or 'Environment ' + str(len(grouped) + 1) + ' · ' + scene,
            'available': (Path(scene_root) / scene / (scene + '.glb')).is_file(), 'episodes': []})
        environment['episodes'].append({
            'episode_key': case['episode_key'], 'title': case['title'], 'index': case['index'],
            'request': case['default_request'], 'group': case['group'], 'category': case.get('category', '')})
    for scene, environment in grouped.items():
        if len(collections[scene]) > 1:
            environment['label'] = 'Study environment · ' + scene
    return list(grouped.values())
