import unittest
from src.code_executor import execute_code


# 测试 Python 代码执行器
class TestCodeExecutor(unittest.TestCase):

    # 测试正常的数据转换
    def test_basic_conversion(self):
        input_data = {"angle": 12.5}
        code = 'output = input_data["angle"] * 60'

        result = execute_code(input_data, code)

        self.assertEqual(result, 750.0)

    # 测试执行结果和运行日志
    def test_execution_logs(self):
        input_data = {"angle": 12.5}

        code = """
print("开始转换")
output = input_data["angle"] * 60
print("转换完成")
"""

        result, logs = execute_code(
            input_data,
            code,
            return_logs=True
        )

        self.assertEqual(result, 750.0)
        self.assertIn("开始转换", logs)
        self.assertIn("转换完成", logs)

    # 测试用户没有定义 output 的情况
    def test_missing_output(self):
        input_data = {"angle": 12.5}
        code = 'angle = input_data["angle"]'

        with self.assertRaises(ValueError):
            execute_code(input_data, code)


if __name__ == "__main__":
    unittest.main()