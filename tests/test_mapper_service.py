
import copy
import json
from pathlib import Path

import pytest

from src.mapper_service import transform_single, transform_multi


# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# 读取测试需要的 JSON 文件
def load_json(file_path):
    with open(PROJECT_ROOT / file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# 准备单源转换测试数据
@pytest.fixture
def single_data():
    source_data = {
        "studentId": 2002,
        "studentName": "Amy",
        "score": 88.5
    }

    mapping_spec = load_json("outputs/mapping_spec.json")
    source_schema = load_json("schemas/source_schema.json")
    target_schema = load_json("schemas/target_schema.json")

    return source_data, mapping_spec, source_schema, target_schema


# 准备多源组装测试数据
@pytest.fixture
def multi_data():
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

    return sources, mapping_spec, schemas, target_schema


# 测试正常单源转换
def test_single_transform_success(single_data):
    source_data, spec, source_schema, target_schema = single_data

    result = transform_single(
        source_data,
        spec,
        source_schema,
        target_schema
    )

    assert result == {
        "id": 2002,
        "name": "Amy",
        "grade": 88.5
    }


# 测试未经审核的单源映射规则
def test_single_unapproved_spec(single_data):
    source_data, spec, source_schema, target_schema = single_data

    spec = copy.deepcopy(spec)
    spec["review_status"] = "pending"

    with pytest.raises(ValueError, match="尚未通过人工审核"):
        transform_single(
            source_data,
            spec,
            source_schema,
            target_schema
        )


# 测试单源数据类型错误
def test_single_invalid_source(single_data):
    source_data, spec, source_schema, target_schema = single_data

    source_data = copy.deepcopy(source_data)
    source_data["studentId"] = "2002"

    with pytest.raises(ValueError):
        transform_single(
            source_data,
            spec,
            source_schema,
            target_schema
        )


# 测试单源 Schema 指纹发生变化
def test_single_schema_changed(single_data):
    source_data, spec, source_schema, target_schema = single_data

    source_schema = copy.deepcopy(source_schema)
    source_schema["description"] = "修改后的源 Schema"

    with pytest.raises(ValueError, match="指纹"):
        transform_single(
            source_data,
            spec,
            source_schema,
            target_schema
        )


# 测试正常多源组装
def test_multi_transform_success(multi_data):
    sources, spec, schemas, target_schema = multi_data

    result = transform_multi(
        sources,
        spec,
        schemas,
        target_schema
    )

    assert result == {
        "id": 2002,
        "name": "Amy",
        "grade": 88.5
    }


# 测试未经审核的多源映射规则
def test_multi_unapproved_spec(multi_data):
    sources, spec, schemas, target_schema = multi_data

    spec = copy.deepcopy(spec)
    spec["review_status"] = "pending"

    with pytest.raises(ValueError, match="尚未通过人工审核"):
        transform_multi(
            sources,
            spec,
            schemas,
            target_schema
        )


# 测试多源数据缺失
def test_multi_missing_source(multi_data):
    sources, spec, schemas, target_schema = multi_data

    sources = copy.deepcopy(sources)
    del sources["student_score"]

    with pytest.raises(ValueError, match="缺少数据源"):
        transform_multi(
            sources,
            spec,
            schemas,
            target_schema
        )


# 测试多源数据类型错误
def test_multi_invalid_source(multi_data):
    sources, spec, schemas, target_schema = multi_data

    sources = copy.deepcopy(sources)
    sources["student_score"]["score"] = "88.5"

    with pytest.raises(ValueError):
        transform_multi(
            sources,
            spec,
            schemas,
            target_schema
        )


# 测试多源 Schema 指纹发生变化
def test_multi_schema_changed(multi_data):
    sources, spec, schemas, target_schema = multi_data

    schemas = copy.deepcopy(schemas)
    schemas["student_score"]["description"] = "修改后的成绩 Schema"

    with pytest.raises(ValueError, match="指纹"):
        transform_multi(
            sources,
            spec,
            schemas,
            target_schema
        )


# 测试多源目标字段重复写入
def test_multi_duplicate_target(multi_data):
    sources, spec, schemas, target_schema = multi_data

    spec = copy.deepcopy(spec)
    spec["mappings"][2]["target_path"] = "$.id"

    with pytest.raises(ValueError, match="目标字段冲突"):
        transform_multi(
            sources,
            spec,
            schemas,
            target_schema
        )