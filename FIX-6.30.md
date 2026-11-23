# 6.30 照抄红点：素材位置/可见性彻底改为“红点在哪就在哪”

依据：用户提供的 55 秒实机录屏 + 979 行 `RecordingSharingan-V7.log`（6.29，2026-11-23 16:04:04–16:05:40）。

## 一、录屏里到底出了什么问题（逐帧测出来的）

对 110 张裁切帧做红色像素聚类，按秒统计“大圆（写轮眼）”与“小圆（原生红点）”：

| 时间 | 现象 |
|---|---|
| 0–17 s | 写轮眼在岛左端，尺寸/位置都对（红色直径 ≈68px ≈ 药丸高度） |
| 17.5–19.5 s | 岛整体换到右侧独立小岛，写轮眼跟着到右端，正确 |
| **20–33 s** | **只剩原生小红点，写轮眼整个消失** |
| 34–43.5 s | 写轮眼回到右端（左侧是绿色摄像头指示点），正确 |
| **44.5–49 s** | **又只剩红点** |
| 50–52 s | 写轮眼在右端 |
| **53–55 s** | **又只剩红点** |

也就是说：**位置基本是对的，但素材会成段消失，而且消失时原生红点还亮着。**

## 二、日志给出的两个根因

### 1) 我们一直在压“另一个红点”，真正的红点从没被压住

```
16:04:55 V7.8 indicator alpha 0.00 -> 1.00 frame={{417.83, 29.17}, {5.67,5.67}}
16:04:56 V7.8 indicator alpha 1.00 -> 0.00 frame={{415, 26.33}, {5.67,5.67}}
16:04:57 V7.8 indicator layout frame={{2.83, 2.83}, {5.67,5.67}} ... window=SBRecordingIndicatorWindow
```

`SBRecordingIndicatorWindow` 里同时存在**两个** `SBRecordingIndicatorView` 副本：
一个在屏幕右侧 x≈415（离屏/辅助副本），一个在窗口本地 {2.83,2.83}（岛左端真正显示的那个）。
6.29 的“红点归属判定”用**药丸中心距**过滤，把 x≈415 判成 foreign，于是**只压住了离屏副本**，
真正的红点 alpha 一直是 1 —— 视频里“写轮眼没了、红点还在”就是这个。

### 2) 药丸反查从 6.29 上线起一次都没命中

6.29 的核心修复是“从 portal 反查药丸”，判据写的是类名里含 `_UIPortalView`。
但系统实际用的是 `SBSystemApertureSceneElementAccessoryPortalView`
（日志第一行就有：`V7.9.1 runtime probe hooks installed: SBSystemApertureSceneElementAccessoryPortalView`），
名字里**没有** `_UIPortalView` → 反查永远为假。

于是整场 96 秒里：

- `native dot pending, temporary fallback` 出现 **633 次**（每次发现流程都掉进 fallback）；
- `V7.11 accessory host bound ... frame={{0,0},{17,22}}` —— 素材被挂进 **17×22 的 accessory portal**；
- 一旦岛重建黑背板，素材就在背板下面，看起来就是“消失”；
- 期间系统在 128 / 172 / 179 / 215 / 222 宽度之间反复 morph，
  右侧 morph 抑制链又会主动 `eye.hidden = YES`，进一步加重“消失”。

## 三、6.30 的做法：只认红点自己的位置

新增 `RSV630*` 一组函数（约 200 行），原则只有一条 —— **红点画在哪，素材就摆在哪**：

1. `RSV630FindDotPortal()`：在药丸子树里找镜像红点的 portal，
   **任何**类名含 `Portal` 的都算（含 `SBSystemApertureSceneElementAccessoryPortalView`），
   再用 KVC / ivar 读 `sourceView`，往下找 `SBRecordingIndicatorView`（3–12pt）。
2. `RSV630RealIndicatorInside()`：没有 portal 时，退一步用“红点的屏幕矩形是否落在药丸屏幕矩形内”判断（±4pt）。
3. `RSV630PlaceEyeOnPill()`：
   - 圆心 = 红点（或镜像它的 portal）在该药丸里的中心，**不再做左右猜测**；
   - 直径 = `min(设置尺寸, 药丸高度)`，并夹在药丸内，保证不会被圆角切掉；
   - `bringSubviewToFront` + 尺寸/中心用 `performWithoutAnimation`；
   - **只压住这块药丸里的红点**；其它副本（x≈415 那个）主动 `RSV73RestoreNativeIndicator()` 还原 alpha。
4. `layoutSubviews` 钩子里排队执行一次（`dispatch_async` 出布局事务），
   这就是“灵动岛跳舞”的做法：系统每次重排都在，素材永远在背板之上。
5. `RSUpdateEyeGeometry()` 最前面先走 `RSV630TryDotPlacement()`，
   命中就直接 return —— 不再进右侧 morph 抑制 / 显示门 / fallback 那一整条链，
   从根上消除“成段消失”。

带缓存：红点列表 0.10s、药丸查找 0.10s，`layoutSubviews` 只做命中判定后排队，
不会像 6.25 那样每帧全屏扫描（那次导致发热）。

## 四、预期

- 素材**始终**贴在系统红点的位置上，左右两端自动跟随（不再有“右端凸出/左端偏移”）；
- 红点被正确压住，不会出现“红点 + 素材”同时可见；
- 切换 App、岛 morph、暂停/继续 都不会再让素材成段消失；
- 设置里的左右尺寸/偏移仍然生效（作为微调），但不会再影响“是否可见”。

## 五、验证限制

本机无 macOS / Xcode / iPhoneOS SDK，无法编译或实机验证：
Logos 预处理零错误、大括号 689/689、282+ 个 static 符号无未使用项。
`.deb` 由 GitHub Actions 的 macOS runner 生成，实机效果需安装确认。
