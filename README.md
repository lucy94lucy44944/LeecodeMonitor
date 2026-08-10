# LeetCode 每日监控系统 —— 完整使用与部署报告

---

## 一、项目功能总览

本项目用于**自动监控 LeetCode 中文站用户每天的刷题提交情况**，并将统计结果按群消息推送到企业协作平台，适用于班级、学习小组互相监督每天打卡。

### 1.1 核心监控能力
- 批量监控多个 LeetCode 用户
- **仅校验当日（当前自然日）提交数据**：不会误判历史做题记录
- 可自定义「每日完成阈值」（默认每天 ≥ 1 题算完成）
- 自动按「已完成 / 未完成」分组统计
- 每条消息显示「用户名（真实姓名）」+ 当日提交题数 + 距离阈值的差值
- 报告头部展示金山词霸「每日一句」英语鸡汤

### 1.2 执行模式（4 种，可自由切换）
| 模式 | 说明 | 配置项 |
|---|---|---|
| 立即手动执行 | 每次运行立即跑一次，适合临时催作业 / 调试 | `execution.mode = "manual"` + 命令行加 `--now` |
| 每日固定时间自动执行 | 每天某个固定时刻（例如 22:30）自动跑 1 次 | `mode = "schedule"` + `hour/minute` |
| 固定间隔连续执行 | 每 N 秒跑一次，可总共跑 M 次就停，方便测试自动连发 | `schedule.interval_seconds = 5` + `schedule.max_runs = 5` |
| 双模式同时开启 | 支持「立即执行一次」+「之后按定时 / 间隔」组合 | `mode = "both"` + `run_on_startup = true` |

### 1.3 消息推送平台
- 主支持：**飞书（Lark）群自定义机器人**（Webhook + 可选签名校验）
- 预留扩展能力（框架已搭好，后续补配置即可）：
  - 钉钉自定义机器人
  - Telegram Bot
  - 微信群机器人（企业微信 Webhook）
  - Facebook Messenger

---

## 二、本地快速启动（在你自己电脑上跑）

### 2.1 环境准备
1. 安装 Python 3.8 及以上版本（推荐 3.10+）
2. 进入项目目录并安装依赖：
   ```powershell
   cd e:\gitclon\leetcode-monitor
   pip install -r requirements.txt
   ```

### 2.2 修改本地配置文件 config.json
所有本地设置都在 **config.json** 里改，打开即可。下面是最常用的几项：

```json
{
  "users": [
    {"slug": "HU3783TekW",  "real_name": "啥子"}
  ],
  "completion_threshold": 1,
  "execution": {
    "mode": "both",
    "run_on_startup": true,
    "schedule": {
      "hour": 9,
      "minute": 0,
      "timezone": "Asia/Shanghai",
      "interval_seconds": null,
      "max_runs": null
    }
  },
  "channels": {
    "enabled": ["feishu"],
    "feishu": {
      "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/你的飞书机器人token",
      "secret": "",
      "msg_type": "text"
    }
  }
}
```

#### 每一项说明：
| 配置项 | 在哪 | 你要怎么填 |
|---|---|---|
| `users[].slug` | config.json 第 2~4 行 | LeetCode 个人主页 URL `/u/xxx` 里的 `xxx` 那段，**大小写敏感** |
| `users[].real_name` | 同上 | 你要在群里显示的真实姓名（会自动拼写成「HU3783TekW（啥子）」）|
| `completion_threshold` | 第 5 行 | 每天多少题才算完成，默认 1 题 |
| `execution.mode` | 第 7 行 | `"manual"` 只手动 / `"schedule"` 只定时 / `"both"` 两者都要 |
| `execution.run_on_startup` | 第 8 行 | `true` = 程序一启动先立刻跑一次再等定时 |
| `schedule.hour / minute` | 第 10、11 行 | 每日固定时间跑的「时:分」，24 小时制 |
| `schedule.interval_seconds` | 第 13 行 | 填数字（如 5）= 每 5 秒一次；`null` = 用每日定时 |
| `schedule.max_runs` | 第 14 行 | 填数字（如 5）= 总共跑 5 次就自动退出；`null` = 无限次 |
| `channels.enabled` | 第 16 行 | 默认 `["feishu"]`，想多渠道就写 `["feishu","dingding"]` |
| `feishu.webhook_url` | 第 18 行 | 飞书群 → 群设置 → 群机器人 → 自定义机器人 → 复制的完整 URL |
| `feishu.secret` | 第 19 行 | 如果机器人设置了「签名校验」填这里，没开就保持 `""` |

#### 关于如何找到 LeetCode slug：
登录 leetcode.cn → **右上角点自己头像 → 我的主页**，地址栏里 `/u/` 后面那一段就是，例如主页是：
```
https://leetcode.cn/u/HU3783TekW/
```
那 slug 就是 `HU3783TekW`。

---

## 三、「私下更改设置」常用命令速查

改完 config.json 后，在项目根目录 PowerShell 执行以下命令快速验证效果。

