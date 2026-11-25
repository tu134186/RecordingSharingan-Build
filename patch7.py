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

# 1) 删掉「沿用当前父视图」的兜底（它把素材塞回 26×22 的窄容器）
rep(
    '''    if (!host || !host.window) {
        UIView *curHost = RSSharinganView.superview;
        if (curHost && (RSV622ClassHas(curHost, @"ApertureContainer") ||
                        RSV622ClassHas(curHost, @"ProvidedView"))) {
            host = curHost;
            fromDot = NO;
        }
    }
    if (!host || !host.window) {''',
    '''    if (!host || !host.window) {''',
    'drop-curhost')

# 2) accessory 锚定提到最前面
rep(
    '''static BOOL RSV622DotAnchoredPlacement(UIView *element, BOOL allowShow) {
    UIImageView *eye = RSSharinganView;
    if (!eye || !element || !element.window) return NO;
    UIView *dot = RSV622FastDot(element);''',
    '''static BOOL RSV622DotAnchoredPlacement(UIView *element, BOOL allowShow) {
    UIImageView *eye = RSSharinganView;
    if (!eye || !element || !element.window) return NO;

    // 6.29：accessory 锚定优先。
    // 这台系统的红点类名不含 RecordingIndicator，类名扫描会把 App 图标角标
    // （SBDarkeningImageView / SBIconBadgeView）当成红点，全程都是错的。
    // 而「录屏装饰 accessory」的结构位置是稳定的（始终在岛最左端、宽 17~26pt），
    // 所以直接走这条不依赖红点的路。
    if (RSV628AccessoryAnchoredPlacement(element, allowShow)) return YES;

    UIView *dot = RSV622FastDot(element);''',
    'accessory-first')

# 3) accessory 锚定时把里面露出来的原生红点压掉
rep(
    '''    BOOL visible = allowShow && !RSEyeGracePaused && !RSEyeResumeVisibilityPending;
    if (visible) { eye.hidden = NO; eye.alpha = 1.0; }
    RSV622AnchoredActive = YES;''',
    '''    BOOL visible = allowShow && !RSEyeGracePaused && !RSEyeResumeVisibilityPending;
    if (visible) { eye.hidden = NO; eye.alpha = 1.0; }

    // 素材盖住之后，把 accessory 里仍然露在外面的原生红点压成透明
    NSArray<UIView *> *leaves = RSV622RedLeafDots(acc);
    for (UIView *leaf in leaves) {
        NSNumber *old = objc_getAssociatedObject(leaf, RSOriginalAlphaKey);
        if (visible) {
            if (!old) objc_setAssociatedObject(leaf, RSOriginalAlphaKey, @(leaf.alpha),
                                               OBJC_ASSOCIATION_RETAIN_NONATOMIC);
            leaf.alpha = 0.0;
            RSV622TrackDot(leaf);
        } else if (old) {
            leaf.alpha = old.doubleValue;
            objc_setAssociatedObject(leaf, RSOriginalAlphaKey, nil, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
        }
    }

    RSV622AnchoredActive = YES;''',
    'hide-native')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
