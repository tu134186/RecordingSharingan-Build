# 6.25 三个实机问题

基于 6.24（6.24 已修掉安全模式崩溃）。用户反馈三件事，逐一取证与修复。

## 1. 素材跑到屏幕最右边（打开地图后开始录屏）

截图证据：左上是被加宽过的黑色药丸（内含系统小红点），**右上角单独一块红底写轮眼**，
位置正好压在地图 App 的 Live Activity 区域上。

### 根因

`RSV711BestAccessoryHostForElement()` 只按“离录屏元素最近的 Accessory 视图”打分，
再加上 `RSV711AccessoryPortal` 缓存会被直接复用，**从未校验这块宿主是不是真属于录屏元素**。
屏幕上一旦出现别的 Live Activity（地图/音乐），它那块独立岛就可能：
- 距离比录屏元素更近 → 被选成宿主；
- 或者上一轮会话把它记进 `RSV711AccessoryPortal`，下一轮直接被复用。

于是素材挂到了别的活动的岛上，看起来就是“跑到最右边”。

### 修复（三重过滤）

1. **归属过滤**：候选视图用 `RSV71191ExplicitlyWrongOwner()` 校验，
   归属的 `SAUIElementView` 明确不是录屏元素的，直接排除（不再参与打分）。
2. **左右惩罚**：录屏元素在屏幕左半边时，右半边的候选加 2500 惩罚分，
   只有在没有任何同归属候选时才可能被选到。
3. **距离上限**：最终选出的宿主与录屏元素中心距离 > 150pt 就判为“别的活动”，
   当作没有可用宿主（宁可先不显示，也不贴到别人岛上）。
   日志：`reject far host class=... d={x,y} (likely another Live Activity)`。
4. 缓存复用同样加了归属校验（`RSV71190MigrationTarget` / 当前 superview / 缓存 portal 三处）。

## 2. 暂停后“点空白继续录屏”，素材延迟约 1~2 秒

### 根因

快恢复路径 `RSV7117ArmPresentationRemount()` 在等 SystemAperture 的 presentation 生命周期事件，
**兜底超时是 1.60 秒**。而快恢复时系统常常复用同一个 Portal 对象、不产生新事件，
于是每次都吃满 1.60s。另外 `RSConfirmCaptureResume()` 在旧容器失效时直接 `return`，
等于什么都不做，只能等下一轮 0→1。

### 修复

1. 兜底超时 1.60s → **0.35s**；并在 **0.06s** 先尝试一次立即重挂载（多数情况这一次就够）。
2. `RSConfirmCaptureResume()` 立即执行一次 `RSDiscoverAll(YES)` 并请求加宽，
   不再等事件链；旧容器失效也继续恢复而不是 return。
3. 重挂载仍保持 3 次有界尝试（0 / 0.10 / 0.30s），不会无限循环。

## 3. 左边灵动岛“没有加宽”

### 根因

6.24 为了避开崩溃，把 `RSIslandForceApplyNow()` 里所有 `setFrame:` 都换成了
`setNeedsLayout`。但 `SBSystemApertureContainerView` 的 frame 由外部布局驱动，
单纯 `setNeedsLayout` 有时不会产生新的 `setFrame:` 调用 → 我们的加宽 hook 没被触发，
岛就保持原生宽度（要用户手动滑一下才加宽）。

### 修复

在**下一个主队列周期**（已脱离系统布局事务）补一次
`setNeedsLayout` + `layoutIfNeeded`（父视图优先），让它真正产生一次 `setFrame:`。
因为不在布局事务内部，不会像 6.23 那样和布局引擎打架。
另外恢复路径在 0s / 0.10s 各请求一次，录屏开始时 0.12s / 0.45s 各一次。

## 保持不变的

- 宽度算法仍是“原生基线 + 绝对目标宽度”（`target = baseline + extra`），
  数学上不可能阶梯累积；右边缘 `newX = MaxX - target` 固定不动。
- 全文件 **零** `masksToBounds = YES`（6.23 崩溃根因）。
- 圆角只用 `cornerRadius`，范围限制在宿主 + Accessory 外壳 + 2 层，0.25s 限流。
  用户已确认：右侧独立岛现在是**圆形**了。
- 所有 island 代码 `@try/@catch` 包裹，异常一律放行原 frame。

## 关于“找到灵动岛控制器”

当前使用的链路（都已在代码里）：
`UIApplication.systemApertureControllerForMainDisplay`
→ `_systemApertureViewController`
→ `_systemApertureManager`
→ `registeredElements`（按 `elementIdentifier == systemApertureElementIdentifierScreenRecording` 过滤）
→ `elementViewControllerForElement:` → `SAUIElementView`
→ 配件叶子 `SBSystemApertureSceneElementAccessoryPortalView / AccessoryView`
→ `_UIPortalView.sourceView → SBRecordingIndicatorView`（真正的红点）

素材位置一律照抄红点中心（逐帧同步），左右由系统几何决定，不加固定偏移。
这正是“川剧变脸”思路：脸是系统的，脸谱才是我们的。

## 验证限制

本机无 Theos / iOS SDK，仅做源码级验证（Logos 零错误、括号 610/610、
零 `masksToBounds`）。`.deb` 由 GitHub Actions macOS runner 编译，实机需安装确认。