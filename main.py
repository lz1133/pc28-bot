import urllib.request
import json
import random
import time
import os
from collections import defaultdict

API_URL = "https://pc28.help/api/kj.json?nbr=300"
ALL_GROUPS = ['大单', '大双', '小单', '小双']
TEMA_POOL = {
    "小双": [0, 2, 4, 6, 8, 10, 12], "小单": [1, 3, 5, 7, 9, 11, 13],
    "大双": [14, 16, 18, 20, 22, 24, 26], "大单": [15, 17, 19, 21, 23, 25, 27]
}
STATE_FILE = 'state.json'

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

def fetch_data():
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f: return json.load(f)
    return {"preds": {}}

def main():
    data = None
    for i in range(3):
        try:
            data = fetch_data()
            break
        except Exception:
            time.sleep(3)
            
    if not data or 'data' not in data: return
        
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
    state = load_state()
    
    # 验证之前的预测
    for r in records:
        p = state['preds'].get(r['period'])
        if p and p.get('actual') is None:
            p['actual'] = r['type']
            p['mainHit'] = 1 if r['type'] in p['main'] else 0
            p['defHit'] = 1 if r['type'] == p['defense'] else 0
            p['temaHit'] = 1 if r['sum'] in p['temas'] else 0
            
    # 统计胜率
    done = [p for p in state['preds'].values() if p.get('actual') is not None]
    stats = {"total": len(done), "main": 0, "def": 0, "tema": 0}
    for p in done:
        stats['main'] += p['mainHit']
        stats['def'] += p['defHit']
        stats['tema'] += p['temaHit']
    
    # 生成新预测
    res = get_7_0_prediction(records)
    if res and next_period not in state['preds']:
        state['preds'][next_period] = {
            "kill": res[0], "main": res[1], "defense": res[2], "temas": res[3]
        }
        
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
        
    # 把结果打包给网页
    output = {
        "latest": latest,
        "next_period": next_period,
        "prediction": state['preds'].get(next_period),
        "stats": stats,
        "last_verify": state['preds'].get(latest['period'])
    }
    
    with open('data.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False)

if __name__ == '__main__':
    main()