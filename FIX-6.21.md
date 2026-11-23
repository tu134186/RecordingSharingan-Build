# 6.21 灵动岛左边缘加宽 + 素材跟随系统呈现位置

基于 6.20 源码（含 FIX-6.20.md 内的全部改动）。

## 需求

1. 灵动岛“总宽度”左边加 7pt。
2. 录屏后加载素材时，素材要跟着系统自己的呈现位置走（系统有时放在左边、有时放在右边）。

## 改动

### 1. 灵动岛总宽度左侧 +7pt（仅录屏会话内）

- `SBSystemApertureContainerView -setFrame:` 里把系统给的 frame 改成
  `origin.x -= extra`、`size.width += extra`，右边缘保持不动，即只向左加宽。
- `extra` 来自新的设置项 `islandLeftExtra`，默认 `7.0`，范围 0–20，0 表示关闭。
- 反递归保护：用弱键 `NSMapTable` 记录“我们真正改写过的 frame”。
  - 系统把加宽后的 frame 原样回灌 → 直接放行，不二次加宽；
  - 系统基于加宽后的 bounds 重新算出一个同宽 frame（只改 origin/center 的布局轮次）→ 也放行；
  - 只有出现新的、未加宽的宽度时才继续叠加 7pt。
  这样不会像旧版 +5pt 方案那样每轮布局再多加一点。
- 只在 `RSRecordingActive` 为真时加宽（包含暂停面板的 1.35s 宽限），
  所以暂停/恢复不会让岛宽来回跳 7pt。
- 停止录屏后 `RSRemoveSharingan()` 调用 `RSIslandForgetFrames()` 清空记录；
  之后系统一布局，frame 就回到原生宽度。
- 日志：`[V7.11.9.4.3.2.6.21] island width extend left=7.0 native=... -> ...`（限流 0.5s 一条）。
  `control`、`VERSION.txt`、`RSVersion`、Prefs `Info.plist` 同步到 7.11.9.4.3.2.6.21。

### 2. 素材跟随系统自己的呈现位置

- 素材的锚点仍然是系统自己的呈现叶子：
  优先 `SBRecordingIndicatorView` 的父视图（真红点路径），
  否则 `SBSystemApertureSceneElementAccessoryPortalView`（22x22 呈现叶子）。
  没有加入任何固定偏移，也没有把 7pt 加宽量写进素材坐标。
- 加宽发生后立刻合并刷新一次（`RS20ScheduleRefresh()`），
  让素材当帧就按系统新的布局重新同步，不会停在旧位置。
- 左右侧依旧由 `RSPreferenceSideForHost()` 按宿主在屏幕上的实际位置判定（中间有死区，
  避免 morph 过程中左右反复横跳），所以系统把录屏放到左边就用左侧素材/尺寸，放到右边就切右侧。
- 逐帧 `CADisplayLink` 同步保持不变，素材随系统动画/形变跟随。

## 可调项

设置 → 录屏写轮眼 → 灵动岛宽度 → 左侧加宽（默认 7.0，步进 0.1，0 = 关闭）。
“恢复默认参数”会把该值一起恢复成 7.0。

## 云端编译失败（BuildMate BM-F2BD099E / Codemagic 6b03ef18）取证结论

- 诊断包里的 `16-Codemagic-compile.log` 与 `15-Codemagic-Artifacts-01.zip` 中的 `src/compile.log`
  实际是 **BuildMate.app 自己的 `xcodebuild -project ./BuildMate.xcodeproj`**，结尾是 `** BUILD SUCCEEDED **`，
  不是本插件 Theos 的编译输出。
- `10-真实错误定位.txt`：`有效错误行：0；一般失败提示：0`——没有任何编译错误行被捕获。
- 时间线：15:45:29 派发 → 15:47:29 失败，**总共约 2 分钟**。Theos 克隆（`--recursive`）+ `brew install ldid`
  + `make package` 不可能在 2 分钟内跑完，所以失败点在流水线准备阶段（第 1–3 步），而不是源码编译。
- 时间线同时写明：本次源码 SHA-256 = `dbd51ff7…`、`bytes=208145`，与本次上传的
  `RecordingSharingan-7.11.9.4.3.2.6.21-source.zip` 完全一致（我本地复核：208145 字节）。
  即 ZIP 本身已正确送达，工程识别条件（根目录同时存在 `Makefile` 与 `control`）也已满足。

结论：这次失败不能用来说明 6.21 源码编译不通过；要定位真实报错，需要这次 Run 的
`src/compile-errors.txt`（或完整 `src/compile.log`）。

## 本机为什么不能直接出 deb

本机是 iPhone 上的 iSH（Alpine aarch64），没有 macOS / Xcode / iPhoneOS SDK：
Theos 的 Linux 预编译工具链只有 x86_64（glibc），aarch64 musl 无法执行；
生成 Mach-O dylib 还需要 ld64，Alpine 没有；剩余磁盘仅约 1.4GB，装不下 SDK。
因此这里只能做源码级校验（Logos 预处理、plist 解析、括号/版本一致性），
`.deb` 必须在 macOS（或云端 macOS Runner）上生成。

## 验证限制

本机无法编译 Theos 工程，也无法在设备上重现。以上仅为源码级改动：
- 未验证 `SBSystemApertureContainerView` 的黑色胶囊是否确实按 bounds 宽度绘制（若系统另有 backdrop 视图且宽度写死，加宽可能不生效）；
- 未验证加宽后系统是否会以 7pt 为步长反向自增（已用回灌识别拦截，但仍需看日志确认
  `island width extend` 是否只在几何真正变化时出现）；
- 云端编译成功只能证明源码可编译，真实效果仍需装到设备上确认。