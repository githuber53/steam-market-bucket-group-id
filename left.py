import json
from collections import Counter

name_path = r"data/cs2/names.json"

with open(name_path, "r", encoding="utf-8") as f:
    names = json.load(f)

total = 11849

# 收集所有 count_id
count_ids = [int(item["count_id"]) for item in names if "count_id" in item]

# 查重复
counter = Counter(count_ids)
duplicates = [cid for cid, c in counter.items() if c > 1]

# 查缺失
existing_ids = set(count_ids)
left_count_list = [i for i in range(total) if i not in existing_ids]

print("已有数量:", len(existing_ids))
print("缺失数量:", len(left_count_list))
print("重复数量:", len(duplicates))
print("\n缺失 count_id:")
print(left_count_list)
print("\n重复 count_id:")
print(duplicates)