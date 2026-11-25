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

FAKE = '''// 判断「这个红点是不是假的」：App 图标角标（SBIconBadgeView / SBDarkeningImageView）
// 会被误认成录屏红点，必须排除，否则锚定逻辑会拿它当标尺。
static BOOL RSV631LooksFakeDot(UIView *dot) {
    if (!dot) return YES;
    NSString *cls = NSStringFromClass(dot.class);
    if ([cls rangeOfString:@"Darkening"].location != NSNotFound) return YES;
    if ([cls rangeOfString:@"IconBadge"].location != NSNotFound) return YES;
    NSInteger hops = 0;
    for (UIView *p = dot.superview; p && hops++ < 6; p = p.superview) {
        if (RSV622ClassHas(p, @"IconBadge") || RSV622ClassHas(p, @"SBIconView")) return YES;
    }
    return NO;
}

'''

rep(
    '// 从候选里挑最像「系统录屏红点」的那个：接近方形、直径 12pt 左右、落在录屏元素内、靠左',
    FAKE + '// 从候选里挑最像「系统录屏红点」的那个：接近方形、直径 12pt 左右、落在录屏元素内、靠左',
    'fake-detector')

OLD_HEAD = '''    // 6.29：accessory 锚定优先。
    // 这台系统的红点类名不含 RecordingIndicator，类名扫描会把 App 图标角标
    // （SBDarkeningImageView / SBIconBadgeView）当成红点，全程都是错的。
    // 而「录屏装饰 accessory」的结构位置是稳定的（始终在岛最左端、宽 17~26pt），
    // 所以直接走这条不依赖红点的路。
    if (RSV628AccessoryAnchoredPlacement(element, allowShow)) return YES;

    UIView *dot = RSV622FastDot(element);
    if (!dot || !dot.window) {
        dot = RSProbeBestRedDot(element);
        if (dot) { RSV622CachedDot = dot; RSV622CachedDotAt = CACurrentMediaTime(); }
    }
    if (!dot || !dot.window) {
        // 6.28：红点彻底找不到时，改用「录屏装饰 accessory」定位，不再退回猜侧别
        if (RSV628AccessoryAnchoredPlacement(element, allowShow)) return YES;
        RSV622AnchoredActive = NO;
        return NO;
    }'''

NEW_HEAD = '''    // 6.31：红点优先（portal 渲染的红点现在能拿到屏幕位置了），accessory 只作兜底。
    // 类名扫描拿到的 App 图标角标（SBDarkeningImageView / SBIconBadgeView）必须丢掉。
    UIView *dot = RSV622FastDot(element);
    if (dot && RSV631LooksFakeDot(dot)) dot = nil;
    if (!dot) {
        dot = RSProbeBestRedDot(element);
        if (dot && RSV631LooksFakeDot(dot)) dot = nil;
        if (dot) { RSV622CachedDot = dot; RSV622CachedDotAt = CACurrentMediaTime(); }
    }
    if (!dot) {
        // 红点彻底找不到时，改用「录屏装饰 accessory」定位，不再退回猜侧别
        if (RSV628AccessoryAnchoredPlacement(element, allowShow)) return YES;
        RSV622AnchoredActive = NO;
        return NO;
    }
    if (!dot.window && CGRectIsEmpty(RSProbeDotScreenRect(dot))) {
        if (RSV628AccessoryAnchoredPlacement(element, allowShow)) return YES;
        RSV622AnchoredActive = NO;
        return NO;
    }'''

rep(OLD_HEAD, NEW_HEAD, 'dot-first')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
