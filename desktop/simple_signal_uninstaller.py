import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


APP_NAME = "Simple Signal Desktop"
UNINSTALLER_NAMES = (
    "Uninstall Simple-Signal-Desktop.exe",
    "Uninstall Simple Signal Desktop.exe",
    "Uninstall SimpleSignal.exe",
    "Uninstall.exe",
)


def is_frozen():
    return getattr(sys, "frozen", False)


def exe_dir():
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def possible_backend_dirs():
    base = exe_dir()
    candidates = [
        Path(os.environ.get("SIMPLE_SIGNAL_BACKEND_DIR", "")),
        base / "resources" / "app-backend",
        base / "app-backend",
        base.parent,
        base.parent / "resources" / "app-backend",
        Path.home() / "simple-signal-cli",
        Path("C:/Users/Falab/simple-signal-cli"),
    ]

    seen = set()
    valid = []
    for candidate in candidates:
        if not str(candidate):
            continue
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "web_server.py").exists() or (resolved / "extensions").exists():
            valid.append(resolved)
    return valid


def default_backend_dir():
    dirs = possible_backend_dirs()
    return dirs[0] if dirs else None


def default_extensions_dir():
    configured = os.environ.get("SIMPLE_SIGNAL_EXTENSIONS_DIR")
    if configured:
        path = Path(configured).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            path = Path(local_app_data) / "SimpleSignal" / "extensions"
        else:
            path = Path.home() / ".simple-signal" / "extensions"

    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def extension_display_name(path):
    manifest_path = path / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name") or path.name
            return f"{name} ({path.name})"
        except Exception:
            pass
    return path.name


def list_extensions(extensions_dir):
    if not extensions_dir.exists():
        return []
    items = []
    for child in sorted(extensions_dir.iterdir(), key=lambda p: p.name.lower()):
        if child.is_dir():
            items.append((extension_display_name(child), child.name, child))
    return items


def safe_remove_dir(path, expected_parent):
    target = path.resolve()
    parent = expected_parent.resolve()
    if target.parent != parent:
        raise ValueError(f"Refusing to remove unexpected path: {target}")
    if target.exists():
        shutil.rmtree(target)


