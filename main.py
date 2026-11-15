import urllib.request
import json
import random
from collections import defaultdict

API_URL = "https://pc28.help/api/kj.json?nbr=300"
ALL_GROUPS = ['大单', '大双', '小单', '小双']
TEMA_POOL = {
    "小双": [0, 2, 4, 6, 8, 10, 12], "小单": [1, 3, 5, 7, 9, 11, 13],
    "大双": [14, 16, 18, 20, 22, 24, 26], "大单": [15, 17, 19, 21, 23, 25, 27]
}

def get_7_0_prediction(history):
    if len(history) < 30: return None
    groups = [x['type'] for x in history]
    current_group = groups[-1]
    lookback = groups[-100:]
    trans_matrix = defaultdict(lambda: defaultdict(int))
    for i in range(len(lookback) - 1):
        trans_matrix[lookback[i]][lookback[i+1]] += 1
    probs = {}
    for group in ALL_GROUPS:
        count = trans_matrix[current_group][group]
        total_count = sum(trans_matrix[current_group].values())
        prob = (count + 1.0) / (total_count + len(ALL_GROUPS) * 1.0)
        probs[group] = prob
    recent_5 = groups[-5:]
    for group in ALL_GROUPS:
        if recent_5.count(group) >= 3: probs[group] *= 0.75
        elif recent_5.count(group) == 0: probs[group] *= 1.15
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    main_bets = [sorted_probs[0][0], sorted_probs[1][0]]
    defense = sorted_probs[2][0]
    kill = sorted_probs[-1][0]
    all_pool_nums = []
    for g in main_bets + [defense]:
        all_pool_nums.extend(TEMA_POOL[g])
    all_pool_nums = list(set(all_pool_nums))
    all_pool_nums.sort(key=lambda x: abs(x - 13.5))
    core_pool = all_pool_nums[:8]
    temas = random.sample(core_pool, min(4, len(core_pool)))
    return kill, main_bets, defense, sorted(temas)

def main():
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    records = []
    for row in data['data']:
        nums = [int(x) for x in row['number'].split('+')]
        total = int(sum(nums))
        records.append({
            'period': str(row['nbr']), 'nums': nums, 'sum': total,
            'type': ('大' if total >= 14 else '小') + ('单' if total % 2 else '双')
        })
    records.sort(key=lambda x: int(x['period']))
    
    latest = records[-1]
    next_period = str(int(latest['period']) + 1)
    res = get_7_0_prediction(records)
    
    output = {
        "latest": latest,
        "next_period": next_period,
        "prediction": {
            "kill": res[0], "main": res[1], "defense": res[2], "temas": res[3]
        } if res else None
    }
    
    with open('data.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False)

if __name__ == '__main__':
    main()
