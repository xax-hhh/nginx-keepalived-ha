#!/usr/bin/env python3
"""
Linux 运维实训项目 — 极限压力测试
用法:
  python stress_test.py                  # 默认攀升模式: 10→20→50→100→200 并发
  python stress_test.py --mode crawl       # 攀升模式, 找到崩溃临界点
  python stress_test.py -c 50 -n 500      # 固定压力模式
  python stress_test.py --mode internal    # 内网模式(从 app-1 跑, 直连所有服务器)
"""

import requests
import time
import json
import threading
import argparse
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutTimeout
from collections import defaultdict

# ── 服务器地址 ──────────────────────────────────────
VIP       = os.environ.get("VIP",       "192.168.1.200")
NGINX1    = os.environ.get("NGINX1",    "192.168.10.120")
NGINX2    = os.environ.get("NGINX2",    "192.168.10.123")
APP1      = os.environ.get("APP1",      "192.168.10.121")
APP2      = os.environ.get("APP2",      "192.168.10.124")
PROXY     = os.environ.get("PROXY",     "192.168.10.126")
PROXY_PORT = 3307
API_PORT  = 8080

# ── 颜色 ────────────────────────────────────────────
class C:
    G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
    B = "\033[96m"; W = "\033[1m"; E = "\033[0m"

def ok(m):    print(f"  {C.G}✅ {m}{C.E}")
def fail(m):  print(f"  {C.R}❌ {m}{C.E}")
def warn(m):  print(f"  {C.Y}⚠️  {m}{C.E}")
def info(m):  print(f"  {C.B}→ {m}{C.E}")
def header(t): print(f"\n{'═'*60}\n  {C.W}{t}{C.E}\n{'═'*60}")

