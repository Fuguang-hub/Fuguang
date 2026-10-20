import configparser
import json
import mimetypes
import os
import shutil
import subprocess
from openai import OpenAI

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "config.ini"), encoding="utf-8")

client = OpenAI(
    api_key=config["llm"]["api_key"],
    base_url=config["llm"]["base_url"],
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "getDate",
            "description": "获取当前电脑的日期和时间",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "isLeapYear",
            "description": "判断一个年份是否为闰年",
            "parameters": {
                "type": "object",
                "properties": {"year": {"type": "integer", "description": "要判断的年份"}},
                "required": ["year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getCwd",
            "description": "获取当前工作目录",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listDir",
            "description": "列出指定目录下的所有文件和子目录",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "目录路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getFileType",
            "description": "获取指定文件的文件类型",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "readFile",
            "description": "读取指定纯文本文件的内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "createFile",
            "description": "在指定目录下创建一个新的空文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir": {"type": "string", "description": "目录路径"},
                    "name": {"type": "string", "description": "文件名"},
                },
                "required": ["dir", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "editFile",
            "description": "编辑指定纯文本文件的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "新的文件内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "createDir",
            "description": "创建新目录",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "目录路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deleteDir",
            "description": "删除目录（包括非空目录）",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "目录路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deleteFile",
            "description": "删除文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "renamePath",
            "description": "重命名文件或目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "原路径"},
                    "dst": {"type": "string", "description": "新路径"},
                },
                "required": ["src", "dst"],
            },
        },
    },
]

messages = []

while True:
    question = input("请输入你的问题：")
    messages.append({"role": "user", "content": question})

    while True:
        stream = client.chat.completions.create(
            model=config["llm"]["model"],
            messages=messages,
            tools=tools,
            stream=True,
        )

        reply = ""
        calls = {}
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                reply += delta.content
            for call in delta.tool_calls or []:
                if call.index not in calls:
                    calls[call.index] = {"id": call.id, "name": call.function.name, "arguments": ""}
                calls[call.index]["arguments"] += call.function.arguments or ""

        if not calls:
            print()
            messages.append({"role": "assistant", "content": reply})
            break

        messages.append(
            {
                "role": "assistant",
                "content": reply,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["name"], "arguments": call["arguments"]},
                    }
                    for call in calls.values()
                ],
            }
        )
        for call in calls.values():
            name = call["name"]
            args = json.loads(call["arguments"] or "{}")
            if name == "getDate":
                output = subprocess.run("date /t & time /t", shell=True, capture_output=True, text=True).stdout
            elif name == "isLeapYear":
                output = f"{args['year']} 是闰年" if args["year"] % 4 == 0 and (args["year"] % 100 != 0 or args["year"] % 400 == 0) else f"{args['year']} 不是闰年"
            elif name == "getCwd":
                output = os.getcwd()
            elif name == "listDir":
                output = "\n".join(os.listdir(args["path"]))
            elif name == "getFileType":
                output = mimetypes.guess_type(args["path"])[0] or os.path.splitext(args["path"])[1] or "未知类型"
            elif name == "readFile":
                output = open(args["path"], encoding="utf-8").read()
            elif name == "createFile":
                output = os.path.join(args["dir"], args["name"])
                open(output, "w", encoding="utf-8").close()
            elif name == "editFile":
                open(args["path"], "w", encoding="utf-8").write(args["content"])
                output = args["path"]
            elif name == "createDir":
                os.makedirs(args["path"], exist_ok=True)
                output = args["path"]
            elif name == "deleteDir":
                shutil.rmtree(args["path"])
                output = args["path"]
            elif name == "deleteFile":
                os.remove(args["path"])
                output = args["path"]
            elif name == "renamePath":
                os.rename(args["src"], args["dst"])
                output = f"{args['src']} -> {args['dst']}"
            else:
                output = f"未知工具：{name}"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
