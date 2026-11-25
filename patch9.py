import sys, re

p = '/var/minis/workspace/rs/Tweak.xm'
s = open(p, encoding='utf-8').read()

def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        print(f'FAIL {tag}: {n} occurrences')
        sys.exit(1)
    s = s.replace(old, new)

OLD_SCAN = '''static NSArray<UIView *> *RSProbeScanRedDots(void) {
    NSMutableArray<UIView *> *raw = [NSMutableArray array];
    CGRect screen = [UIScreen mainScreen].bounds;
    for (UIWindow *window in RSAllApplicationWindows()) {
        if (!window) continue;
        NSMutableArray<UIView *> *stack = [NSMutableArray arrayWithObject:window];
        NSInteger guard = 0;
        while (stack.count && guard++ < 1500) {
            UIView *v = stack.lastObject;
            [stack removeLastObject];
            if (!v || v == RSSharinganView) continue;
            if (v.window && !v.hidden && v.alpha > 0.05) {
                CGFloat w = CGRectGetWidth(v.bounds), h = CGRectGetHeight(v.bounds);
                if (w >= 2.0 && h >= 2.0 && w <= 40.0 && h <= 40.0) {
                    CGRect sr = RSV622ScreenRect(v);
                    if (!CGRectIsEmpty(sr) && CGRectIntersectsRect(sr, screen) &&
                        CGRectGetMinY(sr) < 140.0 && RSRedScoreInView(v, 0) >= 50) {
                        [raw addObject:v];
                    }
                }
            }
            if (RSV622ClassHas(v, @"Portal")) {
                UIView *src = nil;
                @try {
                    id sv = [v valueForKey:@"sourceView"];
                    if ([sv isKindOfClass:[UIView class]]) src = (UIView *)sv;
                } @catch (...) {}
                if (src) [stack addObject:src];
            }
            for (UIView *sub in [v.subviews copy]) if (sub) [stack addObject:sub];
        }
    }'''

NEW_SCAN = '''static const void *RSProbeDotScreenRectKey = &RSProbeDotScreenRectKey;

// 红点真正的屏幕位置：自己挂在窗口上就用自己；
// 如果它是某个 Portal 的 sourceView（window 为 nil，拿不到坐标），就用那个 Portal 的位置。
// —— 这就是之前颜色扫描一直漏掉系统红点的原因：它被 portal 渲染，window 是空的。
static CGRect RSProbeDotScreenRect(UIView *dot) {
    if (!dot) return CGRectZero;
    CGRect r = RSV622ScreenRect(dot);
    if (!CGRectIsEmpty(r)) return r;
    NSValue *v = objc_getAssociatedObject(dot, RSProbeDotScreenRectKey);
    return v ? v.CGRectValue : CGRectZero;
}

static NSArray<UIView *> *RSProbeScanRedDots(void) {
    NSMutableArray<UIView *> *raw = [NSMutableArray array];
    CGRect screen = [UIScreen mainScreen].bounds;
    for (UIWindow *window in RSAllApplicationWindows()) {
        if (!window) continue;
        NSMutableArray<UIView *> *stack = [NSMutableArray arrayWithObject:window];
        NSInteger guard = 0;
        while (stack.count && guard++ < 1800) {
            UIView *v = stack.lastObject;
            [stack removeLastObject];
            if (!v || v == RSSharinganView) continue;

            CGRect sr = RSProbeDotScreenRect(v);
            if (!v.hidden && v.alpha > 0.02 && !CGRectIsEmpty(sr) &&
                CGRectIntersectsRect(sr, screen) && CGRectGetMinY(sr) < 150.0) {
                CGFloat w = CGRectGetWidth(v.bounds), h = CGRectGetHeight(v.bounds);
                if (w >= 3.0 && h >= 3.0 && w <= 40.0 && h <= 40.0) {
                    NSInteger score = RSRedScoreInView(v, 0);
                    if ([v isKindOfClass:[UIImageView class]]) score += 30;
                    if (score >= 25) [raw addObject:v];
                }
            }

            if (RSV622ClassHas(v, @"Portal")) {
                UIView *src = nil;
                @try {
                    id sv = [v valueForKey:@"sourceView"];
                    if ([sv isKindOfClass:[UIView class]]) src = (UIView *)sv;
                } @catch (...) {}
                CGRect pr = RSV622ScreenRect(v);
                if (src && !CGRectIsEmpty(pr)) {
                    // portal 显示到哪儿，它里面的红点就在哪儿
                    objc_setAssociatedObject(src, RSProbeDotScreenRectKey,
                                             [NSValue valueWithCGRect:pr],
                                             OBJC_ASSOCIATION_RETAIN_NONATOMIC);
                    [stack addObject:src];
                }
            }
            for (UIView *sub in [v.subviews copy]) if (sub) [stack addObject:sub];
        }
    }'''

rep(OLD_SCAN, NEW_SCAN, 'scan')

# 评分/候选文本用新的位置函数
rep(
    '''    for (UIView *v in reds) {
        CGRect r = RSV622ScreenRect(v);
        CGFloat w = CGRectGetWidth(r), h = CGRectGetHeight(r);
        if (w <= 0 || h <= 0) continue;''',
    '''    for (UIView *v in reds) {
        CGRect r = RSProbeDotScreenRect(v);
        CGFloat w = CGRectGetWidth(r), h = CGRectGetHeight(r);
        if (w <= 0 || h <= 0) continue;''',
    'best-dot-rect')

rep(
    '''        if (n++ >= 6) { [s appendString:@"    …\\n"]; break; }
        CGRect r = RSV622ScreenRect(v);''',
    '''        if (n++ >= 6) { [s appendString:@"    …\\n"]; break; }
        CGRect r = RSProbeDotScreenRect(v);''',
    'candidate-rect')

# DotAnchoredPlacement 里用新的位置函数
rep(
    '''    UIView *dotAnchor = RSV622AnchorForDot(dot);
    CGRect dotScreen = RSV622ScreenRect(dotAnchor);
    if (CGRectIsEmpty(dotScreen)) { RSV622AnchoredActive = NO; return NO; }''',
    '''    UIView *dotAnchor = RSV622AnchorForDot(dot);
    CGRect dotScreen = RSProbeDotScreenRect(dot);
    if (CGRectIsEmpty(dotScreen)) dotScreen = RSV622ScreenRect(dotAnchor);
    if (CGRectIsEmpty(dotScreen)) { RSV622AnchoredActive = NO; return NO; }''',
    'anchor-rect')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
