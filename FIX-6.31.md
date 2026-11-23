# 6.31 素材必须挂在药丸容器上（修“不是圆的”红月牙 / 切素材消失）

依据：用户 46 秒实机录屏（`video_C20B9D5A.mp4`）+ 1148 行日志（6.30 实机，2026-11-23 22:50–22:52）。

## 一、录屏里看到什么

| 时间/状态 | 现象 |
|---|---|
| 单独录屏 | 素材正常，贴在岛左端 |
| 2 s（刚开音乐） | 左端只剩一道**红色月牙**，其余被黑色吞掉 —— 用户说的“不是圆的” |
| 12 s | 只剩原生红点，素材不在 |
| 开地图后（30–40 s） | 有时正常在右端，有时又只剩红点 |
| 切左边素材 | 素材消失一段时间 |

## 二、日志为什么 6.30 的“照抄红点”没生效

```
$ grep -c 'eye anchored' RecordingSharingan-V7_1.log
0
$ grep -c 'native dot pending, temporary fallback'
709
```

6.30 新加的两条路径**一次都没命中**：

- `RSV630FindDotPortal()` 要求 portal 的 `sourceView` 里能找到 3–12pt 的红点 ——
  实机里 `SBSystemApertureSceneElementAccessoryPortalView` 镜像的是 accessory view，
  红点并不在它的 source 子树里 → 找不到；
- `RSV630RealIndicatorInside()` 要求红点屏幕矩形落在药丸矩形内 ——
  两个副本分别在 `{417.8, 29.2}` 和窗口本地 `{2.83, 2.83}`，
  都不在药丸的屏幕矩形里 → 找不到。

于是整场仍然走旧路径：`V7.11 accessory host bound class=SBSystemApertureSceneElementAccessoryPortalView frame={{0,0},{17,22}}`
—— 素材被 `addSubview` 到了 **17×22 的 accessory portal** 上。

## 三、根因：父视图选错了，不是位置错了

素材尺寸 37pt，却被挂进 17×22 的 portal。portal 在药丸的黑色背板**下面**，
所以：

- 只有伸出药丸圆角之外的一小条能看见 → **红色月牙**（“不是圆的”）；
- 系统一重建背板 / 切换活动，portal 子树的 z 序变化 → 素材被完全盖住 → **消失**；
- 切素材时 `RSReloadEyeImage` 重建视图，旧 portal 身份失效 → 消失。

## 四、6.31 改法

1. 新增 `RSV631EnclosingPill(view)`：从 portal / 锚点向上找最近的
   `SBSystemApertureContainerView`（≤12 层，必须在窗口内、可见）。
2. 新增 `RSV631PlaceEye(pill, anchor, allowShow)` 统一摆放：
   - **父视图永远是药丸容器**，`bringSubviewToFront`；
   - 圆心取 anchor（portal / 红点 / provided 容器）在药丸坐标系里的中心；
   - 直径 `min(设置尺寸, 药丸高度)`，再夹在药丸内；
   - 立刻 `RSApplyMaterialForSide` + 保证旋转动画。
3. 三处调用点全部改成“先找药丸再摆”：
   - accessory portal 分支（就是月牙/消失的来源）；
   - fallback provided-container 分支；
   - 6.30 的红点分支（保留，命中时更准）。
4. `layoutSubviews` 排队重贴的条件放宽：只要
   “红点在这块岛里”**或**“素材当前就挂在这块岛”**或**“这块岛是上次锁定的药丸”，
   就重贴一次 —— 系统每次重排后素材都在最上层。
5. `RSReloadEyeImage` 末尾立即重贴一次，修“切左边素材会消失”。
6. 新增诊断：找不到药丸时打印
   `[6.31] no pill for accessory-portal chain=...`，把视图层级链打出来，
   下次一眼就能看出 portal 到底挂在谁下面。

## 五、验证限制

本机无 macOS / Xcode / iPhoneOS SDK：Logos 预处理零错误、大括号 709/709、
static 符号无未使用项。`.deb` 由 GitHub Actions 生成，实机效果需安装确认。
