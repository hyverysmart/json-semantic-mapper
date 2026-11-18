from src.code_executor import execute_code

input_data = {
    "angle" : 12.5
}

code="""
angle = input_data["angle"]

degree = int(angle)
minutes = (angle - degree) * 60
minute = int(minutes)
second = round((minutes - minute) * 60, 2)

output = {
    "degree": degree,
    "minute": minute,
    "second": second
}
"""

result = execute_code(input_data,code)

print("转换结果：")
print(result)