### 3.1 立即手动执行一次（最常用）
```powershell
python monitor.py
```
或（等价）：
```powershell
python main.py --now
```

### 3.2 启动常驻自动模式（每天定时执行）
先在 config.json 把 `mode` 设成 `"schedule"` 或 `"both"`，把 `hour/minute` 改成你要的时间，然后：
```powershell
python main.py
```
窗口别关，程序会一直挂着到点自动发。

### 3.3 测试「5 秒一次 + 连跑 5 次停」（验证自动连发有没有问题）
不用改 config.json，直接加 CLI 参数最方便：
```powershell
python main.py --interval 5 --max-runs 5
```
你会看到 25 秒内连续推送 5 条消息，第 5 条发完自动退出。

### 3.4 临时只改推送渠道 / 定时时间（不改 config.json）
```powershell
# 今天想试试钉钉
python main.py --now --channels dingding

# 今天临时改到晚上 22:30 再发
python main.py --hour 22 --minute 30
```

---

## 四、飞书机器人创建（1 分钟完成）

1. 打开飞书桌面端 → 进入要发消息的群聊 → 右上角「…」→「群机器人」。
2. 点「**添加机器人**」→ 选「**自定义机器人**」（一定选这个，别选带图标的第三方应用）。
3. 起名 `LeetCode每日提醒` → 点「添加」。
4. 复制弹出的**完整 Webhook 地址**，粘到 config.json 的 `feishu.webhook_url`。
5. **安全设置全部不要勾**（签名校验、IP 白名单、关键词都先别勾，先跑通再说，后面再加也不迟）→ 点「完成」。

然后跑一下最小化连通性测试（不依赖 LeetCode 接口）：
```powershell
python -c "import json, requests; from config import load_config; cfg=load_config()['channels']['feishu']; payload={'msg_type':'text','content':{'text':'🎉 飞书连通性测试'}}; r=requests.post(cfg['webhook_url'], headers={'Content-Type':'application/json'}, data=json.dumps(payload, ensure_ascii=False).encode('utf-8')); print('飞书返回:', r.text)"
```
看到 `code:0, msg:success` + 群里收到消息，就说明机器人完全没问题。

---

## 五、部署到 GitHub（免费 24h 自动跑，推荐）

### 5.1 为什么推荐部署到 GitHub？
- 不用你自己电脑一直开着
- 零成本（公开仓库无限分钟 / 私有仓库每月 2000 分钟，每天 1 次完全用不完）
- 支持随时手动点一下立刻补发 + 每次运行全量 Log 可回溯

### 5.2 步骤 1：创建空仓库 + 把代码推上去
1. GitHub 右上角 **+ → New repository** → Name 填 `LeecodeMonitor`（你刚才用的名字）→ 别勾任何初始化选项 → **创建仓库**。
2. 在本地 CMD / PowerShell 里：

```powershell
# 第一次 push 前先设置你是谁（只设一次，以后不用再跑）
git config --global user.name "lucy94lucy44944"
git config --global user.email "lucy94lucy44944@users.noreply.github.com"

# 绑定到你的仓库 + 推送
cd e:\gitclon\leetcode-monitor
git remote remove origin 2>$null
git remote add origin https://github.com/lucy94lucy44944/LeecodeMonitor.git
git branch -M master
git push -u origin master
```

3. 弹 GitHub 登录框时：
   - 用户名填 `lucy94lucy44944`
   - **密码用 Personal Access Token（PAT）**，不是你的 GitHub 登录密码（如果不会生成 PAT，看下面一节）。

#### 如何生成 GitHub PAT（一次性）
- GitHub 右上角头像 → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**
- Note 填 `LeetcodeMonitorPAT`，Expiration 选 `No expiration`，权限只勾 **repo**，点 Generate。
- ⚠️ `ghp_` 开头那串立刻保存好（再关掉就看不到了）。

---

### 5.3 步骤 2：在仓库里配置 3 个 Secrets（飞书 Webhook 不要直接写死到仓库里）

打开仓库 → **Settings → Secrets and variables → Actions → New repository secret**，按表格依次创建：

| Name（严格照抄，大小写不能错） | Secret（填什么） |
|---|---|
| `FEISHU_WEBHOOK_URL` | 完整的飞书 Webhook：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxx` |
| `FEISHU_SECRET` | 没开启签名校验就填 `NONE`（4 个大写字母） |
| `LEETCODE_USERS_JSON` | 一行紧凑 JSON 数组，例如：<br>`[{"slug":"HU3783TekW","real_name":"啥子"},{"slug":"user2-slug","real_name":"张三"}]` |

创建完你能在列表里看到这三个名字，Value 显示 `********`。

> 以后想加/减监控用户，**不用改代码、不用重新 push**，只要来这里更新 `LEETCODE_USERS_JSON` 的内容，下一次自动运行 / 手动 Run 就会用新用户列表。这就是用 Secrets 最大的好处 ✅

---

### 5.4 步骤 3：立即手动验证（在 GitHub 服务器上推一次消息）
1. 仓库顶栏点 **Actions → 左侧选「LeetCode Daily Monitor」→ 右上蓝色按钮 **「Run workflow」** → 选 master 分支 → 再点 Run workflow。
2. 等约 30 秒刷新页面，点进去最新的 workflow run → 展开 **run-monitor → Inject config from Secrets and run monitor** 看实时 Log。
3. 如果 Log 最后没报错，**并且飞书群里机器人发了和本地一样格式的报告** → 就说明 GitHub 端 100% 通了。🎉

---

### 5.5 步骤 4：设置每日自动执行时间

现在 workflow 默认每天晚上 **22:30 北京时间** 自动跑一次。想改时间就编辑本地 `.github/workflows/python-app.yml` 的第 9 行：
```yaml
schedule:
  - cron: '30 14 * * *'   # UTC 14:30 = 北京 22:30
