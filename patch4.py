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

REDSCAN = '''// ---------------------------------------------------------------------------
// 按颜色找红点（不依赖类名）
// 系统改过红点的类名、或者把红点塞进 portal 的 sourceView 时，类名扫描会全军覆没。
// 这里直接在屏幕顶部区域里找「红色的小方块/圆点」，作为最后的兜底。
// ---------------------------------------------------------------------------
static NSArray<UIView *> *RSProbeScanRedDots(void) {
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
    }
    // 只保留最内层：祖先也命中时丢掉祖先，避免把整个容器当红点
    NSMutableArray<UIView *> *out = [NSMutableArray array];
    for (UIView *v in raw) {
        BOOL ancestor = NO;
        for (UIView *o in raw) {
            if (o != v && [o isDescendantOfView:v]) { ancestor = YES; break; }
        }
        if (!ancestor) [out addObject:v];
    }
    return out;
}

// 从候选里挑最像「系统录屏红点」的那个：接近方形、直径 12pt 左右、落在录屏元素内、靠左
static UIView *RSProbeBestRedDot(UIView *element) {
    NSArray<UIView *> *reds = RSProbeScanRedDots();
    if (!reds.count) return nil;
    CGRect er = element ? RSV622ScreenRect(element) : CGRectZero;
    UIView *best = nil;
    CGFloat bestScore = -1e9;
    for (UIView *v in reds) {
        CGRect r = RSV622ScreenRect(v);
        CGFloat w = CGRectGetWidth(r), h = CGRectGetHeight(r);
        if (w <= 0 || h <= 0) continue;
        CGFloat score = 0.0;
        score -= fabs(w - h) * 3.0;                  // 方形优先
        score -= fabs((w + h) / 2.0 - 12.0) * 2.0;   // 直径接近 12pt
        if (!CGRectIsEmpty(er) && CGRectIntersectsRect(er, r)) score += 100.0;
        score -= CGRectGetMidX(r) * 0.2;             // 靠左优先
        if (score > bestScore) { bestScore = score; best = v; }
    }
    return best;
}

static NSString *RSProbeCandidateText(void) {
    NSArray<UIView *> *reds = RSProbeScanRedDots();
    NSMutableString *s = [NSMutableString string];
    [s appendFormat:@"    屏幕上「顶部红色小点」候选 %lu 个：\\n", (unsigned long)reds.count];
    NSInteger n = 0;
    for (UIView *v in reds) {
        if (n++ >= 6) { [s appendString:@"    …\\n"]; break; }
        CGRect r = RSV622ScreenRect(v);
        [s appendFormat:@"      · %@  (%.0f, %.0f)  %.1f×%.1f  alpha=%.2f\\n",
         NSStringFromClass(v.class), CGRectGetMidX(r), CGRectGetMidY(r),
         CGRectGetWidth(r), CGRectGetHeight(r), v.alpha];
    }
    return s;
}

'''

# 1) 插入红色扫描模块
rep(
    '// 返回 YES 表示已经按真实红点落位，后续旧路径全部跳过。\nstatic BOOL RSV622DotAnchoredPlacement',
    REDSCAN + '// 返回 YES 表示已经按真实红点落位，后续旧路径全部跳过。\nstatic BOOL RSV622DotAnchoredPlacement',
    'redscan')

# 2) 红点找不到时走颜色兜底
rep(
    '''    UIView *dot = RSV622FastDot(element);
    if (!dot || !dot.window) { RSV622AnchoredActive = NO; return NO; }''',
    '''    UIView *dot = RSV622FastDot(element);
    if (!dot || !dot.window) {
        dot = RSProbeBestRedDot(element);
        if (dot) { RSV622CachedDot = dot; RSV622CachedDotAt = CACurrentMediaTime(); }
    }
    if (!dot || !dot.window) { RSV622AnchoredActive = NO; return NO; }''',
    'dot-fallback')

# 3) 宿主找不到时，沿用素材当前挂着的那个药丸
rep(
    '''    if (!host || !host.window) {
        NSTimeInterval now = CACurrentMediaTime();
        if (now - RSV622LastAnchorLog > 1.0) {
            RSV622LastAnchorLog = now;
            RSLog(@"[V6.22] dot found but no host dot=%@ screen=%@ chain=%@",''',
    '''    if (!host || !host.window) {
        UIView *curHost = RSSharinganView.superview;
        if (curHost && (RSV622ClassHas(curHost, @"ApertureContainer") ||
                        RSV622ClassHas(curHost, @"ProvidedView"))) {
            host = curHost;
            fromDot = NO;
        }
    }
    if (!host || !host.window) {
        NSTimeInterval now = CACurrentMediaTime();
        if (now - RSV622LastAnchorLog > 1.0) {
            RSV622LastAnchorLog = now;
            RSLog(@"[V6.22] dot found but no host dot=%@ screen=%@ chain=%@",''',
    'host-fallback')

# 4) 探针报「找不到红点」时附上候选
rep(
    '''        if (RSProbeStatNoDot > 3) {
            RSProbeAppend(RSProbeKindNoDot, @"探针找不到系统红点",
                          @"没有标尺就没法判断素材位置对不对——这时候素材位置只能靠猜，很容易跑偏",
                          RSProbeContext(element, nil, eye));
        }''',
    '''        if (RSProbeStatNoDot > 3 && (RSProbeStatNoDot % 5) == 1) {
            NSString *detail = [NSString stringWithFormat:
                @"没有标尺就没法判断素材位置对不对——这时候素材位置只能靠猜，很容易跑偏\\n%@",
                RSProbeCandidateText()];
            RSProbeAppend(RSProbeKindNoDot, @"探针找不到系统红点", detail,
                          RSProbeContext(element, nil, eye));
        }''',
    'probe-candidates')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
