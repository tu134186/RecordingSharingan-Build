# 6.29 参照「灵动岛跳舞」的做法重写定位逻辑

同时参考了用户提供的第三方插件 `灵动岛跳舞_2.4_无根.deb`（已完整解包分析）。

## 一、苹果红点的真实工作原理（从日志推断）

1. 红点本体 `SBRecordingIndicatorView` 只有 **5.67×5.67pt**，住在**独立窗口**
   `SBRecordingIndicatorWindow` 里，根本不在灵动岛视图树中。
   （6.25 日志：`V7.8 indicator layout frame={{417.83,29.17},{5.67,5.67}} window=SBRecordingIndicatorWindow`）
2. 灵动岛里显示出来的那个红点，是 `_UIPortalView` 把上面那个红点**镜像**过来的
   —— 即 `portal.sourceView = SBRecordingIndicatorView`。
3. 所以岛在左边开一个 portal、在右边开另一个 portal、展开时再开第三个，
   **指向的都是同一个红点**。红点自己从不移动，是 portal 跟着岛走。

结论：想让素材“像苹果自带的一样”，就必须跟着**系统自己的容器几何**走，
而不是每帧自己算坐标。

## 二、拆解「灵动岛跳舞 2.4」得到的实现

Mach-O 解析结果（arm64 slice，__objc_methname 238 条）：

- Hook 目标：`SBSystemApertureContainerView`、`_SAUIProvidedViewContainerView`
- Hook 方法：`layoutSubviews`、`setFrame:`、`didMoveToWindow`、`addSubview:`、`setHidden:`
- 自建视图：`UIImageView`（`initWithFrame:` / `initWithImage:` / `addSubview:`），
  另有 `setupMaskLayer` / `setMask:` / `setMaskImageView:`、`setCornerRadius:`、`setMasksToBounds:`
- 动画：`CABasicAnimation` / `CAKeyframeAnimation` + `startRotation` / `stopRotation`
  + `layer.speed` / `timeOffset`（暂停用）
- 素材路径：`/var/mobile/DynamicIsland/eye/%`、`/dance/%`、`/mask/%@/Mask.png`
- 隐藏红点：直接 `setHidden:`（在 `_SAUIProvidedViewContainerView` 一侧）

也就是说，它的做法是：**在容器 layout 时把自建 UIImageView 塞进容器、设 frame、设圆角、隐藏原生红点**，
素材位置完全由容器 bounds 决定 —— 与 6.27 起我们采用的「挂药丸容器」是同一思路。

## 三、6.29 的改动（依据 6.28 实机日志）

### 1. 素材挂不上 / 切 App 掉回 fallback（主 bug）

6.28 日志里 `native dot pending, temporary fallback` 刷了上千次，`native indicator locked` **一次都没有**：

```
13:00:10 V7.8 ScreenRecording ready; native dot pending, temporary fallback   (×N)
```

原因有两个，都出在我 6.27 加的“归属过滤”：

- 它用**录屏元素矩形**去算间隙，但录屏元素实测是**整宽视图**（中心≈215，宽度覆盖整屏），
  这个判据天然不成立 → 正确红点也被拒；
- 药丸搜索也依赖同样不可靠的 `er`，元素短暂离窗时 `pad` 变空 → 找不到药丸。

修法：

- 红点归属改为**按药丸中心距**判定（≤60pt 同一块岛），并且药丸找不到时**不做否定**（放行）。
- 药丸搜索的**主判据改成“这块容器里有没有录屏 portal”**
  （`_UIPortalView.sourceView → SBRecordingIndicatorView`，尺寸 3–12pt），
  与元素矩形无关。这样切 App、元素离窗、红点窗口抖动都不影响。
- `RSV6SyncEyeToElement` 不再要求 `element.window`。

### 2. 点暂停 / 点空白，素材闪一下，长时间只剩红点

6.28 日志证据 —— `capture-off grace` **每秒重复一次**：

```
12:59:39 capture-off grace started 1.35s
12:59:40 capture-off grace started 1.35s
12:59:41 capture-off grace started 1.35s
...
```

说明 `UIScreen.isCaptured` 在录屏过程中会持续抖动。而我每次抖动都隐藏素材 0.18s，
于是反复闪烁、甚至长时间只剩原生红点。

修法：**capture-off 完全不隐藏素材**。素材现在是药丸容器的子视图，
录屏真停时药丸消失、素材自然一起消失，不需要手动隐藏。
宽限期只保留“会话保持 + 每 0.1s 复核状态 + 1.35s 后确认真正停止”。

显示门（6.28 引入）一并删除 —— 它在这种抖动下反而制造闪烁。

### 3. 设置图标太大

第三方插件用 `icon@2x.png` 90×90 也能显示，但标准 PreferenceLoader 尺寸是
**29 / 58 / 87 pt**。6.28 输出的是 180/180/270，导致图标顶到行高。
6.29 改为 29 / 58 / 87，视觉上与其它插件一致。

## 四、保持不变

- 加宽只作用于录屏岛自己的容器，`target = 来帧 + extra`，右边缘不动。
- 素材圆心 = 药丸端点圆弧圆心（左 `(h/2,h/2)`、右 `(W-h/2,h/2)`），贴边且不缺角。
- 迟滞：上次的药丸仍可用就沿用，避免切换时抖动。
- 全文件零 `masksToBounds = YES`（6.23 崩溃根因）。

## 五、验证限制

本机无 macOS / Xcode / iPhoneOS SDK，无法编译或实机验证：
Logos 预处理零错误、括号 642/642、无未使用函数、零 `masksToBounds`。
`.deb` 由 GitHub Actions 的 macOS runner 生成。实机效果需安装确认。
## 六、构建修复（6.29 首次真正出货）

前一阶段 6.29 连续 5 次构建失败，日志是：

```
Tweak.xm:103:23: error: unused variable 'RSIslandShowDeadline' [-Werror,-Wunused-variable]
Tweak.xm:104:19: error: unused variable 'RSIslandGateHits'
Tweak.xm:105:16: error: unused variable 'RSIslandGateCenter'
```

删掉显示门时只删了逻辑、忘了删这三个静态变量（Theos 编译带 `-Werror`）。
删除后本地扫描确认 282 个 static 符号无未使用项，重新构建成功：

- run 45209952482，deb 253006 字节，sha256 80d0dbcdc41768d1…
