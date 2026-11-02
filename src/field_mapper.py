import json

with open("outputs/source_catalog.json","r",encoding="utf-8")as file:
    source_catalog=json.load(file)

with open("outputs/target_catalog.json","r",encoding="utf-8")as file:
    target_catalog=json.load(file)

print("源字段：")
for field in source_catalog:
    print(field["name"],field["type"],field["description"])

print("\n目标字段：")
for field in target_catalog:
    print(field["name"],field["type"],field["description"])


def match_fields(source_catalog, target_catalog):
    matches = []

    for target_field in target_catalog:
        for source_field in source_catalog:

            if source_field["type"] != target_field["type"]:
                continue

            if source_field["name"] == target_field["name"]:
                matches.append({
                    "source": source_field["path"],
                    "target": target_field["path"],
                    "reason": "字段名称相同"
                })

            elif source_field["description"] == target_field["description"] \
                    and source_field["description"] != "无描述":

                matches.append({
                    "source": source_field["path"],
                    "target": target_field["path"],
                    "reason": "字段描述相同"
                })

    return matches

matches = match_fields(source_catalog, target_catalog)

print("\n候选字段匹配结果：")

for match in matches:
    print(
        match["source"],
        "→",
        match["target"],
        "原因：",
        match["reason"]
    )

matched_targets = set()

for match in matches:
    matched_targets.add(match["target"])

unmatched_targets=[]

print("\n未匹配的目标字段：")

for target_field in target_catalog:
    if target_field["path"] not in matched_targets:
        unmatched_targets.append(target_field)
        print(
            target_field["path"],
            target_field["description"]
        )


with open("outputs/candidate_mappings.json", "w", encoding="utf-8") as file:
    json.dump(matches, file, ensure_ascii=False, indent=2)

with open("outputs/unmatched_targets.json", "w", encoding="utf-8") as file:
    json.dump(unmatched_targets, file, ensure_ascii=False, indent=2)

print("\n候选映射结果已保存")
print("未匹配字段已保存")