```
换算规则：**北京时间 - 8 小时 = UTC 时间**。常用对照表：

| 北京每天几点发 | cron 写法 |
|---|---|
| 08:00 早提醒 | `0 0 * * *` |
| 12:00 午提醒 | `0 4 * * *` |
| 21:00 晚催 | `0 13 * * *` |
| **22:30 睡前催（推荐）** | `30 14 * * *` |
| 23:59 截止前 | `59 15 * * *` |

改完 YAML，本地提交并 push：
```powershell
git add .
git commit -m "tune: 调整每日发送时间为 22:30"
git push
```
下一个定时周期就按新时间执行。

> ⚠️ 说明：GitHub Actions 的 cron 实际触发通常会比设定时间晚 3~15 分钟（全球调度器排队），这是正常现象。

---

### 5.6 想在 GitHub 上测试「连续自动连发」
GitHub 的 cron 最小单位是 5 分钟，不能 5 秒一次。但你可以在一次 workflow run 里让 Python 程序本身连发 N 次：

把 YAML 最后一行（`python monitor.py`）临时改成：
```yaml
python main.py --interval 10 --max-runs 3
```
再 push 上去，然后 Run workflow 一次，飞书群会连续收到 3 条消息（间隔约 10 秒），验证自动推送的稳定性。验证完记得改回 `python monitor.py`，不然每次定时都会连发 3 条。

---

## 六、常见错误速查表

| 错误现象 / 返回码 | 原因 | 怎么修 |
|---|---|---|
| 飞书返回 `code:19001 access token invalid` | webhook URL 错了 / 机器人被移除了 | 重新加自定义机器人，完整复制新的 webhook |
| 飞书返回 `sign match fail` | 机器人开了签名校验，但 `secret` 没填 / 填错 | 两边一致，或者都关了 |
| 某个用户数据一直显示 0 题 | slug 写错了（大小写！）/ 今天真的没提交 | 打开 `https://leetcode.cn/u/你的slug/` 看是不是自己主页 |
| `ModuleNotFoundError: No module named 'schedule'` | 没装依赖 | `pip install -r requirements.txt` |
| Git `Author identity unknown` | 没设 git user.name / user.email | 跑一次 `git config --global user.name "你的GitHub名"` 和 `.user.email "xxx"` |
| Git push 要密码 / 报 403 | 用真密码填了密码框，应该用 PAT token | 按 5.2 生成 PAT，密码框粘贴 ghp_ 开头的 token |
| GitHub Actions 跑失败 | 点进 workflow 看 Log 最后 50 行 | 最常见是 3 个 Secrets 有 1 个没填对 |

---

## 七、项目关键代码文件索引（给你以后改着玩）

| 功能模块 | 文件位置 | 改它能实现什么 |
|---|---|---|
| 配置加载 + 用户名真名映射 | [config.py](file:///e:/gitclon/leetcode-monitor/config.py) | 新增配置项 / 向后兼容旧配置 |
| LeetCode 当日提交校验核心 | [monitor.py](file:///e:/gitclon/leetcode-monitor/monitor.py) | 改报告文案 / 改统计排序方式 / 换数据接口 |
| 调度器（定时 + 间隔 + 次数限制）| [schedule_job.py](file:///e:/gitclon/leetcode-monitor/schedule_job.py) | 改调度逻辑 / 新增命令行参数 |
| 飞书推送实现 | [channel_bot/feishu_bot.py](file:///e:/gitclon/leetcode-monitor/channel_bot/feishu_bot.py) | 改消息为富文本 / 消息卡片 / @ 群成员 |
| 可扩展推送框架注册 | [channel_bot/__init__.py](file:///e:/gitclon/leetcode-monitor/channel_bot/__init__.py) | 新增企业微信 / Slack / Discord 渠道 |
| GitHub Actions 工作流 | [.github/workflows/python-app.yml](file:///e:/gitclon/leetcode-monitor/.github/workflows/python-app.yml) | 改每日 cron 时间 / 改运行环境 |
| 项目依赖清单 | [requirements.txt](file:///e:/gitclon/leetcode-monitor/requirements.txt) | 新增第三方库版本管控 |

---

文档生成时间：2026-08-10
