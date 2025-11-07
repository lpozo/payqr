import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from payqr.qr import QRCodeGenerator
from payqr.templates import TemplateManager


def _ensure_user_templates_dir() -> Path:
    """Ensure ~/.payqr/templates/ exists and contains default templates.

    Returns the Path to ~/.payqr/templates/
    """
    user_payqr_dir = Path.home() / ".payqr"
    user_templates_dir = user_payqr_dir / "templates"

    # Get bundled templates directory
    bundled_templates = Path(__file__).parent.parent.parent / "templates"

    # Create directories if they don't exist
    user_templates_dir.mkdir(parents=True, exist_ok=True)

    # Copy templates if directory is empty (config.toml is always read from project)
    template_files = list(user_templates_dir.glob("*.toml"))

    if not template_files:
        if bundled_templates.exists():
            for template_file in bundled_templates.glob("*.toml"):
                if template_file.name != "config.toml":  # Skip config.toml
                    dest = user_templates_dir / template_file.name
                    if not dest.exists():
                        shutil.copy2(template_file, dest)

    return user_templates_dir


class PayQRApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=12)
        self.master = master
        self.master.title("IPS QR Code Generator - PayQR")
        self.grid(sticky="nsew")

        # Configure grid weights
        for i in range(2):
            self.columnconfigure(i, weight=1)
        self.rowconfigure(1, weight=1)

        # Configure style for readonly entries
        self.style = ttk.Style()
        self.style.configure("Readonly.TEntry", fieldbackground="#f0f0f0")

        # Discover templates from user directory
        self.templates_dir = _ensure_user_templates_dir()
        self.template_files = sorted(self.templates_dir.glob("*.toml"))
        self.template_names = [
            f.stem for f in self.template_files if f.name != "config.toml"
        ]

        # Load default template
        default_template = (
            "default"
            if "default" in self.template_names
            else (self.template_names[0] if self.template_names else None)
        )
        if default_template is None:
            raise FileNotFoundError("No .toml templates found in templates/ directory")

        self.current_template = default_template
        template_path = self.templates_dir / f"{self.current_template}.toml"
        self.template_mgr = TemplateManager(str(template_path))
        self.qr = QRCodeGenerator(fixed_size=(490, 490))

        # Build UI
        self.vars = {}
        self._last_image = None
        self.form_frame = None
        self.modified_var = tk.BooleanVar(value=False)  # Track if template modified
        self.original_values = {}  # Store original template values
        self.setup_ui()
        self._store_original_values()

    @staticmethod
    def _format_label(table_name: str, key: str) -> str:
        """Format TOML table name with spaces and add key in parentheses."""
        # Insert spaces before uppercase letters (for PascalCase/camelCase)
        spaced = re.sub(r"([A-Z])", r" \1", table_name).strip()
        return f"{spaced} ({key}):"

    def _store_original_values(self):
        """Store current values as baseline for modification detection."""
        self.original_values = {k: v.get() for k, v in self.vars.items()}
        self.modified_var.set(False)

    def _check_modified(self, *args):
        """Check if any field differs from original template values."""
        modified = any(
            self.vars[k].get() != self.original_values.get(k, "") for k in self.vars
        )
        self.modified_var.set(modified)

    def setup_ui(self):
        """Create the user interface."""
        # Template selector
        selector_frame = ttk.Frame(self, padding=4)
        selector_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(selector_frame, text="Template:").pack(side="left", padx=(0, 8))
        self.template_combo = ttk.Combobox(
            selector_frame, values=self.template_names, state="readonly", width=20
        )
        self.template_combo.set(self.current_template)
        self.template_combo.pack(side="left")
        self.template_combo.bind("<<ComboboxSelected>>", self.on_template_change)

        # Modified indicator
        self.modified_label = ttk.Label(
            selector_frame,
            text="",
            foreground="orange",
            font=("TkDefaultFont", 9, "italic"),
        )
        self.modified_label.pack(side="left", padx=(12, 0))

        # Update indicator when modified state changes
        def update_indicator(*args):
            if self.modified_var.get():
                self.modified_label.config(text="● Modified")
            else:
                self.modified_label.config(text="")

        self.modified_var.trace_add("write", update_indicator)

        # Create input form
        self.form_frame = ttk.LabelFrame(self, text="Payment Details", padding=8)
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        # Fields that should be read-only
        readonly_fields = {"IdentificationCode", "Version", "CodeSet"}

        # Currency storage for Amount field
        self.currency_var = None
        self.amount_numeric_var = None

        for idx, field in enumerate(self.template_mgr.get_fields()):
            label_text = self._format_label(field["label"], field["key"])
            ttk.Label(self.form_frame, text=label_text).grid(
                row=idx, column=0, sticky="w", padx=4, pady=2
            )

            # Special handling for Amount field with currency
            if field["label"] == "Amount":
                # Parse currency and amount from value like "RSD9000,00"
                value = field["value"]
                currency = "RSD"
                amount = value

                # Try to extract currency code (first 3 letters)
                import re

                match = re.match(r"^([A-Z]{3})(.+)$", value)
                if match:
                    currency, amount = match.groups()

                # Create frame for currency + amount
                amount_frame = ttk.Frame(self.form_frame)
                amount_frame.grid(row=idx, column=1, sticky="ew", padx=4, pady=2)

                # Currency entry (read-only)
                self.currency_var = tk.StringVar(value=currency)
                currency_entry = ttk.Entry(
                    amount_frame,
                    textvariable=self.currency_var,
                    style="Readonly.TEntry",
                    state="readonly",
                    width=5,
                )
                currency_entry.pack(side="left", padx=(0, 4))

                # Amount entry
                self.amount_numeric_var = tk.StringVar(value=amount)
                amount_entry = ttk.Entry(
                    amount_frame, textvariable=self.amount_numeric_var, width=30
                )
                amount_entry.pack(side="left", fill="x", expand=True)

                # Store a combined var that concatenates currency + amount
                combined_var = tk.StringVar(value=field["value"])
                self.vars[field["key"]] = combined_var

                # Trace changes to update combined value
                def update_combined(*args):
                    cv = self.currency_var.get() if self.currency_var else ""
                    av = (
                        self.amount_numeric_var.get() if self.amount_numeric_var else ""
                    )
                    combined_var.set(f"{cv}{av}")
                    self._check_modified()

                self.currency_var.trace_add("write", update_combined)
                self.amount_numeric_var.trace_add("write", update_combined)

                continue

            var = tk.StringVar(value=field["value"])
            self.vars[field["key"]] = var
            var.trace_add("write", self._check_modified)

            # Create entry with readonly state for fixed fields
            if field["label"] in readonly_fields:
                entry = ttk.Entry(
                    self.form_frame,
                    textvariable=var,
                    width=40,
                    style="Readonly.TEntry",
                    state="readonly",
                )
            else:
                entry = ttk.Entry(self.form_frame, textvariable=var, width=40)
            entry.grid(row=idx, column=1, sticky="ew", padx=4, pady=2)

        self.form_frame.columnconfigure(1, weight=1)

        # Actions and preview
        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            actions,
            text="Generate",
            command=self.on_generate,
        ).pack(side=tk.LEFT)
        ttk.Button(
            actions,
            text="Save as...",
            command=self.on_save,
        ).pack(side=tk.LEFT, padx=8)

        preview_frame = ttk.LabelFrame(self, text="IPS QR Code Preview", padding=8)
        preview_frame.grid(row=1, column=1, rowspan=2, sticky="nsew")
        preview_frame.grid_propagate(False)
        preview_frame.configure(width=540, height=540)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        # Preview label to hold the generated QR image
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        self.form_frame.columnconfigure(1, weight=1)

    def payload(self) -> str:
        overrides = {k: v.get() for k, v in self.vars.items()}
        return self.template_mgr.render_payload(overrides)

    def _save_template_if_modified(self):
        """Auto-save template if it has been modified."""
        if not self.modified_var.get():
            return

        try:
            template_name = self.current_template
            
            # If modifying default template, prompt for new template name
            if template_name == "default":
                # Prompt for new template name
                dialog = tk.Toplevel(self)
                dialog.title("Save Template As")
                dialog.transient(self)
                dialog.grab_set()
                
                frame = ttk.Frame(dialog, padding=20)
                frame.grid(row=0, column=0, sticky="nsew")
                
                ttk.Label(frame, text="You are modifying the default template.", 
                         font=("TkDefaultFont", 9, "bold")).grid(
                    row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
                )
                
                ttk.Label(frame, text="Enter new template name:").grid(
                    row=1, column=0, columnspan=2, sticky="w", pady=(0, 4)
                )
                
                name_var = tk.StringVar()
                entry = ttk.Entry(frame, textvariable=name_var, width=30)
                entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
                entry.focus_set()
                
                result = {"save": False, "name": ""}
                
                def on_ok():
                    name = name_var.get().strip()
                    if not name:
                        messagebox.showerror("Error", "Template name cannot be empty.", parent=dialog)
                        return
                    # Sanitize name
                    import re
                    sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", name)
                    if sanitized in self.template_names:
                        messagebox.showerror("Error", f"Template '{sanitized}' already exists.", parent=dialog)
                        return
                    result["save"] = True
                    result["name"] = sanitized
                    dialog.destroy()
                
                def on_cancel():
                    dialog.destroy()
                
                button_frame = ttk.Frame(frame)
                button_frame.grid(row=3, column=0, columnspan=2, sticky="e")
                ttk.Button(button_frame, text="OK", command=on_ok).pack(side="left", padx=(0, 4))
                ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side="left")
                
                # Center dialog
                dialog.update_idletasks()
                x = self.winfo_rootx() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
                y = self.winfo_rooty() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
                dialog.geometry(f"+{x}+{y}")
                
                dialog.wait_window()
                
                if not result["save"]:
                    return  # User cancelled
            
            template_path = self.templates_dir / f"{template_name}.toml"

            # Build TOML content with current values
            lines = ["# Variable fields\n"]
            for field in self.template_mgr.get_fields():
                label = field["label"]
                key = field["key"]
                # Skip fixed fields (they're in config.toml)
                if label in ("IdentificationCode", "Version", "CodeSet"):
                    continue

                # Get current value from GUI
                value = self.vars[key].get()
                desc = field.get("description", "")

                lines.append(f"\n[{label}]\n")
                lines.append(f'key = "{key}"\n')
                lines.append(f'value = "{value}"\n')
                lines.append("required = true\n")
                if desc:
                    lines.append(f'description = "{desc}"\n')

            # Write file
            template_path.write_text("".join(lines), encoding="utf-8")
            
            # If we saved as a new template, switch to it
            if template_name != self.current_template:
                self.current_template = template_name
                # Refresh template list
                self.template_files = sorted(self.templates_dir.glob("*.toml"))
                self.template_names = [
                    f.stem for f in self.template_files if f.name != "config.toml"
                ]
                self.template_combo["values"] = self.template_names
                self.template_combo.set(template_name)
                # Reload the template manager with new file
                template_path = self.templates_dir / f"{template_name}.toml"
                self.template_mgr = TemplateManager(str(template_path))

            # Update stored values and clear modified flag
            self._store_original_values()

            # Show brief notification
            self.modified_label.config(text="✓ Saved", foreground="green")

            def reset_indicator():
                if self.modified_var.get():
                    self.modified_label.config(text="● Modified", foreground="orange")
                else:
                    self.modified_label.config(text="", foreground="orange")

            self.after(2000, reset_indicator)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to auto-save template:\n{e}")

    def on_generate(self):
        try:
            # Generate QR code with current values first
            payload = self.payload()
            img = self.qr.generate_qr_image(payload)
            self._last_image = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self._last_image)
            
            # Then auto-save if modified
            self._save_template_if_modified()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_save(self):
        try:
            payload = self.payload()
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
                initialfile="untitled.png",
            )
            if not path:
                return
            self.qr.generate_and_save(payload, path)
            messagebox.showinfo("Saved", f"QR saved to\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_template_change(self, event=None):
        """Handle template selection change: reload fields and rebuild the form."""
        selected = self.template_combo.get()
        if not selected:
            return
        self.current_template = selected
        template_path = self.templates_dir / f"{self.current_template}.toml"
        try:
            self.template_mgr = TemplateManager(str(template_path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load template: {e}")
            return

        # Rebuild form
        if self.form_frame is not None:
            self.form_frame.destroy()

        self.vars = {}
        self.currency_var = None
        self.amount_numeric_var = None

        self.form_frame = ttk.LabelFrame(self, text="Payment Details", padding=8)
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        readonly_fields = {"IdentificationCode", "Version", "CodeSet"}

        for idx, field in enumerate(self.template_mgr.get_fields()):
            label_text = self._format_label(field["label"], field["key"])
            ttk.Label(self.form_frame, text=label_text).grid(
                row=idx, column=0, sticky="w", padx=4, pady=2
            )

            if field["label"] == "Amount":
                value = field["value"]
                currency = "RSD"
                amount = value
                match = re.match(r"^([A-Z]{3})(.+)$", value)
                if match:
                    currency, amount = match.groups()

                amount_frame = ttk.Frame(self.form_frame)
                amount_frame.grid(row=idx, column=1, sticky="ew", padx=4, pady=2)

                self.currency_var = tk.StringVar(value=currency)
                currency_entry = ttk.Entry(
                    amount_frame,
                    textvariable=self.currency_var,
                    style="Readonly.TEntry",
                    state="readonly",
                    width=5,
                )
                currency_entry.pack(side="left", padx=(0, 4))

                self.amount_numeric_var = tk.StringVar(value=amount)
                amount_entry = ttk.Entry(
                    amount_frame, textvariable=self.amount_numeric_var, width=30
                )
                amount_entry.pack(side="left", fill="x", expand=True)

                combined_var = tk.StringVar(value=field["value"])
                self.vars[field["key"]] = combined_var

                def update_combined(*_):
                    cv = self.currency_var.get() if self.currency_var else ""
                    av = (
                        self.amount_numeric_var.get() if self.amount_numeric_var else ""
                    )
                    combined_var.set(f"{cv}{av}")
                    self._check_modified()

                self.currency_var.trace_add("write", update_combined)
                self.amount_numeric_var.trace_add("write", update_combined)
                continue

            var = tk.StringVar(value=field["value"])
            self.vars[field["key"]] = var
            var.trace_add("write", self._check_modified)
            if field["label"] in readonly_fields:
                entry = ttk.Entry(
                    self.form_frame,
                    textvariable=var,
                    width=40,
                    style="Readonly.TEntry",
                    state="readonly",
                )
            else:
                entry = ttk.Entry(self.form_frame, textvariable=var, width=40)
            entry.grid(row=idx, column=1, sticky="ew", padx=4, pady=2)

        self.form_frame.columnconfigure(1, weight=1)
        self._store_original_values()

