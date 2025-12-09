import os
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import customtkinter as ctk
from tkinter import messagebox
from tkinter import filedialog


from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# ------------------------------------------------------------
# Expense Tracker Pro — Application Metadata
# ------------------------------------------------------------
APP_NAME = "Expense Tracker Pro"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Tiago F."
APP_YEAR = "2025"


class ExpenseTrackerApp(ctk.CTk):
    # ---- Universal Button Style ----
    BTN_NORMAL = "#3a3c43"
    BTN_HOVER = "#4b4e57"
    BTN_PRIMARY = "#5865F2"
    BTN_PRIMARY_HOVER = "#4752C4"
    BTN_DANGER = "#b80000"
    BTN_DANGER_HOVER = "#8c0000"
    BTN_RADIUS = 8
    BTN_HEIGHT = 32

    def __init__(self):
        super().__init__()
        import os
        import sys

        # --- File Path System (Corrected for Packaging & Dev) ---
        if getattr(sys, 'frozen', False):
            # Running from .exe
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running from source
            base_dir = os.path.dirname(os.path.abspath(__file__))

        data_dir = os.path.join(base_dir, "data")

        # Ensure folder exists
        os.makedirs(data_dir, exist_ok=True)

        self.expenses_file = os.path.join(data_dir, "expenses.json")
        self.settings_file = os.path.join(data_dir, "settings.json")

        # --- Base window config ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_NAME}  —  v{APP_VERSION}")
        self.geometry("1150x680")
        self.minsize(1000, 620)

        # --- State / settings ---
        self.settings = self.load_settings()
        self.expenses = self.load_expenses()

        # Global state for filters / UI
        self.search_query = ""
        self.current_category_filter = "All"
        self.current_date_filter = "all"  # "7", "30", "90", "all"
        self.current_sort_mode = None
        self.charts_range = "30"
        self.dashboard_range = "30"
        self.selected_row_index = None
        self.chart_frame = None
        self.expense_list_container = None
        self.current_view = None

        # --- Layout: sidebar + main area ---
        self.grid_columnconfigure(0, weight=0)   # sidebar
        self.grid_columnconfigure(1, weight=1)   # main
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_rowconfigure(99, weight=1)  # spacer

        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        # --- Sidebar content ---
        self._build_sidebar()

        # Initial page
        self.show_welcome()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.safe_close)

    # ================== CORE HELPERS ==================

    def after(self, ms, func=None):
        """Patch to track scheduled callbacks for clean closing."""
        if not hasattr(self, "_after_callbacks"):
            self._after_callbacks = []
        callback = super().after(ms, func)
        self._after_callbacks.append(callback)
        return callback


    def make_button(self, parent, text, command=None, width=120, primary=False, danger=False):
        """Centralised CTkButton factory for consistent styling."""
        if primary:
            fg = self.BTN_PRIMARY
            hover = self.BTN_PRIMARY_HOVER
        elif danger:
            fg = self.BTN_DANGER
            hover = self.BTN_DANGER_HOVER
        else:
            fg = self.BTN_NORMAL
            hover = self.BTN_HOVER

        return ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=self.BTN_HEIGHT,
            corner_radius=self.BTN_RADIUS,
            fg_color=fg,
            hover_color=hover,
            command=command,
        )

    def button_row(self, parent, buttons, spacing=8):
        """
        Helper: create a horizontal row of buttons with consistent spacing.
        buttons = [(text, command, options_dict)]
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(anchor="w", pady=(6, 12))

        for i, (text, command, opts) in enumerate(buttons):
            btn = self.make_button(frame, text, command, **opts)
            btn.pack(side="left", padx=(0, spacing) if i < len(buttons) - 1 else 0)

        return frame

    def title_label(self, parent, text):
        """Unified style for main page titles."""
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=24, weight="bold"),
        )

    def subtitle_label(self, parent, text, wrap=750):
        """Unified style for description text under headers."""
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            wraplength=wrap,
            justify="left",
        )


    def load_settings(self):
        defaults = {
            "currency": "€",
            "theme": "dark",
            "report_range": "30",
            "temperature": 0.4,
            "chart_style": "minimal",
            "openai_model": "gpt-4o-mini",
        }

        if not os.path.exists(self.settings_file):
            self._save_json_safely(self.settings_file, defaults)
            return defaults

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return defaults
            return {**defaults, **data}
        except:
            return defaults

    def save_settings_file(self):
        self._save_json_safely(self.settings_file, self.settings)

    def _save_json_safely(self, path, data):
        """Safely save JSON to the correct file location."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Error saving JSON:", e)

    def load_expenses(self):
        if not os.path.exists(self.expenses_file):
            return []

        try:
            with open(self.expenses_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except:
            return []


    def save_expenses(self):
        self._save_json_safely(self.expenses_file, self.expenses)

    def export_to_csv(self):
        """Export expenses to a CSV file."""
        if not self.expenses:
            messagebox.showinfo("Export", "No expenses to export.")
            return

        # Ask user where to save file
        from datetime import datetime
        default_name = f"Expenses_{datetime.now().strftime('%Y-%m-%d')}.csv"

        file_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Exported Expenses"
        )


        if not file_path:
            return  # user canceled

        import csv

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Amount", "Currency", "Category", "Description", "Date"])

            currency = self.settings.get("currency", "€")

            for exp in self.get_filtered_sorted_expenses():
                writer.writerow([
                    f"{float(exp['amount']):.2f}",
                    currency,
                    exp["category"],
                    exp["description"],
                    exp["date"]
                ])

        messagebox.showinfo("Export Complete", f"Expenses exported to:\n{file_path}")


    def get_currency_symbol(self):
        return self.settings.get("currency", "€")

    def clear_main(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self.chart_frame = None
        self.expense_list_container = None

    def safe_close(self):
        try:
            # cancel any running scheduled callbacks
            callbacks = getattr(self, "_after_callbacks", [])
            for cb in callbacks:
                try: self.after_cancel(cb)
                except: pass
        except: pass

        try: self.quit()
        except: pass

        self.destroy()



    # ================== SIDEBAR ==================

    def _build_sidebar(self):
        title = ctk.CTkLabel(
            self.sidebar,
            text="Expense\nTracker Pro",
            font=ctk.CTkFont(size=20, weight="bold"),
            justify="left",
        )
        title.grid(row=0, column=0, padx=15, pady=(20, 10), sticky="w")

        subtitle = ctk.CTkLabel(
            self.sidebar,
            text="AI-powered desktop app",
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af",
        )
        subtitle.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="w")

        row = 2
        self.make_button(self.sidebar, "Home", self.show_welcome, width=160).grid(
            row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        self.make_button(self.sidebar, "Add Expense", self.show_add_expense, width=160, primary=True).grid(
            row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        self.make_button(self.sidebar, "View Expenses", self.show_view_expenses, width=160).grid(
            row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        self.make_button(self.sidebar, "Dashboard", self.show_dashboard, width=160).grid(
            row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        self.make_button(self.sidebar, "Charts", self.show_charts, width=160).grid(
            row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        self.make_button(self.sidebar, "AI Insights", self.show_ai_panel, width=160).grid(
            row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        self.make_button(self.sidebar, "Settings", self.show_settings, width=160).grid(
        row=row, column=0, padx=15, pady=3, sticky="ew"
        ); row += 1

        # spacer row
        row = 999

        self.make_button(self.sidebar, "Exit", self.safe_close, width=160, danger=True).grid(
        row=row, column=0, padx=15, pady=(20, 30), sticky="ew"
        )

        # Developer credit footer
        footer = ctk.CTkLabel(
            self.sidebar,
            text="Developed by Tiago.F",
            font=ctk.CTkFont(size=10),
            text_color="#6b7280"
        )
        footer.grid(row=row+1, column=0, pady=(5, 10))

     
    # ================== WELCOME PAGE ==================

    def show_welcome(self):
        self.current_view = self.show_dashboard
        self.clear_main()

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=30)

        ctk.CTkLabel(
            container,
            text="Welcome to Expense Tracker Pro",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            container,
            text="Track your expenses, visualize charts, and get AI-powered insights on your spending.",
            font=ctk.CTkFont(size=14),
            text_color="#9ca3af",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        # Quick stats
        cur = self.get_currency_symbol()
        total = sum(float(e.get("amount", 0)) for e in self.expenses)
        count = len(self.expenses)

        stats_frame = ctk.CTkFrame(container)
        stats_frame.pack(anchor="w", pady=10)

        ctk.CTkLabel(
            stats_frame,
            text=f"Total recorded: {cur}{total:.2f}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            stats_frame,
            text=f"Number of expenses: {count}",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(2, 0))

        # Quick actions
        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.pack(anchor="w", pady=(20, 0))

        self.make_button(actions, "➕ Add Expense", self.show_add_expense, width=150, primary=True).pack(
            side="left", padx=(0, 10)
        )
        self.make_button(actions, "📊 Open Dashboard", self.show_dashboard, width=160).pack(
            side="left", padx=(0, 10)
        )
        self.make_button(actions, "📈 Charts", self.show_charts, width=120).pack(
            side="left", padx=(0, 10)
        )

    # ================== ADD EXPENSE ==================

    def guess_category(self, desc: str) -> str:
        desc = desc.lower()
        mapping = {
            "food": ["restaurant", "dinner", "lunch", "groceries", "cafe", "coffee"],
            "transport": ["uber", "bus", "taxi", "train", "fuel", "gas", "petrol"],
            "shopping": ["amazon", "store", "shopping", "clothes"],
            "entertainment": ["netflix", "spotify", "cinema", "movie", "game"],
            "bills": ["electricity", "water", "internet", "rent", "bill"],
            "health": ["pharmacy", "doctor", "gym", "health"],
            "travel": ["hotel", "flight", "airbnb", "booking.com", "trip"],
        }
        for cat, keywords in mapping.items():
            if any(k in desc for k in keywords):
                return cat.capitalize()
        return "Other"

    def show_add_expense(self):
        self.current_view = self.show_dashboard
        self.clear_main()

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=30)

        self.title_label(container, "Add Expense").pack(anchor="w", pady=(0, 5))
        self.subtitle_label(container, "Quickly record a new expense with amount, description, and category.").pack(
            anchor="w", pady=(0, 15)
        )

        # ---- Form Layout ----
        form = ctk.CTkFrame(container, fg_color="transparent")
        form.pack(anchor="w", pady=(10, 20))

        # 2-column layout
        form.grid_columnconfigure(0, weight=0)
        form.grid_columnconfigure(1, weight=1)

        # ---- Amount ----
        ctk.CTkLabel(
            form,
            text="💰 Amount:",
            font=ctk.CTkFont(size=14)
        ).grid(row=0, column=0, padx=(0, 15), pady=6, sticky="e")

        entry_amount = ctk.CTkEntry(form, placeholder_text="e.g. 12.50", width=260)
        entry_amount.grid(row=0, column=1, sticky="w")

        # ---- Description ----
        ctk.CTkLabel(
            form,
            text="💬 Description:",
            font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, padx=(0, 15), pady=6, sticky="e")

        entry_desc = ctk.CTkEntry(form, placeholder_text="e.g. Lunch with friends", width=260)
        entry_desc.grid(row=1, column=1, sticky="w")

        # ---- Category ----
        ctk.CTkLabel(
            form,
            text="🏷 Category:",
            font=ctk.CTkFont(size=14)
        ).grid(row=2, column=0, padx=(0, 15), pady=6, sticky="e")

        category_var = ctk.StringVar(value="Other")
        category_dropdown = ctk.CTkComboBox(
            form,
            variable=category_var,
            values=[
                "Food",
                "Transport",
                "Shopping",
                "Entertainment",
                "Bills",
                "Health",
                "Travel",
                "Other",
            ],
            width=260
        )
        category_dropdown.grid(row=2, column=1, sticky="w")

        # Suggest button
        def on_suggest():
            desc = entry_desc.get().strip()
            if not desc:
                messagebox.showinfo("Info", "Enter a description first.")
                return
            suggested = self.guess_category(desc)
            category_var.set(suggested)
            messagebox.showinfo("Suggestion", f"Suggested category: {suggested}")

        self.make_button(container, "✨ Suggest Category", on_suggest, width=200).pack(
            pady=(10, 5), anchor="w"
        )   


        # Actions
        def on_add():
            amount_str = entry_amount.get().strip()
            desc = entry_desc.get().strip()
            cat = category_var.get()

            if not amount_str or not desc:
                messagebox.showerror("Error", "Amount and description are required.")
                return

            try:
                amount = float(amount_str)
            except ValueError:
                messagebox.showerror("Error", "Invalid amount. Please enter a number.")
                return

            new_exp = {
                "amount": amount,
                "description": desc,
                "category": cat,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.expenses.append(new_exp)
            self.save_expenses()
            messagebox.showinfo("Added", "Expense saved successfully.")
            self.show_view_expenses()

        def on_cancel():
            self.show_view_expenses()

        row = self.button_row(
            container,
            [
                ("Cancel", on_cancel, {"width": 120}),
                ("Add Expense", on_add, {"width": 140, "primary": True}),
            ],
        )

        row.pack(pady=(15, 5), anchor="center")

    def show_settings(self):
        self.current_view = self.show_dashboard
        self.clear_main()
        self.app_version = "1.0.0"

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=30)

        self.title_label(container, "Settings").pack(anchor="w", pady=(0, 5))
        self.subtitle_label(container, "Customize your experience, appearance, and AI settings.").pack(
            anchor="w", pady=(0, 20)
        )

        # Currency
        ctk.CTkLabel(container, text="Currency", font=ctk.CTkFont(size=14)).pack(anchor="w")
        currency_box = ctk.CTkComboBox(
            container,
            values=["€", "$", "£", "₱", "DKK", "SEK"],
            width=120,
            command=lambda v: self.update_setting("currency", v)
        )
        currency_box.set(self.settings.get("currency", "€"))
        currency_box.pack(anchor="w", pady=(2, 12))

        # Theme
        ctk.CTkLabel(container, text="Theme", font=ctk.CTkFont(size=14)).pack(anchor="w")
        theme_box = ctk.CTkComboBox(
            container,
            values=["dark", "light", "system"],
            width=120,
            command=lambda v: (ctk.set_appearance_mode(v), self.update_setting("theme", v))
        )
        theme_box.set(self.settings.get("theme", "dark"))
        theme_box.pack(anchor="w", pady=(2, 12))

        # AI Model
        ctk.CTkLabel(container, text="AI Model", font=ctk.CTkFont(size=14)).pack(anchor="w")
        ai_box = ctk.CTkComboBox(
            container,
            values=["gpt-4o-mini", "gpt-4.1-mini", "gpt-3.5-turbo-lite"],
            width=200,
            command=lambda v: self.update_setting("openai_model", v)
        )
        ai_box.set(self.settings.get("openai_model", "gpt-4o-mini"))
        ai_box.pack(anchor="w", pady=(2, 25))

        # --- About section ---
        about_frame = ctk.CTkFrame(container, fg_color="transparent")
        about_frame.pack(fill="x", pady=(30, 10))

        ctk.CTkLabel(
            about_frame,
            text="About",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            about_frame,
            text=f"{APP_NAME} v{APP_VERSION}\nDeveloped by {APP_AUTHOR} — {APP_YEAR}",
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            justify="left"
        ).pack(anchor="w", pady=(5, 0))
 
        # Save button
        self.button_row(
            container,
            [
                ("Save", lambda: (self.save_settings_file(), messagebox.showinfo("Settings", "Saved!")), {"width": 120, "primary": True})
            ]
        )


    # ================== VIEW EXPENSES ==================

    def get_filtered_sorted_expenses(self):
        data = list(self.expenses)

        # search filter
        if self.search_query:
            q = self.search_query.lower()
            data = [
                e
                for e in data
                if q in str(e.get("description", "")).lower()
                or q in str(e.get("category", "")).lower()
            ]

        # category filter (future use)
        if self.current_category_filter != "All":
            data = [e for e in data if e.get("category") == self.current_category_filter]

        # date filter
        if self.current_date_filter in ("7", "30", "90"):
            days = int(self.current_date_filter)
            cutoff = datetime.now() - timedelta(days=days)

            def parse_date(e):
                try:
                    return datetime.strptime(e.get("date", "")[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return datetime.min

            data = [e for e in data if parse_date(e) >= cutoff]

        # sorting
        if self.current_sort_mode == "amount_asc":
            data.sort(key=lambda e: float(e.get("amount", 0)))
        elif self.current_sort_mode == "amount_desc":
            data.sort(key=lambda e: float(e.get("amount", 0)), reverse=True)
        elif self.current_sort_mode == "date_new":
            data.sort(key=lambda e: e.get("date", ""), reverse=True)
        elif self.current_sort_mode == "date_old":
            data.sort(key=lambda e: e.get("date", ""))

        for e in data:
            e["category"] = e.get("category", "Other").title()

        return data


    def show_view_expenses(self):
        self.current_view = self.show_view_expenses
        self.clear_main()

        # reset basic state
        self.search_query = ""
        self.current_category_filter = "All"
        self.current_date_filter = "all"
        self.current_sort_mode = None
        self.selected_row_index = None

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text="All Expenses",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        # --- Search + filters row ---
        top = ctk.CTkFrame(container, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        # Search
        search_frame = ctk.CTkFrame(top, fg_color="transparent")
        search_frame.pack(side="left", padx=(0, 20))

        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search description or category...",
            width=260,
        )
        search_entry.pack(side="left", padx=(0, 8))

        def run_search():
            self.search_query = search_entry.get().strip()
            self.refresh_view_expenses()

        self.make_button(search_frame, "Search", run_search, width=90).pack(side="left")

        # Date filter buttons
        filter_frame = ctk.CTkFrame(top, fg_color="transparent")
        filter_frame.pack(side="left")

        active_color = "#5865F2"
        inactive_color = "#3a3c43"
        date_buttons = {}

        def set_date_filter(val):
            self.current_date_filter = val
            refresh_date_buttons()
            self.refresh_view_expenses()

        def make_date_btn(label, value):
            btn = self.make_button(
                filter_frame,
                label,
                command=lambda v=value: set_date_filter(v),
                width=70,
            )
            date_buttons[btn] = value
            return btn

        make_date_btn("7d", "7").pack(side="left", padx=2)
        make_date_btn("30d", "30").pack(side="left", padx=2)
        make_date_btn("90d", "90").pack(side="left", padx=2)
        make_date_btn("All", "all").pack(side="left", padx=2)

        def refresh_date_buttons():
            for btn, val in date_buttons.items():
                if self.current_date_filter == val:
                    btn.configure(fg_color=active_color)
                else:
                    btn.configure(fg_color=inactive_color)

        refresh_date_buttons()

        # ---- Export Button ----
        self.make_button(container, "📤 Export CSV", self.export_to_csv, width=140).pack(
            anchor="w", pady=(5, 10)
        )       

        # --- List container ---
        list_frame = ctk.CTkFrame(container)
        list_frame.pack(expand=True, fill="both")

        scroll = ctk.CTkScrollableFrame(list_frame, fg_color="#2b2d31")
        scroll.pack(expand=True, fill="both", pady=(5, 0))

        self.expense_list_container = scroll
        self.refresh_view_expenses()

    def update_setting(self, key, value):
        """Update a single setting and refresh UI."""
        self.settings[key] = value
        self.save_settings_file()

        # Refresh UI depending on current view
        if hasattr(self, "current_view") and self.current_view:
            self.current_view()
        else:
            self.show_welcome()


    
    def refresh_view_expenses(self):
        import customtkinter as ctk

        # Clear container
        for w in self.expense_list_container.winfo_children():
            w.destroy()

        data = self.get_filtered_sorted_expenses()
        cur = self.get_currency_symbol()

        if not data:
            ctk.CTkLabel(
                self.expense_list_container,
                text="No expenses found.",
                font=ctk.CTkFont(size=13),
                text_color="#9ca3af"
            ).pack(pady=20)
            return

        NORMAL = "#313338"
        HOVER = "#3a3c43"

        for idx, e in enumerate(data):
            row = ctk.CTkFrame(self.expense_list_container, fg_color=NORMAL, corner_radius=6)
            row.pack(fill="x", pady=4, padx=4)

            def on_enter(event, r=row):
                r.configure(fg_color=HOVER)

            def on_leave(event, r=row):
                # True leave check
                x, y = r.winfo_pointerxy()
                abs_x, abs_y = r.winfo_rootx(), r.winfo_rooty()
                w, h = r.winfo_width(), r.winfo_height()
                if not (abs_x <= x <= abs_x + w and abs_y <= y <= abs_y + h):
                    r.configure(fg_color=NORMAL)

            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=8, pady=4)

            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=8)

            amount = ctk.CTkLabel(
                left,
                text=f"{cur}{float(e.get('amount', 0)):.2f}",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            amount.pack(anchor="w")

            desc = ctk.CTkLabel(
                left,
                text=e.get("description", ""),
                font=ctk.CTkFont(size=12),
                text_color="#d1d5db"
            )
            desc.pack(anchor="w")

            category = e.get("category", "Other").title()
            meta = ctk.CTkLabel(
                left,
                text=f"{e.get('category', 'Other')} • {e.get('date', '')}",
                font=ctk.CTkFont(size=11),
                text_color="#9ca3af"
            )
            meta.pack(anchor="w", pady=(0, 2))

            # Buttons
            def edit_closure(i=idx):
                self.edit_expense(i)

            def delete_closure(i=idx):
                self.delete_expense(i)

            self.make_button(right, "Edit", edit_closure, width=70).pack(side="left", padx=(0, 5))
            self.make_button(right, "Delete", delete_closure, width=70, danger=True).pack(side="left")


    def delete_expense(self, index):
        if index < 0 or index >= len(self.expenses):
            return
        exp = self.expenses[index]
        if messagebox.askyesno(
            "Confirm delete",
            f'Delete expense "{exp.get("description", "")}"?',
        ):
            self.expenses.pop(index)
            self.save_expenses()
            self.refresh_view_expenses()

    def edit_expense(self, index):
        if index < 0 or index >= len(self.expenses):
            return
        exp = self.expenses[index]

        win = ctk.CTkToplevel(self)
        win.title("Edit Expense")
        win.geometry("360x280")
        win.grab_set()

        cur = self.get_currency_symbol()

        ctk.CTkLabel(win, text=f"Amount ({cur})").pack(anchor="w", padx=15, pady=(15, 2))
        entry_amount = ctk.CTkEntry(win)
        entry_amount.insert(0, str(exp.get("amount", "")))
        entry_amount.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(win, text="Description").pack(anchor="w", padx=15, pady=(5, 2))
        entry_desc = ctk.CTkEntry(win)
        entry_desc.insert(0, exp.get("description", ""))
        entry_desc.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(win, text="Category").pack(anchor="w", padx=15, pady=(5, 2))
        entry_cat = ctk.CTkEntry(win)
        entry_cat.insert(0, exp.get("category", "Other"))
        entry_cat.pack(fill="x", padx=15, pady=(0, 12))

        def save_changes():
            try:
                amount = float(entry_amount.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Invalid amount.")
                return

            exp["amount"] = amount
            exp["description"] = entry_desc.get().strip()
            exp["category"] = entry_cat.get().strip() or "Other"
            self.save_expenses()
            self.refresh_view_expenses()
            win.destroy()

        self.make_button(win, "Save", save_changes, width=120, primary=True).pack(pady=(0, 15))

    # ================== DASHBOARD ==================

    def _filter_by_range(self, range_value):
        if range_value not in ("7", "30", "90"):
            return list(self.expenses)
        days = int(range_value)
        cutoff = datetime.now() - timedelta(days=days)
        out = []
        for e in self.expenses:
            try:
                dt = datetime.strptime(e.get("date", "")[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if dt >= cutoff:
                out.append(e)
        return out

    def show_dashboard(self):
        self.current_view = self.show_dashboard
        self.clear_main()

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)

        self.title_label(container, "Dashboard").pack(anchor="w", pady=(0, 5))
        self.subtitle_label(container, "High-level overview of your spending and activity.").pack(
            anchor="w", pady=(0, 15)
        )


        # Quick actions
        self.button_row(
            container,
            [
                ("➕ Add Expense", self.show_add_expense, {"width": 140, "primary": True}),
                ("📊 Charts", self.show_charts, {"width": 120}),
            ],
        )


        # Range filter
        filter_frame = ctk.CTkFrame(container, fg_color="transparent")
        filter_frame.pack(anchor="w", pady=(10, 15))

        active_color = "#5865F2"
        inactive_color = "#3a3c43"
        buttons = {}

        def set_range(val):
            self.dashboard_range = val
            refresh_buttons()
            self.show_dashboard()

        def make_range_btn(label, value):
            btn = self.make_button(
                filter_frame,
                label,
                command=lambda v=value: set_range(v),
                width=70,
            )
            buttons[btn] = value
            return btn

        make_range_btn("7d", "7").pack(side="left", padx=2)
        make_range_btn("30d", "30").pack(side="left", padx=2)
        make_range_btn("90d", "90").pack(side="left", padx=2)
        make_range_btn("All", "all").pack(side="left", padx=2)

        def refresh_buttons():
            for btn, val in buttons.items():
                if self.dashboard_range == val:
                    btn.configure(fg_color=active_color)
                else:
                    btn.configure(fg_color=inactive_color)

        refresh_buttons()

        # Stats area
        stats_frame = ctk.CTkFrame(container)
        stats_frame.pack(fill="x", pady=(5, 10))

        cur = self.get_currency_symbol()
        filtered = self._filter_by_range(self.dashboard_range)

        total = sum(float(e.get("amount", 0)) for e in filtered)
        count = len(filtered)

        if filtered:
            dates = [e.get("date", "")[:10] for e in filtered]
            unique_days = len(set(dates))
        else:
            unique_days = 0

        avg_per_day = total / unique_days if unique_days else 0
        avg_per_exp = total / count if count else 0

        # left column
        col1 = ctk.CTkFrame(stats_frame, fg_color="transparent")
        col1.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(col1, text="Total Spent", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(col1, text=f"{cur}{total:.2f}", font=ctk.CTkFont(size=18)).pack(anchor="w")

        ctk.CTkLabel(col1, text="Average per Day", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", pady=(10, 0)
        )
        ctk.CTkLabel(col1, text=f"{cur}{avg_per_day:.2f}", font=ctk.CTkFont(size=16)).pack(anchor="w")

        # middle
        col2 = ctk.CTkFrame(stats_frame, fg_color="transparent")
        col2.pack(side="left", padx=30, pady=10)

        ctk.CTkLabel(col2, text="Average per Expense", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(col2, text=f"{cur}{avg_per_exp:.2f}", font=ctk.CTkFont(size=16)).pack(anchor="w")

        ctk.CTkLabel(col2, text="Number of Expenses", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", pady=(10, 0)
        )
        ctk.CTkLabel(col2, text=f"{count}", font=ctk.CTkFont(size=16)).pack(anchor="w")

        # right: top category
        col3 = ctk.CTkFrame(stats_frame, fg_color="transparent")
        col3.pack(side="left", padx=30, pady=10)

        totals_by_cat = Counter()
        for e in filtered:
            totals_by_cat[e.get("category", "Other")] += float(e.get("amount", 0))

        if totals_by_cat:
            top_cat, top_val = totals_by_cat.most_common(1)[0]
            top_cat_display = top_cat.title()
            ctk.CTkLabel(col3, text="Top Category", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(
                col3,
                text=f"{top_cat_display} ({cur}{top_val:.2f})",
                font=ctk.CTkFont(size=16),
            ).pack(anchor="w")
        else:
            ctk.CTkLabel(col3, text="Top Category", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(col3, text="—", font=ctk.CTkFont(size=16)).pack(anchor="w")


        # Recent activity
        recent_frame = ctk.CTkFrame(container)
        recent_frame.pack(fill="both", expand=True, pady=(10, 0))

        ctk.CTkLabel(
            recent_frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(5, 5))

        scroll = ctk.CTkScrollableFrame(recent_frame, fg_color="#2b2d31")
        scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        recent = list(reversed(self.expenses))[:20]
        if not recent:
            ctk.CTkLabel(
                scroll,
                text="No expenses yet.",
                font=ctk.CTkFont(size=13),
                text_color="#9ca3af",
            ).pack(pady=10)
        else:
            for e in recent:
                row = ctk.CTkFrame(scroll, fg_color="#313338", corner_radius=6)
                row.pack(fill="x", pady=3, padx=4)

                left = ctk.CTkFrame(row, fg_color="transparent")
                left.pack(side="left", fill="x", expand=True, padx=8, pady=4)

                ctk.CTkLabel(
                    left,
                    text=f"{cur}{float(e.get('amount', 0)):.2f}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                ).pack(anchor="w")

                ctk.CTkLabel(
                    left,
                    text=f"{e.get('category', 'Other')} • {e.get('date', '')}",
                    font=ctk.CTkFont(size=11),
                    text_color="#9ca3af",
                ).pack(anchor="w")

                ctk.CTkLabel(
                    left,
                    text=e.get("description", ""),
                    font=ctk.CTkFont(size=11),
                    text_color="#d1d5db",
                ).pack(anchor="w")

    # ================== CHARTS ==================

    def clear_chart_frame(self):
        if self.chart_frame is not None:
            for w in self.chart_frame.winfo_children():
                w.destroy()

    def embed_chart(self, fig):
        self.clear_chart_frame()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def get_chart_filtered_expenses(self):
        return self._filter_by_range(self.charts_range)

    def show_charts(self):
        self.current_view = self.show_dashboard
        self.clear_main()

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)

        self.title_label(container, "Charts & Analytics").pack(anchor="w", pady=(0, 5))


        # Range buttons
        filter_frame = ctk.CTkFrame(container, fg_color="transparent")
        filter_frame.pack(anchor="w", pady=(5, 10))

        active_color = "#5865F2"
        inactive_color = "#3a3c43"
        range_buttons = {}

        def set_chart_range(val):
            self.charts_range = val
            refresh_buttons()
            self.show_charts()

        def make_range_btn(label, value):
            btn = self.make_button(
                filter_frame,
                label,
                command=lambda v=value: set_chart_range(v),
                width=70,
            )
            range_buttons[btn] = value
            return btn

        make_range_btn("7d", "7").pack(side="left", padx=2)
        make_range_btn("30d", "30").pack(side="left", padx=2)
        make_range_btn("90d", "90").pack(side="left", padx=2)
        make_range_btn("All", "all").pack(side="left", padx=2)

        def refresh_buttons():
            for btn, val in range_buttons.items():
                if self.charts_range == val:
                    btn.configure(fg_color=active_color)
                else:
                    btn.configure(fg_color=inactive_color)

        refresh_buttons()

        # Chart type buttons
        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(anchor="w", pady=(5, 10))

        self.make_button(buttons, "Category Pie", self.show_pie_chart, width=140).pack(
            side="left", padx=(0, 8)
        )
        self.make_button(buttons, "Category Bar", self.show_bar_chart, width=140).pack(
            side="left", padx=(0, 8)
        )
        self.make_button(buttons, "Daily Line", self.show_line_chart, width=140).pack(
            side="left", padx=(0, 8)
        )

        # Chart frame
        self.chart_frame = ctk.CTkFrame(container)
        self.chart_frame.pack(expand=True, fill="both", pady=(10, 0))
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        # default chart
        self.show_pie_chart()

    def show_pie_chart(self):
        filtered = self.get_chart_filtered_expenses()
        if not filtered:
            self.clear_chart_frame()
            return

        cur = self.get_currency_symbol()
        totals = Counter()
        for e in filtered:
            totals[e.get("category", "Other")] += float(e.get("amount", 0))

        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        labels = [c.title() for c, _ in sorted_items]
        values = [v for _, v in sorted_items]

        total_sum = sum(values)
        if total_sum == 0:
            self.clear_chart_frame()
            return

        fig, ax = plt.subplots(figsize=(5.5, 4), facecolor="#2b2d31")
        ax.set_facecolor("#2b2d31")

        def autopct(pct):
            return f"{pct:.1f}%" if pct >= 5 else ""

        ax.pie(
            values,
            labels=labels,
            autopct=autopct,
            textprops={"color": "white", "fontsize": 9},
        )
        ax.set_title(f"Spending by Category ({cur})", color="white")
        self.embed_chart(fig)

    def show_bar_chart(self):
        filtered = self.get_chart_filtered_expenses()
        if not filtered:
            self.clear_chart_frame()
            return

        cur = self.get_currency_symbol()
        totals = Counter()

        for e in filtered:
            totals[e.get("category", "Other")] += float(e.get("amount", 0))

        if not totals:
            self.clear_chart_frame()
            return

        # Sort largest > smallest and format labels
        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        labels = [c.title() for c, _ in sorted_items]
        values = [v for _, v in sorted_items]

        fig, ax = plt.subplots(figsize=(6, 4), facecolor="#2b2d31")
        ax.set_facecolor("#2b2d31")

        ax.bar(labels, values)

        ax.set_title(f"Category Spending ({cur})", color="white")
        ax.set_ylabel(cur, color="white")
        ax.tick_params(axis="x", rotation=45, labelcolor="white")
        ax.tick_params(axis="y", labelcolor="white")

        self.embed_chart(fig)


    def show_line_chart(self):
        filtered = self.get_chart_filtered_expenses()
        if not filtered:
            self.clear_chart_frame()
            return

        cur = self.get_currency_symbol()
        daily = defaultdict(float)

        for e in filtered:
            date_key = e.get("date", "")[:10]
            daily[date_key] += float(e.get("amount", 0))

        dates = sorted(daily.keys())
        values = [daily[d] for d in dates]

        # Format dates nicely (example: Jan 05)
        from datetime import datetime
        formatted_dates = [
            datetime.strptime(d, "%Y-%m-%d").strftime("%b %d")
            for d in dates
        ]

        fig, ax = plt.subplots(figsize=(6, 4), facecolor="#2b2d31")
        ax.set_facecolor("#2b2d31")

        ax.plot(formatted_dates, values, marker="o")

        ax.set_title(f"Daily Spending ({cur})", color="white")
        ax.set_xlabel("Date", color="white")
        ax.set_ylabel(cur, color="white")

        ax.tick_params(axis="x", rotation=45, labelcolor="white")
        ax.tick_params(axis="y", labelcolor="white")

        # Optional: subtle grid
        ax.grid(color="#444", linestyle="--", linewidth=0.5, alpha=0.3)

        self.embed_chart(fig)


    # ================== AI PANEL ==================

    def show_ai_panel(self):
        self.current_view = self.show_dashboard
        self.clear_main()

        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text="🤖 AI Financial Insights",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            container,
            text='Ask questions about your expenses (e.g. "What do I spend the most on?", "Any ways to save?").',
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            wraplength=750,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        self.ai_input = ctk.CTkTextbox(container, width=600, height=100)
        self.ai_input.pack(pady=(5, 10), fill="x")

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(anchor="w", pady=(0, 10))

        self.make_button(buttons, "Ask AI", self.ask_ai, width=120, primary=True).pack(
            side="left", padx=(0, 8)
        )

        self.ai_output = ctk.CTkTextbox(container, width=600, height=260)
        self.ai_output.pack(fill="both", expand=True, pady=(5, 0))

    def ask_ai(self):
        """Simple rule-based insights (stub instead of real OpenAI call)."""
        question = self.ai_input.get("1.0", "end").strip()
        if not question:
            messagebox.showinfo("Info", "Type a question first.")
            return

        cur = self.get_currency_symbol()
        total = sum(float(e.get("amount", 0)) for e in self.expenses)
        by_cat = Counter()
        for e in self.expenses:
            by_cat[e.get("category", "Other")] += float(e.get("amount", 0))

        if not self.expenses:
            answer = (
                "You don't have any expenses recorded yet.\n"
                "Add some first so I can analyze your spending."
            )
        else:
            lines = []
            lines.append(
                f"Here are some quick insights based on your {len(self.expenses)} recorded expenses:"
            )

            if by_cat:
                top_cat, top_val = by_cat.most_common(1)[0]
                pct = (top_val / total * 100) if total > 0 else 0
                lines.append(
                    f"• Your top spending category is **{top_cat}**, "
                    f"with about {cur}{top_val:.2f} ({pct:.1f}% of total)."
                )

            avg = total / len(self.expenses)
            lines.append(f"• On average, each expense is about {cur}{avg:.2f}.")

            if by_cat:
                for cat, val in by_cat.most_common(3):
                    if cat.lower() in ("food", "entertainment", "shopping") and val > total * 0.2:
                        lines.append(
                            f"• Consider reviewing your **{cat}** spending. It's relatively high; "
                            "maybe set a monthly limit."
                        )
                        break

            lines.append("")
            lines.append(
                "This is a simple heuristic summary. You can plug in an OpenAI API key later "
                "for deeper, natural-language insights."
            )

            answer = "\n".join(lines)

        self.ai_output.delete("1.0", "end")
        self.ai_output.insert("1.0", answer)


if __name__ == "__main__":
    app = ExpenseTrackerApp()
    app.mainloop()
