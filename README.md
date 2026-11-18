# Kindle Buddy

把闲置的 Kindle 变成办公桌上的离线时钟与农历月历。

针对 **Kindle Paperwhite 2（第六代），固件 5.12.2.2** 开发和实测。横屏使用，充电接口在右侧。其他机型的分辨率、触摸与 RTC 接口尚未适配。

## 界面

### 日历与时钟

![Kindle Buddy 主界面](docs/images/main.png)

- 24 小时制时钟，每分钟更新。
- 公历日期、星期、农历年月与生肖。
- 周一起始的六周月历，补齐相邻月份日期，今天高亮。
- 电量百分比每分钟更新；插拔充电器时单独更新闪电图标。
- 右上角 X 退出，睡在书上的小猫作点缀。

### 休眠

![Kindle Buddy 休眠界面](docs/images/sleep.png)

静态黑白插画，无文字。休眠时墨水屏保留画面，不需要持续刷新。

以上为 PW2 实际显存截图，已旋转为观看方向；真实屏幕的残影、光照效果可能不同。

## 安装条件

设备需要已越狱，并具备：

- 支持 Scriptlets 的 Hotfix，能从图书馆运行 documents 里的 `.sh` 文件。
- root helper：`/var/local/mkk/su`。
- Python 3.9 与 Pillow：`/mnt/us/python3/bin/python3.9`。
- PW2 版 FBInk：`/mnt/us/fbink/fbink`。
- 原机字体、LIPC 电源服务、触摸设备与 rtc0。启动校时使用系统 `ntpdate`；缺失或失败会跳过校时。

这不是越狱安装包，也不包含 Python、FBInk 或系统字体。运行不需要服务器，不要求安装 KUAL 菜单。

## 通过 USB 安装

1. 下载或克隆本项目。
2. 将 `device/` 中的文件和 `vendor/` 目录复制到 Kindle 根目录的 `kindle-buddy/` 文件夹。
3. 再将 `device/KindleBuddy.sh` 复制到 Kindle 的 `documents/` 文件夹。
4. 安全弹出并拔掉 USB，在原生图书馆中打开 **Kindle Buddy**。

安装后的主要路径：

```text
Kindle 根目录/
├── documents/
│   └── KindleBuddy.sh
└── kindle-buddy/
    ├── buddy.py
    ├── start.sh
    ├── launch.sh
    ├── stop.sh
    ├── power_schedule.py
    ├── sync_time.py
    ├── config.json
    ├── cover.png
    ├── cat-icon.png
    ├── sleep-cat.png
    └── vendor/
```

图书馆网格视图会显示黑白时钟与日历封面；新入口可能需要等待索引。文件需保留 UTF-8、LF 换行。已有 SSH 开发环境也可使用 [开发说明](DEVELOP.md) 中的部署脚本。

## 如何使用

| 操作 | 行为 |
| --- | --- |
| 图书馆点击 Kindle Buddy | 启动应用；有网络时先尝试校时，失败继续离线运行 |
| 点击右上角 X | 退出应用，恢复 Kindle 原生界面 |
| 短按电源键 | 手动休眠，显示小猫插画 |
| 休眠时再按电源键 | 提前唤醒；工作时段外临时运行 10 分钟后再休眠 |
| 插拔充电器 | 更新充电图标，不额外刷新整张日历 |

默认作息按 **UTC+8**：

- 周一至周六 **08:00–18:00** 正常显示。
- 18:00 自动休眠，下一工作日 08:00 自动唤醒。
- 周日保持休眠；周六晚直接安排周一早上唤醒。
- 白天手动休眠后，可按电源键提前唤醒，也会在下一工作日上午自动唤醒。

前光保持你手动设置的档位，休眠时关闭，唤醒后恢复。应用不主动关闭 Wi-Fi，但深度休眠期间 SSH 可能不可达。设备重启后需从图书馆重新启动，没有开机自启动。

## 配置

修改 Kindle 上的 `kindle-buddy/config.json`，退出应用后重新打开生效：

```json
{
  "utc_offset_hours": 8,
  "sync_time_on_start": true,
  "ntp_servers": ["ntp.aliyun.com", "time.cloudflare.com"],
  "schedule": {
    "enabled": true,
    "workdays": [0, 1, 2, 3, 4, 5],
    "wake_hour": 8,
    "sleep_hour": 18,
    "manual_wake_minutes": 10
  }
}
```

`workdays` 中 0 为周一、6 为周日。设置 `schedule.enabled` 为 `false` 可关闭自动作息；设置 `sync_time_on_start` 为 `false` 可完全禁止应用联网校时。时区为固定 UTC 偏移，不自动处理夏令时。

时间、月历、农历与界面渲染都在 Kindle 本机完成。校时仅在启动时尝试，总等待不超过 8 秒，不依赖联网启动。

## 排查问题

- **找不到图书馆入口**：检查 Scriptlets 支持，确认文件在 documents，等待索引后搜索 Kindle Buddy。
- **启动后没有界面**：查看 `kindle-buddy/buddy.log`，确认 Python/Pillow、FBInk 与字体路径。
- **休眠后 SSH 连不上**：先按电源键唤醒，再连接；必要时重新启用 SSH 服务。
- **需要更新文件**：先点 X 退出，再复制文件，完成后重新打开。

已验证分钟刷新、充电事件、退出、短睡眠 RTC 唤醒，以及周末和跨年日期计算。完整跨夜与长期续航仍需持续实测；目前不支持月份切换。

## 项目资料

- [开发、部署与日志](DEVELOP.md)
- [界面设计](UI-DESIGN.md)
- [RTC 单次测试记录](docs/RTC-TEST.md)
- [第三方组件与素材说明](THIRD-PARTY.md)
