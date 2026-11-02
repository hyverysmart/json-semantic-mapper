import copy
import pytest

from src.multi_source_assembler import assemble_sources


# 准备测试数据
@pytest.fixture
def sample_data():
    sources = {
        "student_info": {
            "studentId": 1001,
            "studentName": "Tom"
        },
        "student_score": {
            "score": 95.5
        }
    }

    mapping_spec = {
        "mappings": [
            {
                "source_id": "student_info",
                "source_path": "$.studentId",
                "target_path": "$.id"
            },
            {
                "source_id": "student_info",
                "source_path": "$.studentName",
                "target_path": "$.name"
            },
            {
                "source_id": "student_score",
                "source_path": "$.score",
                "target_path": "$.grade"
            }
        ]
    }

    return sources, mapping_spec


# 测试正常的双源组装
def test_normal_assembly(sample_data):
    sources, spec = sample_data

    result = assemble_sources(sources, spec)

    assert result == {
        "id": 1001,
        "name": "Tom",
        "grade": 95.5
    }


# 测试不存在的数据源
def test_missing_source(sample_data):
    sources, spec = sample_data
    spec = copy.deepcopy(spec)

    spec["mappings"][0]["source_id"] = "student_address"

    with pytest.raises(ValueError, match="数据源不存在"):
        assemble_sources(sources, spec)


# 测试重复写入目标字段
def test_duplicate_target(sample_data):
    sources, spec = sample_data
    spec = copy.deepcopy(spec)

    spec["mappings"][2]["target_path"] = "$.id"

    with pytest.raises(ValueError, match="目标字段冲突"):
        assemble_sources(sources, spec)


# 测试缺失源字段
def test_missing_field(sample_data):
    sources, spec = sample_data
    spec = copy.deepcopy(spec)

    spec["mappings"][2]["source_path"] = "$.examScore"

    with pytest.raises(ValueError, match="源字段不存在"):
        assemble_sources(sources, spec)


# 测试父子目标路径冲突
def test_nested_path_conflict(sample_data):
    sources, spec = sample_data
    spec = copy.deepcopy(spec)

    spec["mappings"][0]["target_path"] = "$.student"
    spec["mappings"][1]["target_path"] = "$.student.name"

    with pytest.raises(ValueError, match="目标字段冲突"):
        assemble_sources(sources, spec)
