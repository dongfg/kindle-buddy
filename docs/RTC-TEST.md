# PW2 单次 RTC 休眠测试

日期：2026-11-18，保持现有应用代码与运行模式不变。

- 使用 rtc0 的 sysfs wakealarm 设置相对 25 秒闹钟，读取确认后进入 mem。
- 北京时间 13:01:54 进入，13:02:20 返回；总耗时 26 秒，挂起调用返回 0。
- 内核明确记录 valid RTC Alarm0 interrupt，闹钟时间与恢复 RTC 时间一致。
- 设备恢复耗时约 832ms（内核设备恢复阶段，非完整唤醒耗时）。
- SSH 可重新连接，应用继续输出 13:02 分钟刷新；powerd 恢复 active。
- 本次测试闹钟已清除，无循环闹钟、无应用省电模式变更。
- 测试时正在充电，尚未验证断电续航、重复唤醒、触摸/插拔唤醒。

注意：BusyBox rtcwake -m no 在 rtc1 与 rtc0 上均返回 Invalid argument；其中 rtc0 尽管返回错误仍实际写入了闹钟。因此不能据此判断 RTC 硬件不可用，后续改用 sysfs 写入并回读确认。初次尝试没有进入休眠，试写闹钟均已清除。

独立测试脚本与原始日志保存在 work/（不提交），设备侧为 /tmp/kindle-buddy-rtc-once.sh 与 /tmp/kindle-buddy-rtc-test.log。后续如实施分钟休眠，先验证独立连续循环与非充电状态，不直接默认启用。