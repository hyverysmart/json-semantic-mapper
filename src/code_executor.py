import json
import subprocess
import sys

# 执行用户编写的数据转换代码
def execute_code(input_data,code,return_logs=False):
    if not isinstance(code,str) or not code.strip():
        raise ValueError("代码必须是非空字符串")
    input_json = json.dumps(input_data,ensure_ascii=False)
    runner = """
import json
import sys
import io
from contextlib import redirect_stdout

input_data = json.loads(sys.stdin.read())
user_code = sys.argv[1]

variables = {
    "input_data": input_data
}

# 创建日志缓冲区
log_buffer = io.StringIO()

# 收集用户代码中的 print 输出
with redirect_stdout(log_buffer):
    exec(user_code, variables, variables)

# 检查用户是否提供 output
if "output" not in variables:
    raise ValueError("用户代码没有定义 output")
# 同时返回转换结果和运行日志
response = {
    "output": variables["output"],
    "logs": log_buffer.getvalue()
}
# 只将最终 JSON 结果输出给主程序
print(json.dumps(response, ensure_ascii=False))
"""

    try:
        result = subprocess.run(
        [sys.executable,"-c",runner,code],
        input=input_json,
        capture_output=True,
        text=True,
        timeout=3
    )
    except subprocess.TimeoutExpired:
        raise ValueError("代码执行超时，超时3秒")

    if result.returncode != 0:
        raise ValueError(
            f"代码执行失败:{result.stderr.strip()}"
        )
    # 解析子进程返回的数据
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise ValueError(f"代码输出不是合法 JSON，实际输出：{repr(result.stdout)}")

    # 根据需要决定是否返回运行日志
    if return_logs:
        return response["output"], response["logs"]

    return response["output"]
