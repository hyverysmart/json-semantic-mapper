import io   #读取代码字符串
import keyword    #判断某个单词是不是 Python 关键字
import tokenize   #分析 Python 代码中的单词、符号等
import tkinter as tk
import json
from .code_executor import execute_code
from .workflow_runner import run_workflow
from tkinter import filedialog

# 创建代码编辑器窗口
root = tk.Tk()
# 设置窗口标题
root.title("Python 数据处理节点")
# 设置窗口大小
root.geometry("1000x800")
root.minsize(850,650)
root.configure(bg="#F4F6FA")
# 显示输入数据标题
input_label=tk.Label(root,text="输入Json 数据",font=("Arial",12),bg="#F4F6FA",fg="#1E293B")
input_label.pack(anchor="w",padx=20,pady=(15,5))
# 创建多行 JSON 输入框
input_text=tk.Text(root,height=7,font=("Consolas",11),bg="#F4F6FA",fg="#1E293B")
input_text.pack(fill="x",padx=20)
# 设置默认输入示例
input_text.insert("1.0",'{\n "angle":12.5\n}')
# 显示 Python 代码编辑区标题
code_label=tk.Label(root,text="Python 转换代码",font=("Arial",12),bg="#F4F6FA",fg="#1E293B")
code_label.pack(anchor="w",padx=20,pady=(15,5))
#创建代码编辑器容器
code_frame = tk.Frame(root,bg="#FFFFFF")
code_frame.pack(fill="both",padx=20)
# 创建多行代码编辑框
code_text=tk.Text(
    code_frame,
    height=10,
    font=("Consolas",11),
    bg="#FFFFFF",
    fg="#1E293B",
    insertbackground="#2563EB",
    relief="flat",
    wrap="none",
    bd=0,
    padx=15,
    pady=12)

# 创建行号显示区域
line_numbers = tk.Text(
    code_frame,
    width=4,
    height=10,
    font=("Consolas", 12),
    bg="#F1F5F9",
    fg="#64748B",
    relief="flat",
    bd=0,
    padx=5,
    pady=12,
    state="disabled"
)
line_numbers.pack(side="left", fill="y")
# 创建代码编辑器右侧的滚动条
scrollbar = tk.Scrollbar(
    code_frame,
    command=code_text.yview   #拖动滚动条时，让代码编辑框上下移动
)

# 滚动条放在最右侧
scrollbar.pack(side="right", fill="y")

# 代码编辑框放在行号和滚动条之间
code_text.pack(side="left", fill="both", expand=True)
# 设置行号居中显示
line_numbers.tag_configure("center", justify="center")

# 同步代码、行号和滚动条的位置
def sync_scroll(first, last):
    line_numbers.yview_moveto(first)
    scrollbar.set(first, last)

# 监听代码编辑区的滚动位置
code_text.configure(yscrollcommand=sync_scroll)

# 根据代码行数更新行号
def update_line_numbers():
    line_count = int(code_text.index("end-1c").split(".")[0])

    numbers = "\n".join(str(i) for i in range(1, line_count + 1))

    line_numbers.config(state="normal")
    line_numbers.delete("1.0", tk.END)
    line_numbers.insert("1.0", numbers,"center")
    line_numbers.config(state="disabled")
# 设置 Python 关键字颜色
code_text.tag_configure("keyword", foreground="#7C3AED")
# 设置字符串和注释的颜色
code_text.tag_configure("string", foreground="#059669")
code_text.tag_configure("comment", foreground="#64748B")

# 高亮 Python 关键字
def highlight_syntax():
    code_text.tag_remove("keyword", "1.0", tk.END)
    # 清除之前的字符串和注释颜色
    code_text.tag_remove("string", "1.0", tk.END)
    code_text.tag_remove("comment", "1.0", tk.END)
    source = code_text.get("1.0", "end-1c")

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)

        for token in tokens:
            start = f"{token.start[0]}.{token.start[1]}"
            end = f"{token.end[0]}.{token.end[1]}"

            # 高亮 Python 关键字
            if token.type == tokenize.NAME and keyword.iskeyword(token.string):
                code_text.tag_add("keyword", start, end)

            # 高亮字符串
            elif token.type == tokenize.STRING:
                code_text.tag_add("string", start, end)

            # 高亮注释
            elif token.type == tokenize.COMMENT:
                code_text.tag_add("comment", start, end)

    except (tokenize.TokenError, IndentationError):
        pass

# 代码内容变化时更新行号
def on_code_modified(event):
    if code_text.edit_modified():
        update_line_numbers()
        highlight_syntax()
        code_text.edit_modified(False)

code_text.bind("<<Modified>>", on_code_modified)
update_line_numbers()
highlight_syntax()
# 读取工作流所需的 JSON 配置
def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

# 执行用户编写的 Python 代码
def run_code():
    output_text.delete("1.0", tk.END)

    # 清空上一次的运行日志
    log_text.delete("1.0", tk.END)
    try:
        input_data = json.loads(input_text.get("1.0", "end-1c"))
        code = code_text.get("1.0", "end-1c")

        # 勾选时，执行完整 JSON 工作流
        if workflow_enabled.get():
            mapping_spec = load_json("outputs/mapping_spec.json")
            source_schema = load_json("schemas/source_schema.json")
            target_schema = load_json("schemas/target_schema.json")

            # 执行完整工作流，并获取运行日志
            result, logs = run_workflow(
                input_data,
                mapping_spec,
                source_schema,
                target_schema,
                code,
                return_logs=True
            )

            # 在界面中显示运行日志
            log_text.insert("1.0", logs if logs else "（无运行日志）")

        # 未勾选时，直接执行 Python 代码
        else:
            result, logs = execute_code(
                input_data,
                code,
                return_logs=True
            )

            # 将 print 输出显示到日志框
            log_text.insert("1.0", logs if logs else "（无运行日志）")
        output_text.insert(
            tk.END,
            json.dumps(result,ensure_ascii=False, indent=2)
        )

    # 捕获执行过程中的错误
    except Exception as error:
        output_text.insert(
            tk.END,
            f"执行失败：{error}",
            "error"
        )

