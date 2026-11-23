# 6.22 两个实机问题修复

基于 6.21。用户实机录像（886x1920，25s）确认两个问题：

## 1. 开始录屏时 7pt 不是立刻生效，必须再滑一次灵动岛

### 取证

逐帧测量黑色药丸左边缘/宽度（2x 缩放，1pt=2.254px）：

| 时间 | 左 | 右 | 宽度 | 说明 |
|---|---|---|---|---|
| 0.0s | 308 | 616 | 137.1pt | 录屏已开始，morph 中 |
| 2.0s | 285 | 584 | 133.1pt | 过渡帧（画面模糊） |
| 7.0–12.0s | 314 | 610 | 131.8pt | 稳定态，未加宽 |
| 15.0–22.0s | 285 | 571 | 127.3pt | 音乐展开态，未加宽 |

0–12s 一直是原生宽度，说明开始那一刻我们的 hook 全部原样放行。

### 根因

`RSIslandExtendLeftFrame()` 的开关是 `RSRecordingActive`。它由
`UIScreenCapturedDidChangeNotification` 推动，而灵动岛开始 morph 的那次 `setFrame:`
往往比通知早几十毫秒。于是：

- morph 期间：`RSRecordingActive == NO` → 原样放行，岛保持原生宽度；
- 之后没有新的 `setFrame:`（Auto Layout 没有变化就不会再设置 frame）→ 永远停在原生宽度；
- 用户滑动/点开灵动岛时产生新布局 → 又一次 `setFrame:`，此时 `RSRecordingActive` 已 YES → 立刻加宽。

这与用户描述“要点一下软件、重新滑动他才生效”完全一致。

### 修复

1. 触发条件改为系统真实状态 `UIScreen.isCaptured`（`RSRecordingActive` 仅作兜底），
   覆盖通知到达前的那段窗口。
2. 新增 `RSIslandForceApplyNow()`：录屏开始后 0.12s / 0.45s 各主动把当前
   `SBSystemApertureContainerView` 的 frame 重新过一遍 hook（等价于用户手动滑一次），
   所以 7pt 立刻生效，不需要任何用户操作。该操作幂等：宽度已含 extra 时 hook 直接放行。
3. 存取语义从“记录加宽后的 frame”改为**记录系统原生 frame**：
   - 宽度 == 原生 + extra → 说明系统按加宽后的 bounds 重算，放行（不叠加）；
   - 宽度 == 原生 → 系统又算了一次原生宽度，继续加宽到同一目标值；
   - 其它 → 新的几何，按新值加宽。
   这样既不会每轮 +7pt 累积，也不会错过系统重新回到原生宽度的时机。

## 2. 开音乐后分离出的右侧独立岛不是圆的

### 取证

18.5s 右侧独立岛的轮廓逐行扫描（排除左侧音乐岛）：

```
y=22 w=52   y=34 w=80   y=49..70 w=93(平)   y=88 w=77   y=100 w=41
```

即一块 **93x81px（41x36pt）、圆角约 20px（9pt）的圆角矩形黑色背板**，
里面是系统 ~31pt 红点，外面是我们的 37pt 写轮眼素材。
素材 PNG 本身是正圆（256,2 处 alpha=14，四角透明），所以“不圆”来自这块背板：
它的四个角比圆形素材更外，露出黑色/淡红边角。

### 修复

`RSIslandRoundAccessoryHost()`：在每次几何同步时，把写轮眼宿主及其 Accessory 祖先
（最多 3 层）里尺寸落在 28–70pt 的背板 `cornerRadius = MIN(w,h)/2`、`masksToBounds = YES`，
圆角矩形变成正圆/胶囊。只在独立小岛尺寸带内动手，展开的大容器（>70pt）绝不修改。
日志：`accessory chip rounded class=... bounds=... radius=...`。

若实机看仍是“胶囊”（41x36 圆角 18 会留下约 2pt 的左右小耳朵），
下一版可以把背板 bounds 收成正方形（w=h）彻底变圆。

## 验证限制

本机无 Theos / iOS SDK，只能做源码级验证（Logos 预处理零错误、括号 571/571、
版本五处一致）与录像取证；`.deb` 由 GitHub Actions 的 macOS runner 编译。
实机效果（尤其圆角是否够圆）仍需装上看。