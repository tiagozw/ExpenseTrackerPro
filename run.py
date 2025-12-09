import os
import sys

# Ensure the working directory is always the folder of run.py
os.chdir(os.path.dirname(os.path.abspath(__file__)))


from src.expense_tracker_gui import ExpenseTrackerApp

if __name__ == "__main__":
    try:
        app = ExpenseTrackerApp()
        app.mainloop()
    except Exception as e:
        print("Application crashed:", e)
