# 开发说明

## 已验证设备

- Kindle Paperwhite 2，固件 5.12.2.2，ARMv7，Linux 3.0.35。
- 原生 framebuffer 758×1024、8bpp；界面逻辑画布 1024×758。
- Python 3.9 + Pillow 9.0.0.dev0，FBInk v1.25.0，USBNetwork 0.22.N。
- 原生底边充电口对应横屏右边。界面顺时针旋转写入 framebuffer，不修改系统旋转。
- 触摸 `/dev/input/event1`，映射 `(raw_x,raw_y)` → `(raw_y,757-raw_x)`。
- 电源键 `/dev/input/event0`，KEY_POWER=116；长按保留给系统。
- 已验证通过 `/sys/class/rtc/rtc0/wakealarm` 设置闹钟并进入 `mem`。

## 电脑连接

Windows 需要 PowerShell 和 OpenSSH 的 ssh/scp。开发密钥放在 `.local/kindle_ed25519`，主机记录放在 `.local/known_hosts`，两者都不提交。把公钥加入设备 `/mnt/us/usbnet/etc/authorized_keys`，启用 Wi-Fi SSH。

当前脚本默认地址为开发设备 `10.3.81.186`，可用 `-Address` 覆盖。首次连接需核对设备主机密钥并准备 known_hosts；脚本启用严格主机验证。

```powershell
./scripts/kindle.ps1 -Address '10.3.81.186' -Command 'id'
./scripts/kindle.ps1 -Command 'sh /mnt/us/kindle-buddy/stop.sh'
./scripts/deploy.ps1
./scripts/kindle.ps1 -Command 'sh /mnt/us/kindle-buddy/launch.sh'
./scripts/kindle.ps1 -Command 'tail -30 /mnt/us/kindle-buddy/buddy.log'
```

更新前先停止应用。部署脚本上传运行文件、农历库与插画，生成封面、安装 documents 入口，并执行设备端检查；不会自动启动应用。经典 SCP 的 `-O` 用于兼容 Kindle 的服务。

`-Command` 为设备 shell 命令。包含 `$` 时使用 PowerShell 单引号，避免本机展开。设备休眠期间 SSH 不保证可达；先按电源键唤醒。普通 USB 存储模式只能复制文件。

## 代码结构

| 文件 | 职责 |
| --- | --- |
| device/buddy.py | 本机渲染、触摸、电源键、事件循环和应用生命周期 |
| device/power_schedule.py | 作息计算、RTC 闹钟、休眠及前光恢复 |
| device/sync_time.py | 限时的启动 NTP 校时，失败不阻止启动 |
| device/start.sh | 校时后运行应用 |
| device/launch.sh | 提权、检查已运行实例、延迟后台启动 |
| device/KindleBuddy.sh | 图书馆元数据与入口 |
| device/make_cover.py | 生成图书馆黑白封面 |
| device/vendor/ | 固定版本农历库及许可证 |
| scripts/ | Windows SSH 与部署工具 |

运行期间暂停原生 UI 进程并独占触摸输入；退出释放输入、恢复本次暂停的进程与屏保控制，触发原生界面重绘。工作时段每 30 秒设置 preventScreenSaver 并重置空闲计时，保持分钟刷新。

充电监听使用 powerd 的 charging/notCharging 事件，另每 2 秒检查充电状态兜底。百分比每分钟读取；事件只更新角落，不读取新百分比。时钟区域每分钟局部刷新，跨日与每 30 次刷新全屏清残影。

非工作时段与手动休眠使用 rtc0，先写闹钟并回读确认，再进入 mem；失败恢复显示并稍后重试。保留其他任务更早的闹钟。前光睡前保存、休眠关闭、唤醒恢复。夜间手动唤醒临时运行 10 分钟。没有分钟级深度休眠或开机自启动。

## 检查与截图

```powershell
./scripts/kindle.ps1 -Command '/mnt/us/python3/bin/python3.9 /mnt/us/kindle-buddy/buddy.py --self-test'
./scripts/kindle.ps1 -Command 'fbgrab /tmp/kindle-buddy-screen.png'
```

检查覆盖 36 个月份网格、闰年/跨年、农历春节与闰月、作息周末边界、基础渲染和触摸映射。真实触摸、插拔、休眠和长期耗电仍需实机验证。显存截图旋转 90° 逆时针后即为阅读方向，不代表真实墨水屏的残影与闪烁。

`buddy.py --preview` 可生成主界面渲染预览，不驱动屏幕。测试标记 `/tmp/kindle-buddy-sleep-test` 写入 10–60 秒，触发一次短休眠；`/tmp/kindle-buddy-sleep-now` 触发正常手动休眠。两者均一次性消费，请勿在无法手动唤醒设备时随意测试。

不要将 `powerd_test -h` 当作帮助参数：此设备会将其解释为长按电源键，弹出电源选项。

## 素材与配置

配置说明见 README。系统字体不分发；应用按固定 UTC 偏移显示，启动 NTP 会校正系统 UTC 时间。校时每服务器最多 4 秒，总预算 8 秒；缺失工具或网络故障均回退系统时间。

插画源文件在 device/，由内置图像工具生成或编辑。部署会同步插画；休眠图按横屏等比适配，主界面小猫带透明背景。不要提交设备日志、SSH 密钥、个人配置缓存或 vendor 的 Python 编译缓存。