# ── 工具 ────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.ok = 0; self.fail = 0
        self.times = []; self.errors = defaultdict(int)
        self.servers = defaultdict(int)
        self.first_error_time = None
        self.start_time = time.time()

    def add_ok(self, elapsed, server=""):
        with self.lock:
            self.ok += 1
            self.times.append(elapsed)
            if server: self.servers[server] += 1

    def add_fail(self, err=""):
        with self.lock:
            self.fail += 1
            if err: self.errors[err[:60]] += 1
            if self.first_error_time is None:
                self.first_error_time = time.time() - self.start_time

    def summary(self):
        total = self.ok + self.fail
        if total == 0: return
        self.times.sort()
        t = self.times
        avg = sum(t) / len(t) if t else 0
        p50 = t[len(t)//2] if t else 0
        p95 = t[int(len(t)*0.95)] if len(t) >= 20 else (t[-1] if t else 0)
        p99 = t[int(len(t)*0.99)] if len(t) >= 100 else (t[-1] if t else 0)
        success_rate = self.ok / total * 100
        duration = time.time() - self.start_time
        qps = self.ok / duration if duration > 0 else 0

        status = f"{C.G}" if success_rate >= 99 else f"{C.Y}" if success_rate >= 90 else f"{C.R}"
        print(f"\n  {C.W}━━━ 结果 ━━━{C.E}")
        print(f"  成功率: {status}{success_rate:.1f}%{C.E}  ({self.ok}/{total})")
        print(f"  耗时:   {duration:.1f}s  |  QPS: {qps:.0f}")
        if t:
            print(f"  延迟:   平均 {avg*1000:.0f}ms  P50={p50*1000:.0f}ms  P95={p95*1000:.0f}ms  P99={p99*1000:.0f}ms")
        if self.servers:
            print(f"  分发:   {dict(self.servers)}")
        if self.errors:
            for e, c in sorted(self.errors.items(), key=lambda x: -x[1])[:3]:
                warn(f"  高频错误 ×{c}: {e}")
        if self.first_error_time:
            info(f"  首次失败出现在 {self.first_error_time:.1f}s")

        return success_rate, qps

# ── HTTP 请求 ────────────────────────────────────────
SESSION = None  # 每个线程独立 session

def get_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

def do_post(url, json_data, timeout=15):
    s = get_session()
    start = time.time()
    try:
        r = s.post(url, json=json_data, timeout=timeout)
        return time.time() - start, r
    except Exception as e:
        return time.time() - start, None

def do_get(url, timeout=10):
    s = get_session()
    start = time.time()
    try:
        r = s.get(url, timeout=timeout)
        return time.time() - start, r
    except Exception as e:
        return time.time() - start, None

# ── 健康检查 ────────────────────────────────────────
def health_check(mode="vip"):
    header("全链路健康检查")

    if mode == "internal":
        targets = [
            ("App-1",    f"http://{APP1}:{API_PORT}/actuator/health"),
            ("App-2",    f"http://{APP2}:{API_PORT}/actuator/health"),
            ("Nginx-1",  f"http://{NGINX1}/nginx-health"),
            ("Nginx-2",  f"http://{NGINX2}/nginx-health"),
            ("Proxy",    f"http://{APP1}:{API_PORT}/actuator/health"),  # 间接: 登录取 token 验证 DB 通
        ]
    else:
        targets = [
            ("Nginx-1",  f"http://{NGINX1}/nginx-health"),
            ("Nginx-2",  f"http://{NGINX2}/nginx-health"),
            ("VIP",      f"http://{VIP}/nginx-health"),
        ]

    all_ok = True
    for name, url in targets:
        elapsed, r = do_get(url, timeout=5)
        if r and r.status_code == 200:
            ok(f"{name:<10} → {r.elapsed.total_seconds()*1000:.0f}ms  {r.text.strip()[:50]}")
        elif r:
            fail(f"{name:<10} → HTTP {r.status_code}")
            all_ok = False
        else:
            fail(f"{name:<10} → 不通 ({elapsed*1000:.0f}ms)")
            all_ok = False

    # 验证数据库连通性（通过登录 API）
    base = f"http://{VIP}" if mode == "vip" else f"http://{APP1}:{API_PORT}"
    elapsed, r = do_post(f"{base}/api/auth/login",
                         {"username": "admin", "password": "123456"})
    if r and r.status_code == 200 and "token" in r.json():
        ok(f"DB(login)   → {elapsed*1000:.0f}ms  token OK")
    else:
        fail(f"DB(login)   → 失败")
        all_ok = False

    return all_ok

# ── 并发任务：登录 ──────────────────────────────────
def login_worker(base_url, username, password, stats):
    elapsed, r = do_post(f"{base_url}/api/auth/login",
                         {"username": username, "password": password})
    if r and r.status_code == 200 and "token" in r.json():
        server = r.headers.get("X-Java-Server", "?")
        stats.add_ok(elapsed, server)
    else:
        err = r.json().get("error", f"HTTP {r.status_code}") if r else "timeout"
        stats.add_fail(err)

# ── 并发任务：注册 ──────────────────────────────────
def register_worker(base_url, worker_id, stats):
    ts = int(time.time() * 1000000)
    username = f"load_{ts}_{worker_id}"
    elapsed, r = do_post(f"{base_url}/api/auth/register",
                         {"username": username, "password": "test123", "email": f"{username}@t.local"})
    if r and r.status_code in (200, 201):
        stats.add_ok(elapsed)
    else:
        err = r.json().get("error", f"HTTP {r.status_code}") if r else "timeout"
        stats.add_fail(err)

# ── 并发任务：混合读写（注册+登录） ──────────────────
def mixed_worker(base_url, worker_id, stats):
    """一半注册(写)，一半登录(读)，模拟真实负载"""
    if worker_id % 2 == 0:
        register_worker(base_url, worker_id, stats)
    else:
        login_worker(base_url, "admin", "123456", stats)

# ── 执行一轮 ────────────────────────────────────────
def run_round(base_url, count, concurrency, task_type="mixed", description=""):
    """执行一轮并发请求，返回 Stats"""
    info(f"{description}: {count} 请求, {concurrency} 并发")

    # 准备登录凭据
    workers = []
    stats = Stats()

    if task_type == "login":
        fn = lambda i: login_worker(base_url, "admin", "123456", stats)
    elif task_type == "register":
        fn = lambda i: register_worker(base_url, i, stats)
    else:  # mixed
        fn = lambda i: mixed_worker(base_url, i, stats)

    start = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(fn, i) for i in range(count)]
        for f in as_completed(futures):
            try:
                f.result(timeout=20)
            except FutTimeout:
                stats.add_fail("worker_timeout")
            except Exception as e:
                stats.add_fail(str(e)[:60])

    stats.start_time = start
    return stats

