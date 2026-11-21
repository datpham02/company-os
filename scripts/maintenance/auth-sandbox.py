"""Isolated Paperclip instances for the authentication-migration tests (A.5 WS-1, WS-2, WS-5).

    python -I scripts/maintenance/auth-sandbox.py init  <name> --port 3300 --pg-port 54349
    python -I scripts/maintenance/auth-sandbox.py start <name>
    python -I scripts/maintenance/auth-sandbox.py stop  <name>          # node tree, then pg_ctl stop -m fast
    python -I scripts/maintenance/auth-sandbox.py clone <name> <new> --port 3301 --pg-port 54350
                                                                        # WS-1 candidate B: cold copy, stopped only
    python -I scripts/maintenance/auth-sandbox.py mode  <name> local_trusted|authenticated   # stopped only
    python -I scripts/maintenance/auth-sandbox.py teardown <name>       # stop, then delete the folder

Boundaries (step2-board-decisions.md §3 and §3.1; auth-migration-verification-plan.md §2), enforced here:
- every instance lives under %USERPROFILE%\\.company-os-sandbox\\<name> (the profile is private; R8 avoided);
- the live ports 3100 and 54329 are never used, and `start` refuses while either is listening (live stopped);
- fresh secrets per instance (agent JWT secret, tool-action signing secret; Paperclip makes the master key);
- telemetry, update checks and automatic backups off; no GH_TOKEN, no production secret, no agents;
- the live instance folder (~/.paperclip) is never read or written.
Stdlib only. Nothing here prints a secret.
"""
import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.join(os.path.expanduser("~"), ".company-os-sandbox")
LIVE_PORTS = (3100, 54329)
LIVE_HOME = os.path.join(os.path.expanduser("~"), ".paperclip")


class Stop(Exception):
    pass


def home(name):
    if not name.replace("-", "").isalnum():
        raise Stop(f"bad sandbox name {name!r}")
    return os.path.join(ROOT, name)


def inst_dir(name):
    return os.path.join(home(name), "instances", name)


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def config(name):
    with open(os.path.join(inst_dir(name), "config.json"), encoding="utf-8") as f:
        return json.load(f)


