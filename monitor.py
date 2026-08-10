import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests

from channel_bot import build_channels, send_message
import iciba
import config as project_config

LEETCODE_GRAPHQL_URL = 'https://leetcode.cn/graphql/noj-go/'

HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Origin': 'https://leetcode.cn',
    'Referer': 'https://leetcode.cn/u/{}/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'authorization': ';',
    'content-type': 'application/json',
    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"'
}


def get_user_submission_calendar(name: str) -> Dict[str, int]:
    data = {
        "query": "query userProfileCalendar($userSlug: String!, $year: Int) {\n userCalendar(userSlug: $userSlug, year: $year) {\n streak\n totalActiveDays\n submissionCalendar\n activeYears\n monthlyMedals {\n name\n obtainDate\n category\n config {\n icon\n iconGif\n iconGifBackground\n }\n progress\n id\n year\n month\n }\n recentStreak\n }\n}",
        "variables": {"userSlug": name},
        "operationName": "userProfileCalendar"
    }
    response = requests.post(LEETCODE_GRAPHQL_URL, headers=HEADERS, data=json.dumps(data), timeout=20)
    response.raise_for_status()
    response_json = response.json()

    if 'errors' in response_json:
        raise RuntimeError(f"LeetCode API 返回错误: {response_json['errors']}")

    user_calendar = response_json.get('data', {}).get('userCalendar')
    if not user_calendar:
        raise RuntimeError(f"未获取到用户 {name} 的日历数据，请检查用户名是否正确")

    submission_calendar_str = user_calendar.get('submissionCalendar') or '{}'
    submission_calendar = json.loads(submission_calendar_str)
    return submission_calendar


def _today_start_timestamp() -> Tuple[int, str]:
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day)
    ts = int(today_midnight.timestamp())
    date_str = today_midnight.strftime('%Y-%m-%d')
    return ts, date_str


def get_today_submission(submission_calendar: Dict[str, int]) -> Tuple[str, int]:
    today_ts, today_str = _today_start_timestamp()
    key = str(today_ts)
    if key in submission_calendar:
        return today_str, int(submission_calendar[key])
    return today_str, 0


def _collect_users_data(users: List[str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for user in users:
        record: Dict[str, Any] = {"user": user}
        try:
            submission_calendar = get_user_submission_calendar(user)
            today_date, today_submissions = get_today_submission(submission_calendar)
            record["today_date"] = today_date
            record["today_submissions"] = int(today_submissions)
            record["last_date"] = today_date
            record["last_submissions"] = int(today_submissions)
            record["error"] = ""
        except Exception as e:
            print(f"[monitor] 获取用户 {user} 数据失败: {e}")
            _, today_str = _today_start_timestamp()
            record["today_date"] = today_str
            record["today_submissions"] = 0
            record["last_date"] = today_str
            record["last_submissions"] = 0
            record["error"] = str(e)
        results.append(record)
    return results


def _build_report_text(
    user_results: List[Dict[str, Any]],
    threshold: int,
    daily_sentence: str,
    name_map: Dict[str, str]
) -> str:
    sorted_results = sorted(
        user_results,
        key=lambda r: (
            -1 if (int(r.get("today_submissions", 0) or 0) >= threshold) else 0,
            -(int(r.get("today_submissions", 0) or 0)),
            r.get("user", "")
        ),
        reverse=False,
    )
    lines = []
    if daily_sentence:
        lines.append(daily_sentence)
        lines.append("")

    _, today_str = _today_start_timestamp()
    lines.append("===== LeetCode 每日监控报告 =====")
    lines.append(f"校验日期: {today_str}（仅校验当日提交）")
    lines.append(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"完成阈值: 当日提交 >= {threshold} 题")
    lines.append("")

    completed = [r for r in sorted_results if int(r.get("today_submissions", 0) or 0) >= threshold]
    uncompleted = [r for r in sorted_results if int(r.get("today_submissions", 0) or 0) < threshold]

    lines.append(f"✅ 已完成 ({len(completed)} 人):")
    for r in completed:
        display_name = project_config.format_display_name(r['user'], name_map)
        lines.append(f"  • {display_name}: 当日提交 {r.get('today_submissions', 0)} 题")
    lines.append("")

    lines.append(f"❌ 未完成 ({len(uncompleted)} 人):")
    for r in uncompleted:
        sub = int(r.get("today_submissions", 0) or 0)
        diff = threshold - sub
        display_name = project_config.format_display_name(r['user'], name_map)
        if r.get("error"):
            lines.append(f"  • {display_name}: 数据获取失败 - {r['error']}")
        else:
            lines.append(f"  • {display_name}: 当日提交 {sub} 题（还差 {diff} 题达到阈值）")
    lines.append("")

    lines.append("=================================")
    return "\n".join(lines)


def do_monitor(trigger_source: str = "manual") -> Dict[str, Any]:
    config = project_config.load_config()
    raw_users = config.get('users', [])
    user_slugs: List[str] = project_config.get_user_slugs(raw_users)
    name_map: Dict[str, str] = project_config.build_name_map(raw_users)
    threshold: int = int(config.get('completion_threshold', 1) or 1)
    channels_cfg = config.get('channels', {})

    if not user_slugs:
        print("[monitor] 配置中没有用户，跳过执行")
        return {"success": False, "reason": "empty_users"}

    user_results = _collect_users_data(user_slugs)

    try:
        daily_sentence = iciba.get_daily_sentence()
    except Exception as e:
        print(f"[monitor] 获取每日一句失败: {e}")
        daily_sentence = ""

    output_string = _build_report_text(user_results, threshold, daily_sentence, name_map)
    print("[monitor] 生成的报告:\n")
    print(output_string)

    channels = build_channels(channels_cfg)
    if channels:
        print(f"[monitor] 准备通过 {[c.name for c in channels]} 推送消息")
        channel_results = send_message(channels, output_string)
    else:
        print("[monitor] 未配置任何启用的推送渠道，跳过消息推送")
        channel_results = {}

    return {
        "success": True,
        "trigger_source": trigger_source,
        "executed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "users": user_slugs,
        "name_map": name_map,
        "threshold": threshold,
        "user_results": user_results,
        "channel_results": channel_results,
        "report": output_string,
    }


def main():
    do_monitor(trigger_source="monitor_direct")


if __name__ == '__main__':
    main()