# ── 攀升模式：自动找极限 ─────────────────────────────
def crawl_mode(base_url, start=10, max_concurrency=300):
    """从低并发开始, 逐步翻倍, 直到成功率 < 95% 或达到上限"""
    header(f"攀升模式: 自动找极限 (起始 {start} 并发)")

    concurrency = start
    prev_stats = None
    breaking_point = None

    results = []

    while concurrency <= max_concurrency:
        count = concurrency * 5  # 每个并发级别发 5 倍请求
        stats = run_round(base_url, count, concurrency,
                         task_type="mixed",
                         description=f"并发 {concurrency}")

        rate, qps = stats.summary()

        results.append((concurrency, rate, qps, stats))

        # 判定是否崩溃
        if rate < 95:
            breaking_point = concurrency
            fail(f"\n  ⚡ 达到瓶颈! 并发 {concurrency} 时成功率降至 {rate:.1f}%")
            break
        elif rate < 99:
            warn(f"  ⚠️  成功率略低于 99%, 接近极限")

        concurrency *= 2  # 翻倍
        time.sleep(2)  # 间隔让服务器喘息

    # ── 最终报告 ──
    header("攀升测试报告")
    print(f"{'并发':>6}  {'请求数':>6}  {'成功率':>8}  {'QPS':>6}  {'平均延迟':>10}  {'P99':>8}")
    print(f"{'─'*6}  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*10}  {'─'*8}")
    for c, rate, qps, s in results:
        t = s.times
        avg = sum(t)/len(t)*1000 if t else 0
        p99 = t[int(len(t)*0.99)]*1000 if len(t) >= 100 else (t[-1]*1000 if t else 0)
        mark = " ⚡" if rate < 95 else " ⚠" if rate < 99 else ""
        print(f"{c:>6}  {c*5:>6}  {rate:>7.1f}%  {qps:>6.0f}  {avg:>8.0f}ms  {p99:>6.0f}ms{mark}")

    if breaking_point:
        print(f"\n  {C.R}极限并发 ≈ {breaking_point}{C.E}")
        print(f"  建议生产限流设置在 {max(10, breaking_point // 2)} 并发以内")
    else:
        ok(f"未找到崩溃点! 并发 {max_concurrency} 依然稳定, 可尝试更高值")

    return breaking_point

# ── 极限模式：同时打满双 App + VIP ──────────────────────
def brutal_mode(concurrency=150, count=500):
    """并行攻击: App-1 + App-2 + VIP, 三路同时发飙"""
    import multiprocessing as mp

    header(f"极限模式: 双 App({concurrency}并发) + VIP({concurrency}并发) 同时发飙")

    def attack_app1():
        base = f"http://{APP1}:{API_PORT}"
        stats = run_round(base, count, concurrency, task_type="mixed",
                         description="App-1 直连")
        return ("App-1", stats)

    def attack_app2():
        base = f"http://{APP2}:{API_PORT}"
        stats = run_round(base, count, concurrency, task_type="mixed",
                         description="App-2 直连")
        return ("App-2", stats)

    def attack_vip():
        # 先检测 VIP 是否可达
        try:
            r = requests.get(f"http://{VIP}/nginx-health", timeout=3)
            if r.status_code != 200:
                return ("VIP", None)
        except:
            warn("VIP 不可达(不在同一子网)，跳过 VIP 攻击")
            return ("VIP", None)
        base = f"http://{VIP}"
        stats = run_round(base, count*2, concurrency, task_type="mixed",
                         description="VIP 外部")
        return ("VIP", stats)

    start = time.time()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(attack_app1),
            pool.submit(attack_app2),
            pool.submit(attack_vip),
        ]
        raw = [f.result() for f in as_completed(futures)]
        results = [(n, s) for n, s in raw if s is not None]

    duration = time.time() - start

    header("极限模式结果")
    total_ok = 0; total_fail = 0; total_qps = 0
    for name, stats in results:
        r, q = stats.summary()
        total_ok += stats.ok
        total_fail += stats.fail
        total_qps += q
        print()

    total = total_ok + total_fail
    print(f"  {C.W}━━━ 总计 ━━━{C.E}")
    print(f"  总请求: {total}  成功: {total_ok}  失败: {total_fail}")
    print(f"  成功率: {total_ok/total*100:.1f}%" if total > 0 else "  无数据")
    print(f"  总耗时: {duration:.1f}s  总 QPS: {total_qps:.0f}")
    print(f"  等效并发: {total_qps:.0f} QPS × 3 路")

# ── 直连 App 负载分发测试 ────────────────────────────
def direct_app_test():
    """直接打两台 App, 看负载是否均衡"""
    header("直连 App 负载分发测试 (需从内网机器运行)")

    for app_name, app_ip in [("App-1", APP1), ("App-2", APP2)]:
        base = f"http://{app_ip}:{API_PORT}"
        stats = run_round(base, 100, 20, task_type="login",
                         description=f"直连 {app_name}")
        stats.summary()
        time.sleep(1)