def write_config(name, conf):
    with open(os.path.join(inst_dir(name), "config.json"), "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)


def pg_bin(tool):
    npm_root = subprocess.run(["cmd", "/c", "npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    path = os.path.join(npm_root, "paperclipai", "node_modules", "@embedded-postgres", "windows-x64", "native",
                        "bin", tool + ".exe")
    if not os.path.isfile(path):
        raise Stop(f"{tool} not found at {path}")
    return path


def check_ports(port, pg_port):
    for p in (port, pg_port):
        if p in LIVE_PORTS:
            raise Stop(f"port {p} belongs to the live instance")


def cmd_init(a):
    check_ports(a.port, a.pg_port)
    d = inst_dir(a.name)
    if os.path.exists(home(a.name)):
        raise Stop(f"{home(a.name)} already exists")
    os.makedirs(os.path.join(d, "secrets"))
    conf = {
        "$meta": {"version": 1, "source": "company-os auth-sandbox"},
        "database": {"mode": "embedded-postgres", "embeddedPostgresDataDir": os.path.join(d, "db"),
                     "embeddedPostgresPort": a.pg_port,
                     "backup": {"enabled": False, "intervalMinutes": 60, "retentionDays": 30,
                                "dir": os.path.join(d, "data", "backups")}},
        "logging": {"mode": "file", "logDir": os.path.join(d, "logs")},
        "server": {"deploymentMode": "local_trusted", "exposure": "private", "bind": "loopback",
                   "host": "127.0.0.1", "port": a.port, "allowedHostnames": [], "serveUi": True},
        "telemetry": {"enabled": False},
        "updates": {"checkEnabled": False},
        "auth": {"baseUrlMode": "auto", "disableSignUp": False},
        "storage": {"provider": "local_disk", "localDisk": {"baseDir": os.path.join(d, "data", "storage")},
                    "s3": {"bucket": "paperclip", "region": "us-east-1", "prefix": "", "forcePathStyle": False}},
        "secrets": {"provider": "local_encrypted", "strictMode": False,
                    "localEncrypted": {"keyFilePath": os.path.join(d, "secrets", "master.key")}},
    }
    write_config(a.name, conf)
    with open(os.path.join(d, ".env"), "w", encoding="utf-8") as f:
        f.write("# company-os auth-sandbox: fresh values, never production\n"
                f"PAPERCLIP_AGENT_JWT_SECRET={secrets.token_hex(32)}\n"
                f"PAPERCLIP_TOOL_ACTION_SIGNING_SECRET={secrets.token_hex(32)}\n")
    print(f"initialised {a.name}: port {a.port}, Postgres {a.pg_port}, local_trusted, in {home(a.name)}")


def env_for(name):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PAPERCLIP_") and k != "GH_TOKEN"}
    env.update(PAPERCLIP_HOME=home(name), PAPERCLIP_INSTANCE_ID=name,
               PAPERCLIP_AUTH_STORE=os.path.join(home(name), "cli-auth.json"))
    return env


def health(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as r:
        return json.loads(r.read())


def cmd_start(a):
    conf = config(a.name)
    port, pg = conf["server"]["port"], conf["database"]["embeddedPostgresPort"]
    check_ports(port, pg)
    for p in LIVE_PORTS:
        if listening(p):
            raise Stop(f"port {p} is listening: stop the live Paperclip first (step2 §3.1)")
    for p in (port, pg):
        if listening(p):
            raise Stop(f"port {p} is already in use")
    log = open(os.path.join(home(a.name), "console.log"), "ab")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen(["cmd", "/c", "paperclipai", "run", "--data-dir", home(a.name), "--instance", a.name,
                      "--no-repair"], env=env_for(a.name), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                     cwd=home(a.name), creationflags=flags)
    end = time.time() + 240
    while time.time() < end:
        try:
            h = health(port)
            if h.get("status") == "ok":
                for p in LIVE_PORTS:
                    if listening(p):
                        raise Stop(f"live port {p} opened while the sandbox started; stopping")
                print(f"{a.name} up on {port}: {h.get('deploymentMode')}, version {h.get('version')}")
                return
        except OSError:
            pass
        time.sleep(2)
    raise Stop(f"{a.name} did not answer on {port} within 4 minutes; see {home(a.name)}\\console.log")


def procs_of(name):
    """PIDs of processes whose command line names this sandbox home."""
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*" + home(name).replace("'", "''")
          + "*' } | ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    me = os.getpid()
    return [int(x) for x in out.split() if x.strip().isdigit() and int(x) != me]


def cmd_stop(a):
    for pid in procs_of(a.name):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    db = config(a.name)["database"]["embeddedPostgresDataDir"]
    if os.path.exists(os.path.join(db, "postmaster.pid")):
        subprocess.run([pg_bin("pg_ctl"), "stop", "-D", db, "-m", "fast", "-w"], capture_output=True)
    time.sleep(1)
    conf = config(a.name)
    busy = [p for p in (conf["server"]["port"], conf["database"]["embeddedPostgresPort"]) if listening(p)]
    if busy or os.path.exists(os.path.join(db, "postmaster.pid")):
        raise Stop(f"{a.name} not fully stopped (listening: {busy})")
    print(f"{a.name} stopped")


def cmd_clone(a):
    """WS-1 candidate B: cold copy of a stopped instance folder into a new sandbox, paths and ports rewritten."""
    check_ports(a.port, a.pg_port)
    src, dst = home(a.name), home(a.new)
    conf = config(a.name)
    if listening(conf["server"]["port"]) or os.path.exists(
            os.path.join(conf["database"]["embeddedPostgresDataDir"], "postmaster.pid")):
        raise Stop(f"{a.name} is running; a cold copy needs it stopped")
    if os.path.exists(dst):
        raise Stop(f"{dst} already exists")
    shutil.copytree(src, dst)
    os.rename(os.path.join(dst, "instances", a.name), inst_dir(a.new))
    text = json.dumps(conf).replace(json.dumps(inst_dir(a.name))[1:-1], json.dumps(inst_dir(a.new))[1:-1])
    new = json.loads(text)
    new["server"]["port"], new["database"]["embeddedPostgresPort"] = a.port, a.pg_port
    write_config(a.new, new)
    for f in ("console.log", "cli-auth.json"):
        p = os.path.join(dst, f)
        if os.path.exists(p):
            os.remove(p)
    print(f"cold copy {a.name} -> {a.new}: port {a.port}, Postgres {a.pg_port}")


def cmd_mode(a):
    conf = config(a.name)
    if listening(conf["server"]["port"]):
        raise Stop(f"{a.name} is running; stop it before changing the mode")
    conf["server"]["deploymentMode"] = a.mode
    write_config(a.name, conf)
    print(f"{a.name}: deploymentMode {a.mode} (takes effect on the next start)")


def cmd_teardown(a):
    if os.path.exists(home(a.name)):
        try:
            cmd_stop(a)
        except (Stop, OSError, KeyError) as e:
            print(f"stop: {e}")
        shutil.rmtree(home(a.name))
    print(f"{a.name} removed")


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("name")
    s.add_argument("--port", type=int, required=True)
    s.add_argument("--pg-port", type=int, required=True)
    for c in ("start", "stop", "teardown"):
        sub.add_parser(c).add_argument("name")
    s = sub.add_parser("clone")
    s.add_argument("name")
    s.add_argument("new")
    s.add_argument("--port", type=int, required=True)
    s.add_argument("--pg-port", type=int, required=True)
    s = sub.add_parser("mode")
    s.add_argument("name")
    s.add_argument("mode", choices=("local_trusted", "authenticated"))
    a = p.parse_args(argv)
    if os.path.abspath(ROOT).startswith(os.path.abspath(LIVE_HOME)):
        raise Stop("sandbox root inside the live Paperclip home")
    try:
        {"init": cmd_init, "start": cmd_start, "stop": cmd_stop, "clone": cmd_clone, "mode": cmd_mode,
         "teardown": cmd_teardown}[a.cmd](a)
        return 0
    except Stop as e:
        print(f"STOP: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
