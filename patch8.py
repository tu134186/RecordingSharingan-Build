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

# 1) 报告改为固定文件名，每次录屏覆盖旧的
rep(
    '    RSProbeFile = [NSString stringWithFormat:@"/var/mobile/RS-report-%@.txt", RSProbeStamp()];',
    '''    // 固定文件名：每次录屏覆盖上一份，不会越积越多
    RSProbeFile = @"/var/mobile/RS-report.txt";''',
    'fixed-report-name')

# 2) accessory 选择加迟滞：上次那个还有效就继续用，避免 morph 中来回跳
rep(
    '''static UIView *RSV628RecordingAccessory(void) {
    NSMutableArray<UIView *> *cands = [NSMutableArray array];''',
    '''static __weak UIView *RSV628StickyAccessory = nil;

static UIView *RSV628RecordingAccessory(void) {
    // 迟滞：上一帧选中的 accessory 还在屏幕上、尺寸也合理，就继续用它。
    // morph 过程中系统会不停重建 accessory，没有迟滞的话素材会来回横跳。
    UIView *sticky = RSV628StickyAccessory;
    if (sticky && sticky.window) {
        CGRect sr = RSV622ScreenRect(sticky);
        CGFloat w = CGRectGetWidth(sr), h = CGRectGetHeight(sr);
        if (!CGRectIsEmpty(sr) && w >= 8.0 && h >= 12.0 &&
            CGRectIntersectsRect(sr, [UIScreen mainScreen].bounds)) {
            return sticky;
        }
    }

    NSMutableArray<UIView *> *cands = [NSMutableArray array];''',
    'sticky-head')

rep(
    '''    UIView *best = nil;
    CGFloat bestX = 1.0e9;
    for (UIView *v in cands) {
        CGFloat x = CGRectGetMidX(RSV622ScreenRect(v));
        if (x < bestX) { bestX = x; best = v; }
    }
    return best;
}''',
    '''    UIView *best = nil;
    CGFloat bestX = 1.0e9;
    for (UIView *v in cands) {
        CGFloat x = CGRectGetMidX(RSV622ScreenRect(v));
        if (x < bestX) { bestX = x; best = v; }
    }
    if (best) RSV628StickyAccessory = best;
    return best;
}''',
    'sticky-tail')

# 3) 录屏结束时清掉迟滞
rep(
    'static void RSProbeFinish(void) {\n    if (!RSProbeFile) return;\n    RSProbeStopTimer();',
    'static void RSProbeFinish(void) {\n    if (!RSProbeFile) return;\n    RSProbeStopTimer();\n    RSV628StickyAccessory = nil;',
    'clear-sticky')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
