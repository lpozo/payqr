import tkinter as tk

from gui.ui import PayQRApp


def main() -> None:
    root = tk.Tk()
    root.geometry("1150x650")
    root.minsize(950, 600)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    app = PayQRApp(root)
    app.grid(row=0, column=0, sticky="nsew")
    root.mainloop()


if __name__ == "__main__":
    main()
