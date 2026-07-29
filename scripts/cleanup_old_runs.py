#!/usr/bin/env python3
"""列出本 workflow 除当前 run 外、按时间倒序保留最新 N 条外的所有 run id。

输入:
  /tmp/runs.json   来自 GitHub API list workflow runs
  env CUR          当前 run id (排除自己)
  env WF           workflow name (匹配 run.name)
  env KEEP         保留数量 (默认 1, 加上当前正在跑的这条 = 共 2 条)

输出:
  每行一个待删除的 run id 到 stdout
"""
import json
import os
import sys


def main() -> int:
    try:
        with open("/tmp/runs.json", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.stderr.write("runs.json missing\n")
        return 0

    cur = os.environ.get("CUR", "")
    wf = os.environ.get("WF", "")
    keep = int(os.environ.get("KEEP", "1"))

    runs = [
        r for r in data.get("workflow_runs", [])
        if r.get("name") == wf and str(r.get("id")) != cur
    ]
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    for r in runs[keep:]:
        print(r["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