# ── 全链路极限测试 ──────────────────────────────────
def full_stress(base_url, rounds=3, count=100, concurrency=30, task_type="mixed"):
    """多轮固定压力测试"""
    header(f"全链路极限测试 ({rounds}轮×{count}次, {concurrency}并发, {task_type})")

    all_stats = Stats()

    for rnd in range(rounds):
        stats = run_round(base_url, count, concurrency, task_type,
                         description=f"第 {rnd+1}/{rounds} 轮")
        all_stats.ok += stats.ok
        all_stats.fail += stats.fail
        all_stats.times.extend(stats.times)
        for k, v in stats.servers.items():
            all_stats.servers[k] += v
        for k, v in stats.errors.items():
            all_stats.errors[k] += v
        time.sleep(1)

    all_stats.start_time = stats.start_time  # 用最后一轮的开始时间
    return all_stats

# ── 主入口 ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Linux 运维实训 — 极限压力测试")
    parser.add_argument("-c", "--concurrency", type=int, default=50, help="并发数")
    parser.add_argument("-n", "--count", type=int, default=200, help="每轮请求数")
    parser.add_argument("-r", "--rounds", type=int, default=3, help="轮数")
    parser.add_argument("--mode", choices=["vip", "internal", "crawl"], default="crawl",
                       help="vip=从外部打VIP | internal=内网直连 | crawl=攀升找极限")
    parser.add_argument("--task", choices=["login", "register", "mixed"], default="mixed",
                       help="任务类型: login(只读) | register(只写) | mixed(混合)")
    parser.add_argument("--crawl-start", type=int, default=10, help="攀升起始并发 (默认 10)")
    parser.add_argument("--crawl-max", type=int, default=300, help="攀升最大并发 (默认 300)")
    parser.add_argument("--brutal", action="store_true", help="极限模式: 同时打满双 App + VIP")
    args = parser.parse_args()

    print(f"{C.W}{'▇'*60}{C.E}")
    print(f"{C.W}  Linux 运维实训 — 极限压力测试{C.E}")
    mode_desc = {"vip": f"外部 VIP: {VIP}", "internal": "内网直连", "crawl": "攀升模式"}
    print(f"  模式: {mode_desc[args.mode]}")
    print(f"{C.W}{'▇'*60}{C.E}")

    base_url = f"http://{VIP}"

    if args.mode in ("internal", "crawl"):
        base_url = f"http://{APP1}:{API_PORT}"  # 内网直连 app-1

    # ── 健康检查 ──
    if not health_check(args.mode):
        warn("部分健康检查未通过, 继续测试...")

    # ── CRUD 冒烟 ──
    header("冒烟测试")
    elapsed, r = do_post(f"{base_url}/api/auth/register",
                         {"username": f"smoke_{int(time.time())}", "password": "test",
                          "email": f"smoke_{int(time.time())}@t.local"})
    if r and r.status_code in (200, 201):
        ok(f"注册 OK ({elapsed*1000:.0f}ms)")
    else:
        fail("注册失败 — 服务可能有异常")

    elapsed, r = do_post(f"{base_url}/api/auth/login",
                         {"username": "admin", "password": "123456"})
    if r and r.status_code == 200 and "token" in r.json():
        ok(f"登录 OK ({elapsed*1000:.0f}ms)  server={r.headers.get('X-Java-Server','?')}")
    else:
        fail("登录失败 — 紧急! 检查 Proxy 和 MySQL")

    # ── 主测试 ──
    if args.brutal:
        brutal_mode(args.concurrency, args.count)
        return

    if args.mode == "crawl":
        crawl_mode(base_url, start=args.crawl_start, max_concurrency=args.crawl_max)
    elif args.mode == "internal":
        # 内网模式: 分别直连两台 App
        header("内网直连双 App 测试")
        for app_name, app_ip in [("App-1", APP1), ("App-2", APP2)]:
            base = f"http://{app_ip}:{API_PORT}"
            info(f"目标: {app_name} ({base})")
            stats = run_round(base, args.count, args.concurrency,
                            task_type=args.task,
                            description=f"直连 {app_name}")
            stats.summary()
            time.sleep(2)

        # 同时测试 Proxy
        header("Proxy 连通性测试")
        elapsed, r = do_post(f"http://{APP1}:{API_PORT}/api/auth/login",
                            {"username": "admin", "password": "123456"})
        if r and "token" in r.json():
            ok(f"Proxy(通过App) OK ({elapsed*1000:.0f}ms)")
    else:
        stats = full_stress(base_url, args.rounds, args.count, args.concurrency, args.task)
        stats.summary()

    print(f"\n{C.W}{'▇'*60}{C.E}")
    print(f"{C.W}  测试完成{C.E}")
    print(f"{C.W}{'▇'*60}{C.E}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
