"""Read the authored Level-3 environment/episode catalog without model inference."""
import copy
import hashlib
import json
import re
from pathlib import Path

DEFAULT_EPISODE = 'QUCTc6BB5sX_8247'


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
            'scene': scene, 'label': 'Environment ' + str(len(grouped) + 1) + ' · ' + scene,
            'available': (Path(scene_root) / scene / (scene + '.glb')).is_file(), 'episodes': []})
        environment['episodes'].append({
            'episode_key': case['episode_key'], 'title': case['title'], 'index': case['index'],
            'request': case['default_request'], 'group': case['group'], 'category': case.get('category', '')})
    return list(grouped.values())
