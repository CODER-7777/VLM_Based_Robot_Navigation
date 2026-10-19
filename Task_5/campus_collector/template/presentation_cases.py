"""Read the authored Level-3 environment/episode catalog without model inference."""
import copy
import base64
import hashlib
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


def load_house_cases(source_root):
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
                             'image_urls': ['data:image/jpeg;base64,' + base64.b64encode(image_path.read_bytes()).decode()]})
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


def load_cases(source, default_case=None):
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
            memory['image_urls'] = [data['images'][name]['data_url'] for name in memory['images']]
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
    return {key: value for key, value in case.items() if key not in ['route', 'source_goal_memory_id']}


def environment_catalog(cases, scene_root):
    grouped = {}
    for case in cases.values():
        scene = case['scene']
        environment = grouped.setdefault(scene, {
            'scene': scene, 'label': case.get('environment_label') or 'Environment ' + str(len(grouped) + 1) + ' · ' + scene,
            'available': (Path(scene_root) / scene / (scene + '.glb')).is_file(), 'episodes': []})
        environment['episodes'].append({
            'episode_key': case['episode_key'], 'title': case['title'], 'index': case['index'],
            'request': case['default_request'], 'group': case['group'], 'category': case.get('category', '')})
    return list(grouped.values())
