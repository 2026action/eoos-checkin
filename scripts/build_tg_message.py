#!/usr/bin/env python3
"""构造 Telegram HTML 通知内容, 打印到 stdout 供 workflow 消费."""
import os, html, sys


def main() -> int:
    emoji = os.environ.get("EMOJI", "")
    title = os.environ.get("TITLE", "EOOS 签到")
    bj_time = os.environ.get("BJ_TIME", "")
    event = os.environ.get("EVENT_NAME", "")
    status_line = os.environ.get("STATUS_LINE", "").strip()
    reward_line = os.environ.get("REWARD_LINE", "").strip()
    run_url = os.environ.get("RUN_URL", "")

    lines = [
        f"{emoji} <b>{html.escape(title)}</b>",
        f"⏰ {html.escape(bj_time)}",
        f"🎯 触发: {html.escape(event)}",
    ]
    if status_line:
        lines.append(f"📊 状态: <code>{html.escape(status_line)}</code>")
    if reward_line:
        lines.append(f"💰 奖励: <b>{html.escape(reward_line)}</b>")
    lines.append(f'🔗 <a href="{html.escape(run_url)}">查看运行详情</a>')
    sys.stdout.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
