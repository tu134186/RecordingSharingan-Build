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

# 1) 关联的 portal 位置优先（sourceView 自己的坐标往往是离屏的假坐标）
rep(
    '''static CGRect RSProbeDotScreenRect(UIView *dot) {
    if (!dot) return CGRectZero;
    CGRect r = RSV622ScreenRect(dot);
    if (!CGRectIsEmpty(r)) return r;
    NSValue *v = objc_getAssociatedObject(dot, RSProbeDotScreenRectKey);
    return v ? v.CGRectValue : CGRectZero;
}''',
    '''static CGRect RSProbeDotScreenRect(UIView *dot) {
    if (!dot) return CGRectZero;
    // Portal 里面的视图：屏幕上真正显示的位置是 Portal 的位置，
    // 它自己的 convertRect 往往返回离屏坐标（甚至 (0,0)），必须优先用关联值。
    NSValue *pv = objc_getAssociatedObject(dot, RSProbeDotScreenRectKey);
    if (pv) return pv.CGRectValue;
    return RSV622ScreenRect(dot);
}''',
    'prefer-portal-rect')

# 2) 位置向下传递：portal 的位置要传给 sourceView 的整棵子树
rep(
    '''                if (src && !CGRectIsEmpty(pr)) {
                    // portal 显示到哪儿，它里面的红点就在哪儿
                    objc_setAssociatedObject(src, RSProbeDotScreenRectKey,
                                             [NSValue valueWithCGRect:pr],
                                             OBJC_ASSOCIATION_RETAIN_NONATOMIC);
                    [stack addObject:src];
                }
            }
            for (UIView *sub in [v.subviews copy]) if (sub) [stack addObject:sub];''',
    '''                if (src && !CGRectIsEmpty(pr)) {
                    // portal 显示到哪儿，它里面的红点就在哪儿
                    objc_setAssociatedObject(src, RSProbeDotScreenRectKey,
                                             [NSValue valueWithCGRect:pr],
                                             OBJC_ASSOCIATION_RETAIN_NONATOMIC);
                    [stack addObject:src];
                }
            }
            // 把「我这一支在屏幕上的位置」传给子视图（portal 子树全靠这个）
            NSValue *inherit = objc_getAssociatedObject(v, RSProbeDotScreenRectKey);
            for (UIView *sub in [v.subviews copy]) {
                if (!sub) continue;
                if (inherit && CGRectIsEmpty(RSV622ScreenRect(sub))) {
                    objc_setAssociatedObject(sub, RSProbeDotScreenRectKey, inherit,
                                             OBJC_ASSOCIATION_RETAIN_NONATOMIC);
                }
                [stack addObject:sub];
            }''',
    'inherit-rect')

# 3) 探针判断也用同一个红点来源，否则永远报「找不到红点」
rep(
    '''    UIView *dot = RSV622BestDotForElement(el);
    if (!dot || !dot.window) {
        RSProbeStatNoDot++;''',
    '''    UIView *dot = RSV622BestDotForElement(el);
    if (!dot || !dot.window) dot = RSProbeBestRedDot(el);
    if (!dot || CGRectIsEmpty(RSProbeDotScreenRect(dot))) {
        RSProbeStatNoDot++;''',
    'judge-same-source')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
