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

BLOCK = '''// ---------------------------------------------------------------------------
// 6.28：不依赖红点的定位
// 结构实测（22:06:40 快照）：
//   录屏装饰 accessory = SBSystemApertureSceneElementAccessoryView
//      宽 17~26pt、高 22pt，始终贴在灵动岛最左端
//   音乐/通话的是 36.7×36.7 的独立 SBSystemApertureContainerView
// 所以：找到那个窄 accessory，再往上找药丸容器，把素材挂进药丸、对齐 accessory 中心。
// 这样素材永远有整颗药丸的高度可用，不会被 26×22 的窄格子压扁。
// ---------------------------------------------------------------------------
static UIView *RSV628RecordingAccessory(void) {
    NSMutableArray<UIView *> *cands = [NSMutableArray array];
    CGRect screen = [UIScreen mainScreen].bounds;
    for (UIWindow *window in RSAllApplicationWindows()) {
        if (!window) continue;
        NSMutableArray<UIView *> *stack = [NSMutableArray arrayWithObject:window];
        NSInteger guard = 0;
        while (stack.count && guard++ < 2000) {
            UIView *v = stack.lastObject;
            [stack removeLastObject];
            if (!v) continue;
            if (RSV622ClassHas(v, @"SBSystemApertureSceneElementAccessoryView")) {
                CGRect sr = RSV622ScreenRect(v);
                CGFloat w = CGRectGetWidth(sr), h = CGRectGetHeight(sr);
                if (!CGRectIsEmpty(sr) && CGRectIntersectsRect(sr, screen) &&
                    w >= 10.0 && w <= 40.0 && h >= 14.0 && h <= 40.0) {
                    [cands addObject:v];
                }
            }
            for (UIView *sub in [v.subviews copy]) if (sub) [stack addObject:sub];
        }
    }
    UIView *best = nil;
    CGFloat bestX = 1.0e9;
    for (UIView *v in cands) {
        CGFloat x = CGRectGetMidX(RSV622ScreenRect(v));
        if (x < bestX) { bestX = x; best = v; }
    }
    return best;
}

static UIView *RSV628PillForAccessory(UIView *acc) {
    NSInteger hops = 0;
    for (UIView *p = acc; p && hops++ < 16; p = p.superview) {
        if (RSV622ClassHas(p, @"SBSystemApertureContainerView")) {
            CGRect r = RSV622ScreenRect(p);
            if (!CGRectIsEmpty(r) && CGRectGetHeight(r) >= 24.0) return p;
        }
    }
    return nil;
}

static BOOL RSV628AccessoryAnchoredPlacement(UIView *element, BOOL allowShow) {
    UIImageView *eye = RSSharinganView;
    if (!eye || !element) return NO;

    UIView *acc = RSV628RecordingAccessory();
    if (!acc) return NO;
    UIView *pill = RSV628PillForAccessory(acc);
    if (!pill || !pill.window) return NO;

    CGRect accScreen = RSV622ScreenRect(acc);
    if (CGRectIsEmpty(accScreen)) return NO;

    CGPoint accCenter = CGPointMake(CGRectGetMidX(accScreen), CGRectGetMidY(accScreen));
    BOOL right = RSV622ScreenRight(accCenter.x);
    RSVisualSideRight = right;
    RSLastWasRight = right;
    RSSessionSideLocked = YES;
    RSSessionLockedRight = right;
    RSRightTransitionSuppressed = NO;
    RSRightTransitionStableSince = 0;
    RSRightTransitionSuppressedAt = 0;
    RSRightForceAnchorUntil = 0;

    if (eye.superview != pill) {
        [eye removeFromSuperview];
        [pill addSubview:eye];
    }
    [pill bringSubviewToFront:eye];
    RSEyeHostElement = pill;
    RSApplyMaterialForSide(eye, right);

    CGFloat configured = right ? RSRightSize() : RSLeftSize();
    CGFloat pillH = CGRectGetHeight(RSV622ScreenRect(pill));
    if (pillH > 8.0 && configured > pillH) configured = pillH;
    if (configured < 2.0) configured = 31.0;

    CGPoint center = RSV622WindowPointToView(accCenter, pill, acc.window);
    center.x += right ? RSRightXOffset() : RSLeftXOffset();
    center.y += RSYOffset();

    [UIView performWithoutAnimation:^{
        eye.bounds = CGRectMake(0, 0, configured, configured);
        eye.center = center;
    }];

    BOOL visible = allowShow && !RSEyeGracePaused && !RSEyeResumeVisibilityPending;
    if (visible) { eye.hidden = NO; eye.alpha = 1.0; }
    RSV622AnchoredActive = YES;

    NSTimeInterval now = CACurrentMediaTime();
    if (now - RSV622LastAnchorLog > 1.0) {
        RSV622LastAnchorLog = now;
        RSLog(@"[V6.28] accessory anchor acc=%@ accScreen=%@ pill=%@ pillScreen=%@ side=%@ size=%.2f",
              NSStringFromClass(acc.class), NSStringFromCGRect(accScreen),
              NSStringFromClass(pill.class), NSStringFromCGRect(RSV622ScreenRect(pill)),
              right ? @"right" : @"left", configured);
    }
    return YES;
}

'''

# 1) 插入模块（在 RSProbeScanRedDots 之前，即 DotAnchoredPlacement 区域内）
rep(
    '''// ---------------------------------------------------------------------------
// 按颜色找红点（不依赖类名）''',
    BLOCK + '''// ---------------------------------------------------------------------------
// 按颜色找红点（不依赖类名）''',
    'insert-block')

# 2) 红点找不到时优先用 accessory 锚定
rep(
    '''    if (!dot || !dot.window) { RSV622AnchoredActive = NO; return NO; }

    BOOL fromDot = YES;''',
    '''    if (!dot || !dot.window) {
        // 6.28：红点彻底找不到时，改用「录屏装饰 accessory」定位，不再退回猜侧别
        if (RSV628AccessoryAnchoredPlacement(element, allowShow)) return YES;
        RSV622AnchoredActive = NO;
        return NO;
    }

    BOOL fromDot = YES;''',
    'accessory-branch')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
