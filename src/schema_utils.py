import hashlib
import json


# 计算统一的 Schema 指纹
def schema_fingerprint(schema):
    canonical_json = json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()
