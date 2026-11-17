"""Shared helpers for the project scripts (portable Python 3, no third-party deps)."""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = os.path.join(ROOT, "rtl")
TB = os.path.join(ROOT, "tb")
SYNTH = os.path.join(ROOT, "synth")
RESULTS = os.path.join(ROOT, "results")
LOGS = os.path.join(RESULTS, "logs")
BUILD = os.path.join(ROOT, "build")

for d in (RESULTS, LOGS, BUILD):
    os.makedirs(d, exist_ok=True)


def rtl_files(rtl_dir=RTL):
    return sorted(os.path.join(rtl_dir, f) for f in os.listdir(rtl_dir) if f.endswith(".v"))


def run(cmd, log=None, cwd=ROOT, check=False):
    """Run a command, return (returncode, combined output). Optionally save the log."""
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if log:
        with open(log, "w") as f:
            f.write(p.stdout)
    if check and p.returncode != 0:
        sys.exit("command failed: %s\n%s" % (" ".join(cmd), p.stdout))
    return p.returncode, p.stdout


def iverilog_run(top_tb, params, tag, rtl_dir=RTL, extra_src=(), plusargs=()):
    """Compile tb + rtl with Icarus, run it, return (ok_compile, stdout)."""
    out = os.path.join(BUILD, "%s.vvp" % tag)
    cmd = ["iverilog", "-g2012", "-I", rtl_dir, "-o", out]
    for k, v in params.items():
        cmd.append("-P%s.%s=%s" % (os.path.splitext(os.path.basename(top_tb))[0], k, v))
    cmd += [top_tb] + list(extra_src) + rtl_files(rtl_dir)
    rc, txt = run(cmd)
    if rc != 0:
        return False, txt
    rc, txt = run(["vvp", out] + list(plusargs))
    return True, txt

# note: outputs under results/; re-run after any RTL change
