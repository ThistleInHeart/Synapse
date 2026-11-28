import os
import sys
import zipfile
import py_compile
import shutil
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_BASE = os.path.join(SCRIPT_DIR, "src")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")

# Auto-detect default Sims 4 Mods directory if present (supports redirected Documents / OneDrive / macOS)
try:
    sys.path.insert(0, os.path.join(SRC_BASE, "ai_thought_reader"))
    from ts4_paths import get_sims4_user_dir
    USER_DOCS = os.path.join(get_sims4_user_dir(), "Mods")
except Exception:
    USER_DOCS = os.path.join(os.path.expanduser("~"), "Documents", "Electronic Arts", "The Sims 4", "Mods")
SYNAPSE_MODS_DIR = os.path.join(USER_DOCS, "SynapseMod") if os.path.exists(os.path.join(USER_DOCS, "SynapseMod")) else (os.path.join(USER_DOCS, "Synapse") if os.path.exists(USER_DOCS) else None)

PACKAGES_TO_SYNC = [
    "Synapse_Interactions.package",
    "Synapse_Balloons.package",
]

MODULES_TO_BUILD = [
    {
        "name": "Synapse_SimMind",
        "sub_dir": "ai_thought_reader",
        "output_name": "Synapse_SimMind.ts4script",
    },
    {
        "name": "Synapse_SocialMessenger",
        "sub_dir": "ai_social_pc",
        "output_name": "Synapse_SocialMessenger.ts4script",
    },
    {
        "name": "Synapse_Balloons",
        "sub_dir": "balloons",
        "output_name": "Synapse_Balloons.ts4script",
    },
]


def compile_package(mod_info):
    name = mod_info["name"]
    pkg_dir = os.path.join(SRC_BASE, mod_info["sub_dir"])
    os.makedirs(BUILD_DIR, exist_ok=True)
    out_file = os.path.join(BUILD_DIR, mod_info["output_name"])

    if not os.path.exists(pkg_dir):
        print(f"[SKIP] Directory {pkg_dir} does not exist.")
        return

    print(f"\n{'=' * 50}")
    print(f"  Building {name} ({mod_info['output_name']})...")
    print(f"{'=' * 50}")

    temp_dir = tempfile.mkdtemp(prefix=f"ts4_{mod_info['sub_dir']}_")
    temp_zip = out_file + ".tmp"

    try:
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(pkg_dir):
                for file in files:
                    if file.endswith(".py"):
                        full_py = os.path.join(root, file)
                        # Relative path within src/ (e.g. ai_social_pc/main.py)
                        rel_path = os.path.relpath(full_py, SRC_BASE)
                        rel_pyc = os.path.splitext(rel_path)[0] + ".pyc"
                        temp_pyc = os.path.join(temp_dir, rel_pyc)
                        os.makedirs(os.path.dirname(temp_pyc), exist_ok=True)

                        # Compile with Python 3.7
                        py_compile.compile(full_py, cfile=temp_pyc, dfile=rel_path.replace("\\", "/"), doraise=True)
                        print(f"[COMPILED] {rel_path} -> {rel_pyc}")
                        zf.write(temp_pyc, rel_pyc)
                        if mod_info["sub_dir"] == "balloons" and file == "synapse_balloons.py":
                            zf.write(temp_pyc, "synapse_balloons.pyc")
                    elif file in ("ru_strings.json", "en_strings.json"):
                        # Game string table (STBL hash -> Russian text) used by context.py
                        data_path = os.path.join(root, file)
                        rel_data = os.path.relpath(data_path, SRC_BASE).replace("\\", "/")
                        zf.write(data_path, rel_data)
                        print(f"[DATA] {rel_data}")

        if os.path.exists(out_file):
            os.remove(out_file)
        os.rename(temp_zip, out_file)
        size = os.path.getsize(out_file)
        print(f"[SUCCESS] Built {mod_info['output_name']} ({size:,} bytes) in:\n  -> {out_file}")

        # Also copy to root of repo
        root_dest = os.path.join(SCRIPT_DIR, mod_info["output_name"])
        shutil.copy2(out_file, root_dest)

        # Deploy to game Mods folder if found
        if SYNAPSE_MODS_DIR and os.path.exists(os.path.dirname(SYNAPSE_MODS_DIR)):
            os.makedirs(SYNAPSE_MODS_DIR, exist_ok=True)
            game_dest = os.path.join(SYNAPSE_MODS_DIR, mod_info["output_name"])
            shutil.copy2(out_file, game_dest)
            print(f"[DEPLOYED] Automatically copied to game Mods:\n  -> {game_dest}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def ensure_python_37():
    if sys.version_info[:2] == (3, 7):
        return
    candidates = [
        r"C:\Users\zayar\AppData\Local\Programs\Python\Python37\python.exe",
        r"C:\Python37\python.exe",
        "python3.7",
        "py -3.7",
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            print(f"[RE-EXEC] Detected Python {sys.version.split()[0]}. Re-executing with Python 3.7:\n  -> {candidate}")
            import subprocess
            res = subprocess.run([candidate] + sys.argv)
            sys.exit(res.returncode)
    print("[WARNING] The Sims 4 strictly requires Python 3.7 bytecode. If you compile with another version, TS4 will not load the scripts.")


def sync_package():
    for pkg_name in PACKAGES_TO_SYNC:
        pkg_src = os.path.join(SCRIPT_DIR, pkg_name)
        if os.path.exists(pkg_src):
            build_pkg = os.path.join(BUILD_DIR, pkg_name)
            shutil.copy2(pkg_src, build_pkg)
            print(f"[PACKAGE] Copied {pkg_name} to build directory.")

            if SYNAPSE_MODS_DIR and os.path.exists(os.path.dirname(SYNAPSE_MODS_DIR)):
                game_pkg = os.path.join(SYNAPSE_MODS_DIR, pkg_name)
                try:
                    shutil.copy2(pkg_src, game_pkg)
                    print(f"[PACKAGE] Deployed to Sims 4 Mods:\n  -> {game_pkg}")
                except PermissionError:
                    print(f"[NOTE] {pkg_name} is locked by running The Sims 4 (package already deployed).")
                except Exception as e_pkg:
                    print(f"[WARN] Could not copy {pkg_name}: {e_pkg}")
        else:
            print(f"[WARN] Package file not found: {pkg_src}")


def build_all():
    print(f"--- SIMS 4 AI MOD BUILDER (Python {sys.version.split()[0]}) ---")
    try:
        from sync_mod_translations import sync_languages
        sync_languages()
    except Exception as e:
        print(f"[NOTE] Translation auto-sync skipped or finished: {e}")

    for mod in MODULES_TO_BUILD:
        compile_package(mod)
    try:
        from compile_balloons_package import compile_and_deploy
        compile_and_deploy()
    except Exception as e_bp:
        print(f"[NOTE] compile_balloons_package skipped: {e_bp}")
    sync_package()
    print(f"\n[DONE] All scripts successfully built into: {BUILD_DIR}\n")


if __name__ == "__main__":
    ensure_python_37()
    build_all()