def find_system_uninstaller():
    base = exe_dir()
    candidates = []

    for name in UNINSTALLER_NAMES:
        candidates.append(base / name)
        candidates.append(base.parent / name)

    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    for root in (local_app_data, program_files, program_files_x86):
        if root:
            for app_dir_name in ("Simple-Signal-Desktop", "Simple Signal Desktop", "SimpleSignal"):
                app_dir = Path(root) / app_dir_name
                for name in UNINSTALLER_NAMES:
                    candidates.append(app_dir / name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


class SimpleSignalUninstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple Signal Uninstaller")
        self.geometry("560x360")
        self.minsize(520, 340)
        self.configure(bg="#111318")

        self.backend_dir = default_backend_dir()
        self.extensions_dir = default_extensions_dir()
        self.extensions = []
        self.extension_by_label = {}

        self.action_var = tk.StringVar(value="Uninstall selected extension only")
        self.extension_var = tk.StringVar()
        self.backend_var = tk.StringVar(value=str(self.extensions_dir))
        self.status_var = tk.StringVar(value="")

        self.build_ui()
        self.refresh_extensions()

    def build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#111318")
        style.configure("TLabel", background="#111318", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background="#111318", foreground="#a1a1aa", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TCombobox", fieldbackground="#1f2430", background="#1f2430", foreground="#111318")

        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(root, text="Simple Signal Uninstaller", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        hint = ttk.Label(
            root,
            text="Choose whether to remove an extension while keeping Simple Signal, remove all extensions, or launch the full app uninstaller.",
            style="Hint.TLabel",
            wraplength=510,
        )
        hint.pack(anchor="w", pady=(6, 18))

        ttk.Label(root, text="Simple Signal extensions folder").pack(anchor="w")
        backend_row = ttk.Frame(root)
        backend_row.pack(fill=tk.X, pady=(4, 14))
        self.backend_entry = ttk.Entry(backend_row, textvariable=self.backend_var)
        self.backend_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(backend_row, text="Refresh", command=self.refresh_backend).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(root, text="Uninstall option").pack(anchor="w")
        action_box = ttk.Combobox(
            root,
            textvariable=self.action_var,
            state="readonly",
            values=(
                "Uninstall selected extension only",
                "Uninstall all extensions only",
                "Launch full Simple Signal uninstaller",
            ),
        )
        action_box.pack(fill=tk.X, pady=(4, 14))
        action_box.bind("<<ComboboxSelected>>", lambda _event: self.update_controls())

        ttk.Label(root, text="Extension").pack(anchor="w")
        self.extension_box = ttk.Combobox(root, textvariable=self.extension_var, state="readonly")
        self.extension_box.pack(fill=tk.X, pady=(4, 14))

        button_row = ttk.Frame(root)
        button_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(button_row, text="Uninstall", command=self.perform_uninstall).pack(side=tk.RIGHT)
        ttk.Button(button_row, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=(0, 8))

        status = ttk.Label(root, textvariable=self.status_var, style="Hint.TLabel", wraplength=510)
        status.pack(anchor="w", pady=(18, 0))

    def refresh_backend(self):
        self.backend_dir = default_backend_dir()
        self.extensions_dir = default_extensions_dir()
        self.backend_var.set(str(self.extensions_dir))
        self.refresh_extensions()

    def refresh_extensions(self):
        self.extension_by_label = {}
        if not self.extensions_dir:
            self.extensions = []
        else:
            self.extensions = list_extensions(self.extensions_dir)

        labels = []
        for label, _folder_name, path in self.extensions:
            labels.append(label)
            self.extension_by_label[label] = path

        self.extension_box["values"] = labels
        if labels:
            self.extension_var.set(labels[0])
            self.status_var.set(f"Found {len(labels)} extension(s).")
        else:
            self.extension_var.set("")
            self.status_var.set("No extensions found in the detected backend.")
        self.update_controls()

    def update_controls(self):
        action = self.action_var.get()
        if action == "Uninstall selected extension only":
            self.extension_box.configure(state="readonly")
        else:
            self.extension_box.configure(state="disabled")

    def perform_uninstall(self):
        action = self.action_var.get()
        if action == "Uninstall selected extension only":
            self.uninstall_selected_extension()
        elif action == "Uninstall all extensions only":
            self.uninstall_all_extensions()
        else:
            self.launch_full_uninstaller()

    def uninstall_selected_extension(self):
        if not self.extensions_dir:
            messagebox.showerror("Extensions folder not found", "Could not locate the Simple Signal extensions folder.")
            return
        label = self.extension_var.get()
        target = self.extension_by_label.get(label)
        if not target:
            messagebox.showerror("Extension not found", "Choose an extension to uninstall.")
            return
        if not messagebox.askyesno("Confirm uninstall", f"Remove this extension?\n\n{label}\n\nSimple Signal will be kept."):
            return
        try:
            safe_remove_dir(target, self.extensions_dir)
            self.status_var.set(f"Removed extension: {label}")
            self.refresh_extensions()
        except Exception as exc:
            messagebox.showerror(
                "Uninstall failed",
                "The extension could not be removed. Close Simple Signal and try again.\n\n"
                f"{exc}",
            )

    def uninstall_all_extensions(self):
        if not self.extensions_dir:
            messagebox.showerror("Extensions folder not found", "Could not locate the Simple Signal extensions folder.")
            return
        if not self.extensions:
            messagebox.showinfo("No extensions", "No extensions were found to remove.")
            return
        if not messagebox.askyesno(
            "Confirm uninstall",
            f"Remove all {len(self.extensions)} extension(s)?\n\nSimple Signal will be kept.",
        ):
            return
        errors = []
        extensions_dir = self.extensions_dir
        for label, _folder_name, path in list(self.extensions):
            try:
                safe_remove_dir(path, extensions_dir)
            except Exception as exc:
                errors.append(f"{label}: {exc}")
        self.refresh_extensions()
        if errors:
            messagebox.showerror("Some extensions were not removed", "\n".join(errors))
        else:
            self.status_var.set("Removed all extensions. Simple Signal was kept.")

    def launch_full_uninstaller(self):
        uninstaller = find_system_uninstaller()
        if not uninstaller:
            messagebox.showerror(
                "Full uninstaller not found",
                "Could not find the installed Simple Signal uninstaller.\n\n"
                "Use Windows Settings > Apps to uninstall Simple Signal, or run the installer again and choose uninstall if prompted.",
            )
            return
        if not messagebox.askyesno(
            "Launch full uninstaller",
            f"Launch the full Simple Signal uninstaller?\n\n{uninstaller}\n\n"
            "This removes Simple Signal. User-installed extensions are kept unless you remove them here first.",
        ):
            return
        try:
            subprocess.Popen([str(uninstaller)], cwd=str(uninstaller.parent))
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Launch failed", f"Could not launch the full uninstaller.\n\n{exc}")


if __name__ == "__main__":
    app = SimpleSignalUninstaller()
    app.mainloop()
