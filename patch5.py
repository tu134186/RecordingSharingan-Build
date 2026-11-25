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

DUMP = '''// ---------------------------------------------------------------------------
// 结构快照：把屏幕顶部 90pt 内、尺寸不超过 70pt 的视图逐个抄下来。
// 用来确认系统录屏红点的真实类名（类名扫描和颜色扫描都失败时，这是唯一的真相来源）。
// ---------------------------------------------------------------------------
static NSMutableArray<NSString *> *RSProbeStructSnaps = nil;
static NSTimeInterval RSProbeLastDump = 0;

static NSString *RSProbeColorText(UIColor *c) {
    if (!c) return @"nil";
    CGColorRef cg = c.CGColor;
    size_t n = CGColorGetNumberOfComponents(cg);
    const CGFloat *p = CGColorGetComponents(cg);
    if (n == 4) return [NSString stringWithFormat:@"%.2f,%.2f,%.2f,%.2f", p[0], p[1], p[2], p[3]];
    if (n == 2) return [NSString stringWithFormat:@"g%.2f,a%.2f", p[0], p[1]];
    return @"?";
}

static NSString *RSProbeStructureDump(void) {
    NSMutableString *out = [NSMutableString string];
    NSInteger n = 0;
    for (UIWindow *window in RSAllApplicationWindows()) {
        if (!window) continue;
        NSMutableArray<UIView *> *stack = [NSMutableArray arrayWithObject:window];
        NSInteger guard = 0;
        while (stack.count && guard++ < 2500 && n < 45) {
            UIView *v = stack.lastObject;
            [stack removeLastObject];
            if (!v || v == RSSharinganView) continue;
            if (![v isKindOfClass:[UIWindow class]]) {
                CGRect sr = RSV622ScreenRect(v);
                if (!CGRectIsEmpty(sr) && CGRectGetMinY(sr) >= 0 &&
                    CGRectGetMaxY(sr) <= 92.0 &&
                    CGRectGetWidth(sr) <= 72.0 && CGRectGetHeight(sr) <= 72.0) {
                    [out appendFormat:@"    %@  @(%.1f,%.1f) %.1fx%.1f a=%.2f h=%d bg=%@\\n",
                     NSStringFromClass(v.class),
                     CGRectGetMidX(sr), CGRectGetMidY(sr),
                     CGRectGetWidth(sr), CGRectGetHeight(sr),
                     v.alpha, (int)v.hidden,
                     RSProbeColorText(v.backgroundColor)];
                    n++;
                }
            }
            for (UIView *sub in [v.subviews copy]) if (sub) [stack addObject:sub];
        }
    }
    if (n == 0) [out appendString:@"    （顶部没有符合条件的视图）\\n"];
    return out;
}

'''

# 1) 插入结构快照模块（在 Pulse 之前）
rep(
    'static void RSProbePulse(void) {',
    DUMP + 'static void RSProbePulse(void) {',
    'dump-module')

# 2) Pulse 里定时采集 + 0 宽自愈
rep(
    '''        RSProbeAuditPrefs(RSSharinganView);
        RSProbeJudge(nil);
        if (mono - RSProbeLastFlush > 20.0) {''',
    '''        RSProbeAuditPrefs(RSSharinganView);
        RSProbeJudge(nil);

        // 素材被压成 0 宽（塞进空容器）时自愈，否则整段录屏都看不见
        UIImageView *pe = RSSharinganView;
        if (pe && pe.window && pe.bounds.size.width < 1.0) {
            CGFloat fix = RSVisualSideRight ? RSRightSize() : RSLeftSize();
            if (fix > 2.0) {
                @try { pe.bounds = CGRectMake(0, 0, fix, fix); } @catch (...) {}
            }
        }

        // 每 6 秒抄一次顶部结构，最多 8 份
        if (mono - RSProbeLastDump > 6.0) {
            RSProbeLastDump = mono;
            if (!RSProbeStructSnaps) RSProbeStructSnaps = [NSMutableArray array];
            if (RSProbeStructSnaps.count < 8) {
                NSString *snap = [NSString stringWithFormat:@"  ── %@ ──\\n%@",
                    RSProbeTime([[NSDate date] timeIntervalSince1970]), RSProbeStructureDump()];
                [RSProbeStructSnaps addObject:snap];
            }
        }

        if (mono - RSProbeLastFlush > 20.0) {''',
    'pulse-dump')

# 3) 报告输出结构快照
rep(
    '''    [out appendString:@"==================================================\\n"];
    [out appendString:@"把这个文件发给 Minis 就行。\\n"];''',
    '''    [out appendString:@"──────── 三、结构快照（顶部 90pt 内的视图）────────\\n"];
    if (RSProbeStructSnaps.count) {
        for (NSString *snap in RSProbeStructSnaps) [out appendString:snap];
    } else {
        [out appendString:@"（没有采集到）\\n"];
    }
    [out appendString:@"\\n"];

    [out appendString:@"==================================================\\n"];
    [out appendString:@"把这个文件发给 Minis 就行。\\n"];''',
    'render-dump')

# 4) Begin 重置
rep(
    '    RSProbeGraceUntil = RSProbeStartWall + 4.0;\n    RSProbeLastElement = nil;',
    '    RSProbeGraceUntil = RSProbeStartWall + 4.0;\n    RSProbeLastElement = nil;\n    RSProbeStructSnaps = [NSMutableArray array];\n    RSProbeLastDump = 0;',
    'begin-reset-dump')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
