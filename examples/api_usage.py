
import json
from pathlib import Path

from src.mapper_service import transform_single, transform_multi


# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# 读取 JSON 文件
def load_json(file_path):
    with open(PROJECT_ROOT / file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# 单源 JSON 转换示例
def example_single():
    source_data = {
        "studentId": 2002,
        "studentName": "Amy",
        "score": 88.5
    }

    mapping_spec = load_json("outputs/mapping_spec.json")
    source_schema = load_json("schemas/source_schema.json")
    target_schema = load_json("schemas/target_schema.json")

    result = transform_single(
        source_data=source_data,
        mapping_spec=mapping_spec,
        source_schema=source_schema,
        target_schema=target_schema
    )

    print("单源转换结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


# 多源 JSON 组装示例
def example_multi():
    sources = {
        "student_info": {
            "studentId": 2002,
            "studentName": "Amy"
        },
        "student_score": {
            "score": 88.5
        }
    }

    mapping_spec = load_json(
        "outputs/multi_source_mapping_spec.json"
    )

    schemas = {
        "student_info": load_json(
            "schemas/student_info_schema.json"
        ),
        "student_score": load_json(
            "schemas/student_score_schema.json"
        )
    }

    target_schema = load_json("schemas/target_schema.json")

    result = transform_multi(
        sources=sources,
        mapping_spec=mapping_spec,
        schemas=schemas,
        target_schema=target_schema
    )

    print("\n多源组装结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


# 运行示例
def main():
    example_single()
    example_multi()


if __name__ == "__main__":
    main()