# IOS-003 r2 一次交接（人工档）

- 日期（Asia/Hong_Kong）：2026-11-17
- 任务：`tasks/IOS-003-r2.md`（打开微博、首页刷新 1 次、随机滑动 3–5 下）
- r1 因滑动上限冲突未执行（见 `reviews/IOS-003-r1-7b0b9c6.md`）；
  r2 只改滑动区间为 3–5，用户已确认。其余与 r1 交接相同。
- 人工档：不进清单、等待器不领取；交给现有 DeepSeek Harness 会话
  读一次、跑一次；回执写 `results/IOS-003/r2/a1.md` 并普通 push。

## 顺序

1. 读 `tasks/IOS-003-r2.md` 全文，以其允许/禁止/停止条件为准。
2. 只读核对三个脚本 SHA256 与任务单给出的 r1 基线一致；
   不一致就停、写回执，不要跑。
3. 确认只有 DEVICE_A、无同程序实例在跑、设备已连接。
4. 执行一次：`python weibo_browse.py --open --run --confirm-home
   --refresh-min 1 --refresh-max 1 --swipe-min 3 --swipe-max 5`，
   `--device`、`--bundle` 用本机既有值（bundle 为 `com.sina.weibo`），
   其余用程序默认。
5. 只跑这一次。触发停止条件就停，不重试、不改参数、不修代码。
6. 按任务单写 `results/IOS-003/r2/a1.md` 并 push；画面与原始日志
   只留本机，回执只写相对路径和脱敏摘要。

红线与 r1 相同：不登录、不注册、不输入凭据；不点赞/关注/评论/转发/
发帖；不用程序化滚动冒充真实触摸；不上传截图、录屏、原始日志、完整 UDID。
