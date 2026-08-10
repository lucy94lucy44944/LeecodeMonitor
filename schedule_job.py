import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import schedule

import monitor
import config as project_config


_run_counter = 0
_max_runs: Optional[int] = None


def run_once(trigger_source: str = "manual") -> Dict[str, Any]:
    global _run_counter
    print(f"[{trigger_source}] 开始执行监控任务，时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（第 {_run_counter + 1} 次）")
    result = monitor.do_monitor(trigger_source=trigger_source)
    _run_counter += 1
    print(f"[{trigger_source}] 任务执行完毕，时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（累计 {_run_counter} 次）")

    if _max_runs is not None and _run_counter >= _max_runs:
        print(f"[max_runs] 已达到最大执行次数 {_max_runs} 次，程序自动退出。")
        _raise_exit_signal()
    return result


class _MaxRunsReached(Exception):
    pass


def _raise_exit_signal() -> None:
    raise _MaxRunsReached()


def _now_with_tz(tz_name: str) -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(timezone(timedelta(hours=8)))


def _run_interval(interval_seconds: int, trigger_source: str = "interval") -> None:
    global _run_counter
    print(f"[interval] 间隔定时模式已启动：每 {interval_seconds} 秒执行一次")
    if _max_runs is not None:
        print(f"[interval] 配置的最大执行次数: {_max_runs} 次")
    try:
        while True:
            run_once(trigger_source=trigger_source)
            time.sleep(interval_seconds)
    except _MaxRunsReached:
        return


def schedule_daily_job(hour: int, minute: int, timezone_name: str = "Asia/Shanghai", interval_seconds: Optional[int] = None) -> None:
    if interval_seconds is not None and interval_seconds > 0:
        _run_interval(interval_seconds, trigger_source="schedule_interval")
        return

    now = _now_with_tz(timezone_name)
    today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now > today:
        today += timedelta(days=1)

    next_run = today.strftime("%H:%M")
    print(f"[schedule] 每日定时任务已注册，执行时间: {next_run} (时区: {timezone_name})")
    if _max_runs is not None:
        print(f"[schedule] 配置的最大执行次数: {_max_runs} 次")

    def _schedule_trigger() -> None:
        run_once(trigger_source="schedule")
        if _max_runs is not None and _run_counter >= _max_runs:
            return schedule.CancelJob
        return None

    schedule.every().day.at(next_run).do(_schedule_trigger)

    try:
        while True:
            schedule.run_pending()
            if _max_runs is not None and _run_counter >= _max_runs:
                print(f"[schedule] 已达到最大执行次数 {_max_runs} 次，退出每日调度循环。")
                return
            if not schedule.get_jobs():
                return
            time.sleep(1)
    except _MaxRunsReached:
        return


