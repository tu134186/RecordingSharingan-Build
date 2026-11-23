# 6.27 素材挂进药丸容器（贴边、不缺角）+ 红点归属校验

基于 6.26。用户提供 46 秒录像（886x1920）与 1548 行日志（6.26）。

## 1. 素材缺角 —— 被 22x22 的 accessory portal 裁掉了

### 取证

从录像 0.5s 帧按像素量素材红色区域：

```
red bbox  x 260..319   y 27..94   →  w=60px(26.6pt)  h=68px(30.2pt)
```

而设置里的素材尺寸是 **36.99pt**。高度只有 30.2pt，说明素材**上下各被切掉约 3.4pt**。

原因：素材一直挂在 `SBSystemApertureSceneElementAccessoryPortalView`（日志实测 `frame={{0,0},{17,22}}`
或 `{22,22}`）里。portal 只有 22pt 高，37pt 的圆形素材超出部分被 portal 裁成平边 ——
这就是“被挖掉一块/缺一个角”。胶囊本身是 36.67pt 高，完全装得下素材。

### 修复

改成把素材挂进**药丸容器** `SBSystemApertureContainerView`：

- 新增 `RSIslandRecordingContainerForElement()`：在全部窗口里找与录屏元素矩形基本重合
  （交集 ≥ 容器面积一半、宽 40–420pt、高 18–160pt）的容器；同样是三重归属过滤，
  不会选到音乐/地图那块。
- 素材尺寸 = `min(用户设置, 药丸高度)`，保证不被上下圆角切。
- 素材圆心 = **药丸端点圆弧圆心**：左侧 `(h/2, h/2)`、右侧 `(W - h/2, h/2)`。
  即素材与药丸圆弧同心同半径 → 既完整显示、又严格“贴边”，永不缺角。
- 位置仍然完全由系统决定（药丸在哪边素材就在哪边），用户 X/Y 微调照旧叠加。

## 2. 打开地图，素材飞到屏幕最右边

### 取证（日志 11:51:19）

```
V7.8 indicator layout frame={{417.83, 29.17}, {5.67, 5.67}} alpha=0.00 hidden=0
                           host=UIView window=SBRecordingIndicatorWindow score=80.1
V7.8 indicator alpha 0.00 -> 1.00 frame={{415, 26.33}, ...}
V7.3 native indicator locked class=SBRecordingIndicatorView frame={{415, 26.33}, ...}
SIDEFIX visual side changed=right host=SBRecordingIndicatorView screenX=417.83
SIDEFIX side=right host=0xbd6cfcac0 screenCenter={417.83,29.17} size=37.00
```

`RSV73NativeRecordingIndicatorInElement()` 原先**第一优先**调用 `RSV74GlobalNativeIndicator()`，
它会扫遍所有 `SBRecordingIndicatorWindow`，按“alpha 高、更靠左”打分。
地图活动那个红点在 x=415 且 alpha 刚刚变 1.0，于是压过真正在 x≈143 的录屏红点被选中，
素材就贴到屏幕最右边缘 —— 用户看到的“飞出去”。

### 修复

1. 顺序调换：**先在本元素子树里找**（`RSV73FindViewByClassName` + portal sourceView），
   子树里找不到才退到全局扫描。
2. 新增 `RSV73IndicatorBelongsToElement()`：全局结果必须与录屏元素矩形
   X 间隙 ≤ 40pt、Y 间隙 ≤ 24pt，否则丢弃并记日志
   `ignore foreign indicator frame=... (not near recording element)`。

## 3. 关于“找到灵动岛控制器”

日志已经证明链路是通的、而且拿到了正确对象：

```
V6 element via SystemApertureController ident=systemApertureElementIdentifierScreenRecording class=UIView
V7.11 accessory host bound class=SBSystemApertureSceneElementAccessoryPortalView frame={{0,0},{17,22}}
V7.9 aperture container layout class=SBSystemApertureContainerView frame={{125.67,11.33},{172,36.67}}
```

即：`UIApplication.systemApertureControllerForMainDisplay` → `_systemApertureViewController`
→ `_systemApertureManager` → `registeredElements`（按 ScreenRecording identifier 过滤）
→ `elementViewControllerForElement:` → view，配件叶子与药丸容器都拿到了。

之前的问题不是“没找到控制器”，而是**素材挂错层级**（挂在太小的 portal 里 → 缺角）
和**红点选错实例**（全局扫描拿到别的活动）。6.27 这两点都修了：
素材现在直接挂进系统自己的药丸容器，位置由药丸几何决定，跟系统完全一致。

## 保持不变

- 加宽只作用于录屏岛自己的容器，右边缘不动，`target = 来帧 + extra`（不会累积）。
- 全文件零 `masksToBounds = YES`；圆角只用 `cornerRadius`。
- 暂停/恢复不再闪（0.18s 延迟隐藏 + 0.1s 复核）。

## 验证限制

本机无 Theos / iOS SDK，只做源码级验证（Logos 零错误、括号 626/626、无未使用函数、
零 masksToBounds）。`.deb` 由 GitHub Actions macOS runner 编译，实机效果需安装确认。