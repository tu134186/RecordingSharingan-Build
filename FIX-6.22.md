# RecordingSharingan 7.11.9.4.3.2.6.22 — 红点锚定挂载

## 症状（用户反馈）
- 单独录屏：素材正常。
- 打开音乐后：素材挂载不出来。
- 再点回音乐播放页：素材没有留在最左边，而是挂到岛的最右边。

## 素材证据（54 秒录屏逐帧测量 + V7 日志 950 行）
1. 只录屏阶段（0~30s）：素材圆心 ≈ 142pt，系统红点同位置，正常。
2. 音乐出现（约 33~37s）：素材消失，右侧独立圆里只有系统红点。
3. 点回音乐页（约 40s 之后）：**系统红点在岛的最左侧（≈142pt），素材却被画在 ≈285pt（最右）**。
4. 日志：`native dot pending` 出现 **633 次**，`native indicator locked` **0 次** —— 红点在整个会话里一次都没被找到。
   日志同时显示 `[SIDEFIX] hierarchy host side=leading`（0~30s）在音乐出现后固定变成
   `side=trailing`，`screenCenter={303,29.67}`，即素材被放进 trailing 容器。

## 根因
1. **红点查找条件太死**：`RSV74LooksLikeNativeIndicator()` 要求宿主窗口必须是
   `SBRecordingIndicatorWindow`。该系统版本的录屏红点是以 Portal / accessory 形式
   渲染在 `SBSystemApertureWindow` 里的（真机值是 5.67×5.67、19.67×19 两种），
   于是 `RSV74GlobalNativeIndicator()` 永远返回 nil。
2. **红点找不到时靠“猜侧别”**：`hierarchyRight = indicator ? … : RSVisualSideRight`，
   而 `RSVisualSideRight` 有 24pt 死区、并在 morph 中被锁死。音乐出现时系统把录屏红点
   搬到长条左侧（leading），缓存里仍是 right，素材就被挂进 trailing 容器 → 素材跑到最右，
   左边只剩系统红点。

## 6.22 做法：一切以“屏幕上真实红点的位置”为准
- 新增 `RSV622DotAnchoredPlacement()`，在 `RSV6SyncEyeToElement()` 最前面执行，命中即 return。
- **宽松红点扫描** `RSV622CollectDots()`：遍历所有窗口，类名含 `RecordingIndicator`、
  尺寸 2~30pt、非隐藏的视图；同时下钻所有类名含 `Portal` 的视图的 `sourceView`
  （Portal 里的红点不在 subviews 里）。被本插件压成 alpha=0 的那颗也保留为合法几何来源。
- **选择锚点**：可见优先 → 落在录屏元素屏幕矩形内优先 → 同分取最靠左（用户期望“岛的最左边”）。
- **宿主由红点自己决定**：沿红点祖先链找 `SBSystemApertureContainerView`（药丸，6.31 验证过
  z 序正确）→ `_SAUIProvidedViewContainerView` → `SBSystemApertureSceneElementAccessory*`；
  红点不在 SystemAperture 子树时（Legacy `SBRecordingIndicatorWindow`），改为
  “红点屏幕点落在哪个 leading/trailing Provided 容器里就挂哪儿”（包含判定，不再猜）。
- **圆心 = 红点圆心**：把红点圆心换算到宿主坐标系（跨窗口用
  `-[UIWindow convertPoint:fromWindow:]`），再叠加设置里的左右 X / Y 微调。
- **侧别照抄红点**：`RSVisualSideRight` / `RSLastWasRight` / 会话侧锁全部由红点真实 x 决定，
  并清掉旧的“右侧过渡抑制”状态（否则素材会被 hide）。
- **红点显隐**：素材可见时把与红点/宿主同区域的红点副本压成 alpha=0（用 associated object
  记原值），撤离时全部还原；停止录屏 `RSRemoveSharingan()` 里调用 `RSV622RestoreDots()`。
- **停用旧迁移机制**：`RSV622AnchoredActive` 为真时，`RSV71187SchedulePresentationMigration()`
  直接返回，避免 6.21 的“猜宿主后迁移”把素材再搬走（真机上就是两边抢素材）。
- **性能**：逐帧同步不做全树扫描 —— 红点指针缓存 0.30s，红点显隐同 0.40s 一次、
  或宿主/可见性变化时立即执行。

## 诊断日志（新增）
- `[V6.22] dot candidate …`（3 秒一次，列出所有候选红点：类名、屏幕矩形、alpha、窗口类、父类）
- `[V6.22] dot anchor dot=… host=… side=… center={…} size=…`（1 秒一次，锚定结果）
- `[V6.22] dot found but no host …`（找到红点但找不到可用宿主时）

## 验证要点（下次真机）
1. 只录屏：素材仍在左侧、与红点同心。
2. 播放音乐后：素材应出现在**红点所在的位置**，日志出现 `dot anchor`（`fromDot=1` 更好）。
3. 点回音乐页 / 切换 App：素材跟随红点，不再固定在最右。
4. 若仍不出现，日志里的 `dot candidate` 列表会直接暴露红点类名与所在容器，可据此继续收口。