def run_with_mode(config: Dict[str, Any]) -> None:
    global _max_runs
    exec_cfg = config.get("execution", {})
    mode = exec_cfg.get("mode", "both")
    run_on_startup = exec_cfg.get("run_on_startup", False)

    schedule_cfg = exec_cfg.get("schedule", {})
    hour = schedule_cfg.get("hour", 9)
    minute = schedule_cfg.get("minute", 0)
    tz_name = schedule_cfg.get("timezone", "Asia/Shanghai")
    interval_seconds = schedule_cfg.get("interval_seconds")
    if isinstance(interval_seconds, str) and interval_seconds.strip():
        try:
            interval_seconds = int(interval_seconds.strip())
        except Exception:
            interval_seconds = None
    if interval_seconds is not None and isinstance(interval_seconds, (int, float)):
        interval_seconds = max(1, int(interval_seconds))
    else:
        interval_seconds = None

    raw_max_runs = schedule_cfg.get("max_runs")
    if raw_max_runs is None or raw_max_runs == "":
        _max_runs = None
    else:
        try:
            _max_runs = max(1, int(raw_max_runs))
        except Exception:
            _max_runs = None

    print("[启动] 当前执行模式:", mode)
    print(f"[启动] 启动后立即执行: {'是' if run_on_startup else '否'}")
    if interval_seconds is not None:
        print(f"[启动] 调度模式: 间隔模式，每 {interval_seconds} 秒一次")
    else:
        print(f"[启动] 调度模式: 每日定时 {hour:02d}:{minute:02d}（{tz_name}）")
    if _max_runs is not None:
        print(f"[启动] 最大执行次数: {_max_runs} 次")

    if mode == "manual":
        if run_on_startup:
            run_once(trigger_source="manual_on_startup")
        print("[manual] 手动模式：如需执行，请直接运行 `python monitor.py` 或重新启动程序。")
        return

    if mode == "schedule":
        if run_on_startup:
            run_once(trigger_source="schedule_on_startup")
            if _max_runs is not None and _run_counter >= _max_runs:
                return
        schedule_daily_job(hour, minute, tz_name, interval_seconds)
        return

    if mode == "both":
        if run_on_startup:
            run_once(trigger_source="both_on_startup")
            if _max_runs is not None and _run_counter >= _max_runs:
                return
        print("[both] 同时启用定时/间隔模式；手动执行可直接运行 `python monitor.py`。")
        schedule_daily_job(hour, minute, tz_name, interval_seconds)
        return

    raise ValueError(f"未知的执行模式: {mode}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LeetCode 每日监控工具：支持手动触发 / 每日定时 / 间隔模式 / 最大执行次数限制"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="立即手动执行一次任务，忽略配置中的执行模式"
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "schedule", "both"],
        default=None,
        help="覆盖配置文件中的执行模式"
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=None,
        help="覆盖配置中的定时小时"
    )
    parser.add_argument(
        "--minute",
        type=int,
        default=None,
        help="覆盖配置中的定时分钟"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="覆盖配置中的间隔秒数（>0 则进入间隔模式），例如 --interval 5 表示每 5 秒一次"
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="覆盖配置中的最大执行次数（>0 生效），例如 --max-runs 5 表示总共跑 5 次就自动退出"
    )
    parser.add_argument(
        "--channels",
        type=str,
        default=None,
        help="覆盖启用的推送渠道，逗号分隔（如：feishu,dingding）"
    )
    return parser


def apply_cli_overrides(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    import copy
    cfg = copy.deepcopy(config)

    if args.mode is not None:
        cfg["execution"]["mode"] = args.mode

    sch = cfg.setdefault("execution", {}).setdefault("schedule", {})
    if args.hour is not None:
        sch["hour"] = args.hour
    if args.minute is not None:
        sch["minute"] = args.minute
    if args.interval is not None:
        sch["interval_seconds"] = max(1, int(args.interval))
    if args.max_runs is not None:
        sch["max_runs"] = max(1, int(args.max_runs))

    if args.channels:
        names = [c.strip() for c in args.channels.split(",") if c.strip()]
        if names:
            cfg["channels"]["enabled"] = names

    return cfg


def main() -> int:
    global _max_runs
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        base_config = project_config.load_config()
    except Exception as e:
        print(f"[启动] 加载配置失败: {e}")
        return 1

    config = apply_cli_overrides(base_config, args)
    project_config.save_config(config)

    if args.now:
        try:
            raw_max_runs = config.get("execution", {}).get("schedule", {}).get("max_runs")
            if raw_max_runs is not None and str(raw_max_runs).strip() != "":
                try:
                    _max_runs = max(1, int(raw_max_runs))
                except Exception:
                    _max_runs = None
        except Exception:
            _max_runs = None
        result = run_once(trigger_source="cli_now")
        return 0 if result.get("success", False) else 1

    try:
        run_with_mode(config)
        return 0
    except KeyboardInterrupt:
        print("\n[退出] 用户中断程序")
        return 0
    except Exception as e:
        print(f"[错误] 运行异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