# 是否启用完整工作流
workflow_enabled = tk.BooleanVar(value=True)

# 保存编辑器中的 Python 代码
def save_code():
    path = filedialog.asksaveasfilename(
        defaultextension=".py",
        filetypes=[("Python 文件", "*.py")]
    )

    if not path:
        return

    code = code_text.get("1.0", "end-1c")

    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(code)
    except OSError as error:
        messagebox.showerror("保存失败", str(error))

# 打开已有的 Python 代码
def open_code():
    path = filedialog.askopenfilename(
        filetypes=[("Python 文件", "*.py")]
    )

    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as file:
            code = file.read()
    except (OSError, UnicodeError) as error:
        messagebox.showerror("打开失败", str(error))
        return

    code_text.delete("1.0", tk.END)
    code_text.insert("1.0", code)

# 根据运行模式切换示例数据
def switch_example():
    input_text.delete("1.0", tk.END)
    code_text.delete("1.0", tk.END)

    if workflow_enabled.get():
        input_text.insert(
            "1.0",
            '{"studentId": 1001, "studentName": "Tom", "score": 95.5}'
        )
        code_text.insert(
            "1.0",
            'output = dict(input_data)\noutput["grade"] = round(input_data["grade"])'
        )
    else:
        input_text.insert("1.0", '{"angle": 12.5}')
        # 设置度转度分秒的示例代码
        code_text.insert(
            "1.0",
            'angle = input_data["angle"]\n'
            'degree = int(angle)\n'
            'minute = int((angle - degree) * 60)\n'
            'second = round(((angle - degree) * 60 - minute) * 60, 2)\n'
            'output = {"degree": degree, "minute": minute, "second": second}'
        )

# 创建工作流模式选择框
workflow_check = tk.Checkbutton(
    root,
    text="先执行 JSON 字段映射",
    variable=workflow_enabled,
    command=switch_example
)

workflow_check.pack(anchor="w", padx=20, pady=5)
switch_example()

# 创建运行按钮
run_button = tk.Button(
    root,
    text="▶ 运行代码",
    command=run_code,
    font=("Microsoft Yahei UI",11,"bold"),
    bg=("#2563EB"),
    fg=("#FFFFFF"),
    activebackground="#1D4ED8",   #按下按钮时显示深蓝色
    activeforeground="#FFFFFF",   #按下时文字认为白色
    relief="flat",  #去掉默认立体边框
    bd=0,   #边框宽度为0
    padx=25,
    pady=10,
    cursor="hand2"   #鼠标移到按钮上变成手形
)
run_button.pack(pady=15)

# 创建文件操作按钮区域
file_frame = tk.Frame(root, bg="#F4F6FA")
file_frame.pack(pady=5)

# 打开代码按钮
open_button = tk.Button(
    file_frame,
    text="打开代码",
    command=open_code,
    font=("Microsoft YaHei UI", 10),
    padx=15,
    pady=5
)
open_button.pack(side="left", padx=5)

# 保存代码按钮
save_button = tk.Button(
    file_frame,
    text="保存代码",
    command=save_code,
    font=("Microsoft YaHei UI", 10),
    padx=15,
    pady=5
)
save_button.pack(side="left", padx=5)

# 显示执行结果标题
output_label = tk.Label(root, text="执行结果", font=("Arial", 12))

# 创建结果显示框
output_text = tk.Text(
    root,
    height=7,
    font=("Consolas", 12),
    bg="#F8FAFC",
    fg="#0F172A",
    relief="flat",
    bd=0,
    padx=15,
    pady=12,
    wrap="word"    #长文本尽量在单词边界自动换行
    )

# 创建运行日志区域
log_frame = tk.Frame(root, bg="#F4F6FA")
log_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 10))

# 创建运行日志标题
log_label = tk.Label(
    log_frame,
    text="运行日志",
    font=("Microsoft YaHei UI", 11, "bold"),
    bg="#F4F6FA",
    fg="#1E293B"
)
log_label.pack(anchor="w", pady=(5, 5))

# 创建日志显示框
log_text = tk.Text(
    log_frame,
    height=3,
    font=("Consolas", 11),
    bg="#FFFFFF",
    fg="#475569",
    relief="flat",
    padx=12,
    pady=8
)
log_text.pack(fill="x")

# 将执行结果区域固定在窗口底部
output_text.pack(
    side="bottom",
    fill="x",
    padx=20,
    pady=(0, 15)
)
# 设置错误信息为红色
output_text.tag_configure(
    "error",
    foreground="#DC2626"
)
# 将结果标题放在结果框上方
output_label.pack(
    side="bottom",
    anchor="w",
    padx=20,
    pady=(10, 5)
)

# 使用 Ctrl + Enter 快捷键运行代码
def run_code_shortcut(event):
    run_code()
    return "break"

# 绑定快捷键
root.bind("<Control-Return>", run_code_shortcut)
# 启动图形界面
root.mainloop()