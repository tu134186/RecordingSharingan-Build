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

# 1) 新增全局：独立定时器 / 最后元素 / 启动宽限
rep(
    'static NSInteger RSProbeStatEyeHidden = 0;',
    '''static NSInteger RSProbeStatEyeHidden = 0;
static dispatch_source_t RSProbeTimer = nil;
static __weak UIView *RSProbeLastElement = nil;
static NSTimeInterval RSProbeGraceUntil = 0;''',
    'globals')

# 2) RSProbeTick 降级为「只记录元素」，判定交给定时器
rep(
    '''static void RSProbeTick(UIView *element) {
    if (!RSRecordingActive || !RSProbeFile) return;
    NSTimeInterval now = CACurrentMediaTime();
    if (now - RSProbeLastTick < 1.0) return;
    RSProbeLastTick = now;
    RSProbeSamples++;
    RSProbeStatTicks++;
    @try {
        RSProbeCloseStale();
        RSProbeAuditPrefs(RSSharinganView);
        if (element) RSProbeJudge(element);
        if (now - RSProbeLastFlush > 20.0) {
            RSProbeLastFlush = now;
            RSProbeFlush(NO);
        }
    } @catch (...) {}
}''',
    '''// 同步链路只负责告诉探针「当前绑定的元素是谁」。
// 真正的判定由独立定时器驱动 —— 即使同步链路中途失效（素材被换宿主、元素重建、
// mount 状态被清掉），探针照样每秒看一眼，把「素材不见了」记下来。
static void RSProbeTick(UIView *element) {
    if (element) RSProbeLastElement = element;
}

static void RSProbePulse(void) {
    if (!RSProbeFile) return;
    RSProbeSamples++;
    RSProbeStatTicks++;
    NSTimeInterval mono = CACurrentMediaTime();
    @try {
        RSProbeCloseStale();
        RSProbeAuditPrefs(RSSharinganView);
        RSProbeJudge(nil);
        if (mono - RSProbeLastFlush > 20.0) {
            RSProbeLastFlush = mono;
            RSProbeFlush(NO);
        }
    } @catch (...) {}
}

static void RSProbeStartTimer(void) {
    if (RSProbeTimer) return;
    RSProbeTimer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0,
                                          dispatch_get_main_queue());
    if (!RSProbeTimer) return;
    dispatch_source_set_timer(RSProbeTimer,
                              dispatch_time(DISPATCH_TIME_NOW, (int64_t)NSEC_PER_SEC),
                              (uint64_t)NSEC_PER_SEC,
                              (uint64_t)(100 * NSEC_PER_MSEC));
    dispatch_source_set_event_handler(RSProbeTimer, ^{ RSProbePulse(); });
    dispatch_resume(RSProbeTimer);
}

static void RSProbeStopTimer(void) {
    if (!RSProbeTimer) return;
    dispatch_source_cancel(RSProbeTimer);
    RSProbeTimer = nil;
}''',
    'tick-to-pulse')

# 3) Judge 开头：支持 element 为 nil + 素材缺失即报错 + 启动宽限
rep(
    '''static void RSProbeJudge(UIView *element) {
    UIImageView *eye = RSSharinganView;
    if (!element || !eye) { RSProbeStatNoEye++; return; }

    UIView *dot = RSV622BestDotForElement(element);''',
    '''static void RSProbeJudge(UIView *element) {
    UIImageView *eye = RSSharinganView;
    UIView *el = element ?: RSProbeLastElement;
    NSTimeInterval wallNow = [[NSDate date] timeIntervalSince1970];

    // 录屏刚启动的头几秒素材还在创建，属于正常，不判
    if (wallNow < RSProbeGraceUntil) return;

    // 录屏开着，素材必须存在。不存在就是「没挂上去」——这是用户最常遇到的故障。
    if (!eye) {
        RSProbeStatNoEye++;
        RSProbeAppend(RSProbeKindMissing, @"素材没挂上去",
                      @"录屏已经开着，但素材对象根本不存在——这段时间岛上只剩系统红点",
                      RSProbeContext(el, nil, nil));
        return;
    }

    UIView *dot = RSV622BestDotForElement(el);''',
    'judge-head2')

# 4) Begin 启动定时器 + 宽限
rep(
    '''    RSProbeFile = [NSString stringWithFormat:@"/var/mobile/RS-report-%@.txt", RSProbeStamp()];
    RSLog(@"[V6.23] probe begin %@", RSProbeFile);''',
    '''    RSProbeFile = [NSString stringWithFormat:@"/var/mobile/RS-report-%@.txt", RSProbeStamp()];
    RSProbeGraceUntil = RSProbeStartWall + 4.0;
    RSProbeLastElement = nil;
    RSProbeStartTimer();
    RSLog(@"[V6.24] probe begin %@", RSProbeFile);''',
    'begin-timer')

# 5) Finish 停止定时器
rep(
    '''static void RSProbeFinish(void) {
    if (!RSProbeFile) return;
    RSProbeStopWall = [[NSDate date] timeIntervalSince1970];''',
    '''static void RSProbeFinish(void) {
    if (!RSProbeFile) return;
    RSProbeStopTimer();
    RSProbeStopWall = [[NSDate date] timeIntervalSince1970];''',
    'finish-timer')

# 6) 报告里说明探针是独立驱动的
rep(
    '[out appendFormat:@"一共检查了 %ld 次（每秒一次）\\n\\n", (long)RSProbeSamples];',
    '[out appendFormat:@"一共检查了 %ld 次（独立定时器，每秒一次）\\n\\n", (long)RSProbeSamples];',
    'render-note')

open(p, 'w', encoding='utf-8').write(s)
print('OK')
