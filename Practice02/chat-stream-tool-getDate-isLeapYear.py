import configparser
import json
import os
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
            if call["name"] == "getDate":
                output = subprocess.run("date /t & time /t", shell=True, capture_output=True, text=True).stdout
            else:
                year = json.loads(call["arguments"])["year"]
                output = f"{year} 是闰年" if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else f"{year} 不是闰年"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
