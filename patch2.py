import sys

p = '/var/minis/workspace/rs/Tweak.xm'
s = open(p, encoding='utf-8').read()

def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        print(f'FAIL {tag}: {n} occurrences')
        sys.exit(1)
    s = s.replace(old, new)

# 1) 新增问题类型
rep(
    '    RSProbeKindClipped = 5,\n};',
    '    RSProbeKindClipped = 5,\n    RSProbeKindNoDot   = 6,\n};',
    'enum')

# 2) 自检统计变量
rep(
    'static NSInteger RSProbeSamples = 0;\nstatic NSString *RSProbeFile = nil;',
    '''static NSInteger RSProbeSamples = 0;
static NSString *RSProbeFile = nil;
// 自检：探针自己有没有真的在判，而不是静默跳过
static NSInteger RSProbeStatTicks = 0;
static NSInteger RSProbeStatNoEye = 0;
static NSInteger RSProbeStatNoDot = 0;
static NSInteger RSProbeStatDotOff = 0;
static NSInteger RSProbeStatJudged = 0;
static NSInteger RSProbeStatEyeHidden = 0;''',
    'stats')

# 3) Judge 各分支计数
rep(
    '''static void RSProbeJudge(UIView *element) {
    UIImageView *eye = RSSharinganView;
    if (!element || !eye) return;

    UIView *dot = RSV622BestDotForElement(element);
    if (!dot || !dot.window) return;
    UIView *anchor = RSV622AnchorForDot(dot);
    CGRect dotRect = RSV622ScreenRect(anchor);
    if (CGRectIsEmpty(dotRect)) return;
    if (!CGRectIntersectsRect(dotRect, [UIScreen mainScreen].bounds)) return;''',
    '''static void RSProbeJudge(UIView *element) {
    UIImageView *eye = RSSharinganView;
    if (!element || !eye) { RSProbeStatNoEye++; return; }

    UIView *dot = RSV622BestDotForElement(element);
    if (!dot || !dot.window) {
        RSProbeStatNoDot++;
        if (RSProbeStatNoDot > 3) {
            RSProbeAppend(RSProbeKindNoDot, @"探针找不到系统红点",
                          @"没有标尺就没法判断素材位置对不对——这时候素材位置只能靠猜，很容易跑偏",
                          RSProbeContext(element, nil, eye));
        }
        return;
    }
    UIView *anchor = RSV622AnchorForDot(dot);
    CGRect dotRect = RSV622ScreenRect(anchor);
    if (CGRectIsEmpty(dotRect) || !CGRectIntersectsRect(dotRect, [UIScreen mainScreen].bounds)) {
        RSProbeStatDotOff++;
        return;
    }
    RSProbeStatJudged++;''',
    'judge-head')

# 4) eye 不可见分支：红点也不亮时计入 hidden
rep(
    '''    if (!eyeVisible) return;

    CGRect eyeRect = RSV622ScreenRect(eye);''',
    '''    if (!eyeVisible) { RSProbeStatEyeHidden++; return; }

    CGRect eyeRect = RSV622ScreenRect(eye);''',
    'judge-hidden')

# 5) Tick 计数
rep(
    '    RSProbeSamples++;\n    @try {\n        RSProbeCloseStale();',
    '    RSProbeSamples++;\n    RSProbeStatTicks++;\n    @try {\n        RSProbeCloseStale();',
    'tick-count')

# 6) Begin 重置
rep(
    '    RSProbeLastTick = 0;\n    RSProbeSamples = 0;',
    '    RSProbeLastTick = 0;\n    RSProbeSamples = 0;\n    RSProbeStatTicks = 0;\n    RSProbeStatNoEye = 0;\n    RSProbeStatNoDot = 0;\n    RSProbeStatDotOff = 0;\n    RSProbeStatJudged = 0;\n    RSProbeStatEyeHidden = 0;',
    'begin-reset')

# 7) 报告里加自检段
rep(
    '''    [out appendString:@"──────── 一、设置改动记录 ────────\\n"];''',
    '''    [out appendString:@"──────── 〇、探针自检 ────────\\n"];
    [out appendFormat:@"检查 %ld 次，其中真正完成比对的 %ld 次\\n",
     (long)RSProbeStatTicks, (long)RSProbeStatJudged];
    if (RSProbeStatNoEye)     [out appendFormat:@"  · 素材不存在（没创建/已销毁）：%ld 次\\n", (long)RSProbeStatNoEye];
    if (RSProbeStatNoDot)     [out appendFormat:@"  · 找不到系统红点（无法判定位置）：%ld 次\\n", (long)RSProbeStatNoDot];
    if (RSProbeStatDotOff)    [out appendFormat:@"  · 红点在屏幕外：%ld 次\\n", (long)RSProbeStatDotOff];
    if (RSProbeStatEyeHidden) [out appendFormat:@"  · 红点没亮，素材也没显示：%ld 次\\n", (long)RSProbeStatEyeHidden];
    if (RSProbeStatJudged == 0) {
        [out appendString:@"\\n⚠️ 一次有效比对都没做成，下面的「没发现问题」不可信。\\n"];
    }
    [out appendString:@"\\n"];

    [out appendString:@"──────── 一、设置改动记录 ────────\\n"];''',
    'render-stats')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
