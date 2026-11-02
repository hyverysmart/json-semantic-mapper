import pytest
from src.json_transformer import validate_result

@pytest.fixture
def target_schema():
    return {
        "type":"object",
        "properties":{
            "id":{"type":"integer"},
            "name":{"type":"string"},
            "grade":{"type":"number"},
        },
        "required":["id","name","grade"]
    }

#检查类型错误
def test_invalid_target_type(target_schema):

    invalid_data={
        "id":"1001",
        "name":"Tom",
        "grade":95.5
    }

    # 错误数据：预期抛出异常
    with pytest.raises(ValueError):
        validate_result(invalid_data,target_schema)

#检查缺少必填字段
def test_missing_required_field(target_schema):

    invalid_data={
        "id":1001,
        "name":"Tom",
    }

    with pytest.raises(ValueError):
        validate_result(invalid_data,target_schema)

def test_valid_target_data(target_schema):

    valid_data={
        "id":1001,
        "name":"Tom",
        "grade":95.5
    }
    # 正确数据：预期不抛出异常
    validate_result(valid_data,target_schema)

#测试嵌套json数据是否存在错误
def test_invalid_nested_data():
    nested_schema={
        "type":"object",
        "properties":{
            "student":{
                "type":"object",
                "properties":{
                    "id":{"type":"integer"},
                    "name":{"type":"string"}
                },
                "required":["id","name"]
            },
            "grade":{"type":"number"}
        },
        "requires":["student","grade"]
    }

    invalid_data={
        "student":{
            "id":"1001",
            "name":"Tom"
        },
        "grade":95.5
    }

    with pytest.raises(ValueError):
        validate_result(invalid_data,nested_schema)

#测试json数组中的元素是否存在错误
def test_invalid_array_item():
    array_schema={
        "type": "object",
        "properties": {
            "student": {
                "type": "array",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"]
            },
            "grade": {"type": "number"}
        },
        "requires": ["student", "grade"]
}

    invalid_data={
        "student":[
            {"id":1001,"name":"Tom"},
            {"id":"1002","name":"Amy"}
        ]
    }

    with pytest.raises(ValueError):
        validate_result(invalid_data,array_schema)

#测试数组元素缺少字段
def test_missing_array_item_field():
    array_schema = {
        "type": "object",
        "properties": {
            "students": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"}
                    },
                    "required": ["id", "name"]
                }
            }
        },
        "required": ["students"]
    }

    invalid_data={
        "students":[
            {"id":1001,"name":"Tom"},
            {"id":1002}
        ]
    }

    with pytest.raises(ValueError,match="缺少必填字段"):
        validate_result(invalid_data,array_schema)

#测试数组Schema缺少items定义
def test_array_missing_items():
    invalid_schema={
        "type":"array"
    }

    data=[1001,1002,1003]

    with pytest.raises(ValueError,match="缺少有效 items 定义"):
        validate_result(data,invalid_schema)