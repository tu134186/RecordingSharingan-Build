# 6.24 修安全模式崩溃（6.23 加宽即崩）

## 现象

装 6.23 后：开始录屏 → 素材加载出来 → 灵动岛刚加宽 → **SpringBoard 崩溃进安全模式**。

日志证据（用户上传 `/var/mobile/RecordingSharingan-V7.log`，只有 1310 字节）：

```
[2026-11-23 10:06:57] ===== RecordingSharingan v7.11.9.4.3.2.6.23 loaded =====
[2026-11-23 10:06:58] V7.9.1 runtime probe hooks installed: ...PortalView
[2026-11-23 10:06:58] V7.9.1 runtime probe hooks installed: ...AccessoryView
[2026-11-23 10:06:59] SpringBoard launch completed, initializing
[2026-11-23 10:06:59] ===== RecordingSharingan v7.11.9.4.3.2.6.23 initialized =====
SpringBoard alive +5s (pid=36507)
<日志到此为止>
```

关键：**没有** `recording state 0 -> 1`、**没有** `island width extend`。
说明崩溃发生在“录屏刚被检测到 → 第一次 geometry 同步/加宽”这一瞬间，
且崩溃时连一行日志都来不及落盘（进程被 UIKit 直接掀掉）。

## 根因（两处，都在 6.23 新加的代码里）

### A. `masksToBounds = YES` 打到了 `_UIPortalView`（主因）

6.23 的 `RSIslandRoundSubtree` 会把 28–70pt 的背板视图设成
`cornerRadius = min/2` **并且 `masksToBounds = YES`**，而且是向下扫整棵子树（≤7 层）。

这棵子树里包含 `_UIPortalView` —— 系统录屏红点是通过 portal 从
`SBRecordingIndicatorWindow` 的 `sourceView` 渲染过来的。
**给 portal 视图开启裁切会强制离屏合成**，sourceView 位于另一个 window 时 UIKit 会直接崩。
而且这个赋值发生在 `setFrame:` / `layoutSubviews` 的调用链内部，
等于在布局事务中间改渲染树，属于最容易崩的时机。

### B. 在 `setFrame:` 里同步写日志文件

6.23 的 `RSIslandExtendLeftFrame` 在命中时直接调用 `RSLog()`，
而 `RSLog` 会 `NSFileHandle` 打开/seek/write 磁盘 —— 叠加在布局锁上。

### C. `RSIslandForceApplyNow` 直接 `[v setFrame:current]`

主动“替你滑一下”的实现是直接对 `SBSystemApertureContainerView` 调 `setFrame:`。
这个视图由 Auto Layout 管理，在布局事务之外强行 setFrame 会与布局引擎打架。

## 6.24 的修复

1. **永不设置 `masksToBounds`**（全文件 0 处）。只用 `cornerRadius`
   —— 它本身就会裁 `backgroundColor`，足以让黑背板变圆，但**不会**强制 portal 离屏渲染。
2. 圆角范围从“整棵子树 ≤7 层”收缩为 **宿主 + 最近的 Accessory 外壳 + 外壳下 2 层**，
   且 **0.25 秒最多处理一次**（原来 60fps 每帧都扫）。
3. 跳过 `Replicator / Snapshot / Hosting / _UIVisualEffect` 类。
4. 所有 island 相关代码全部包 `@try/@catch`，异常一律“放行原 frame”，绝不抛回布局事务。
5. `RSIslandExtendLeftFrame` 加**重入保护**（`setFrame` → hook → `%orig` → 系统再次 `setFrame`）。
6. 日志全部改为 `dispatch_async` 延后写，热路径里不做文件 IO。
7. `RSIslandForceApplyNow` 改为 `setNeedsLayout`（含父视图），
   让系统自己走布局 → 我们的 `setFrame` hook 自然接上，不再强行 setFrame。
8. 保留 6.23 的“基线 + 绝对目标宽度”（`target = baseline + extra`），
   所以宽度依然不会阶梯式累积；保留一次性结构探针
   `===== accessory tree probe =====`（延后写日志）。

## 若仍然不圆

装上后开录屏 + 播音乐，把 `/var/mobile/RecordingSharingan-V7.log` 里
`accessory tree probe` 那一段发我。那段会列出配件子树每一层的
类名 / frame / cornerRadius / masksToBounds / 底色，
能直接定位真正绘制黑色背板的是哪个类，再精准改（不会再靠猜）。

## 验证限制

本机无 Theos / iOS SDK，只做源码级验证：Logos 预处理零错误零警告、
括号 599/599、全文件无 `masksToBounds = YES`、无强制 `setFrame`。
`.deb` 由 GitHub Actions 的 macOS runner 编译；实机稳定性需安装后确认。