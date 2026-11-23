# 6.28 设置图标 + 暂停闪现 / 切换乱跳 / 右侧小岛圆角

基于 6.27。用户反馈三件事，并附 1502 行日志（6.27 版本，含 `pill host side=` 与
`ignore foreign indicator` 两条新日志，说明 6.27 的两个修复确实生效了 ——
日志里 `ignore foreign indicator frame={{415, 26.33}...}` 一直在拦地图那个红点）。

## 1. 设置里没有图标 → 新做一个

- `make_icon.py` 用程序绘制：Apple 设置风格的圆角方块（深红径向渐变 + 顶部柔光），
  中央写轮眼（黑描边环 + 红色虹膜 + 三枚逗号状勾玉 + 中心瞳孔 + 镜面高光）。
- 输出 `RecordingSharingan.png` (180)、`@2x` (180)、`@3x` (270)，放进
  `RecordingSharinganPrefs/Resources/`（该目录会被复制到 bundle 根）。
- `Info.plist` 增加 `CFBundleIconFile = RecordingSharingan`；
  PreferenceLoader 入口 plist 的 `entry` 增加 `icon = RecordingSharingan`。

## 2. 暂停 → 点空白，素材闪一下

### 原因

6.27 恢复路径是“先亮、后纠偏”：确认 capture 持续 YES 后立刻 `eye.hidden = NO`，
然后才让 geometry 把素材搬到正确位置。于是会先在**旧位置**亮一帧，再跳过去。

### 修法（显示门）

- 恢复时不再立刻显示，而是开门：`RSIslandShowGate = YES`，最晚 0.20s。
- 药丸分支每次同步都算目标圆心；**连续两次落点相差 ≤1pt** 才点亮，
  到点仍不稳定则强制点亮。日志：`eye shown after geometry gate hits=...`。
- 另加 0.26s 兜底：万一药丸分支没跑到（宿主没就绪），到点也强制显示，
  绝不会因为门关着而永久不出现。

## 3. 切换程序时素材乱跳

### 原因

6.27 的药丸选择只按“交集面积最大”，音乐展开时那个 **407x84** 的大容器会胜出
（日志 12:22:58 有 `island extend ... {407.33, 84}`），把素材圆心按 h/2 算到左边中部；
而且每帧重新评分，容器 A/B 之间会来回切。

### 修法

- 尺寸带收窄：宽 **40–260**、高 **24–50**，直接排除展开的大容器。
- **迟滞**：上一次用的药丸只要仍然可用（`RSIslandPillUsable`）就一直沿用；
  只有它离开窗口/尺寸不符时，才重新评分。
- 评分改为“先比交集比例，再比面积（小的优先）”，避免在两个候选间抖动。

## 4. 右侧独立小岛又不圆了

### 原因

6.27 把素材搬进药丸容器后，药丸分支在末尾直接 `return`，
**跳过了 `RSIslandRoundAccessoryHost()`** —— 6.24 起一直有效的圆角处理被绕开了。

### 修法

药丸分支在显示前补调 `RSIslandRoundAccessoryHost(pill)`：
仍然只用 `cornerRadius`（全文件零 `masksToBounds`），范围限制在宿主 + Accessory 外壳 + 2 层，
0.25s 限流，不会重演 6.23 的崩溃。

## 保持不变

- 加宽只作用于录屏岛自己的容器，`target = 来帧 + extra`，右边缘不动。
- 红点归属过滤（X ≤ 40pt / Y ≤ 24pt），素材不会跑到别的 Live Activity。
- 素材挂药丸容器、圆心 = 端点圆弧圆心，贴边且不缺角。

## 验证限制

本机无 Theos / iOS SDK，仅做源码级验证（Logos 零错误、括号 634/634、无未使用函数、
零 masksToBounds、三个 plist 均可解析）。`.deb` 由 GitHub Actions macOS runner 编译；
图标在设置里的实际显示效果需安装确认。