# 💸 Expense Tracker Pro
[⬇️ Download Latest Release](https://github.com/Tiagozw/ExpenseTrackerPro/releases/latest)

![Version](https://img.shields.io/github/v/release/Tiagozw/ExpenseTrackerPro)
![Downloads](https://img.shields.io/github/downloads/Tiagozw/ExpenseTrackerPro/total)
![License](https://img.shields.io/github/license/Tiagozw/ExpenseTrackerPro)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

A clean and modern desktop app to track daily spending, analyze habits, and visualize expenses — built with Python and CustomTkinter. This was my first ever project!

---

## 🖼 Preview

![App Screenshot](./screenshot.jpg)

---

## 🚀 Features

- Add, edit, and delete expenses  
- Category selection and basic AI category suggestion  
- Search and date range filters  
- Dashboard with totals, averages, and recent activity  
- Charts (pie, bar, and line) using Matplotlib  
- Light/Dark mode support via CustomTkinter  
- Local persistent storage in JSON files  
- Export expenses to CSV  
- Packaged Windows executable (PyInstaller)

---

## 🛠 Tech Stack

| Component   | Technology        |
|------------|-------------------|
| UI         | CustomTkinter     |
| Charts     | Matplotlib        |
| Storage    | JSON files        |
| Packaging  | PyInstaller       |
| Language   | Python 3          |

---

## 📂 Project Structure

```text
ExpenseTrackerPro/
│
├─ src/
│   ├─ expense_tracker_gui.py
│   ├─ __init__.py
│   └─ data/                # created automatically, stores expenses.json / settings.json
│
├─ run.py                    # entry point to launch the app
├─ requirements.txt
├─ LICENSE
├─ release_notes_v1.0.0.md   # optional, changelog
└─ Expense Tracker Pro.spec  # PyInstaller build spec
