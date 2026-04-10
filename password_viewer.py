# -*- coding: utf-8 -*-
"""
星号密码查看器
拖动眼睛到密码框，绿框标识，松开读取密码
"""
import tkinter as tk
import ctypes
import ctypes.wintypes as wt

# ========== DPI Awareness ==========
# 必须在导入tkinter之后立即设置
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # System DPI aware
    except Exception:
        pass

# ========== WinAPI ==========
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
g32 = ctypes.windll.gdi32

GWL_STYLE = -16
ES_PASSWORD = 0x0020
EM_GETPASSWORDCHAR = 0x00D2
GA_ROOT = 2
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56

# Process/memory constants
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
WH_GETMESSAGE = 3
WM_NULL = 0x0000
WM_GETTEXTLENGTH = 0x000E
WM_GETTEXT = 0x000D

# Colors
CLR_BG = "#1a1f2e"
CLR_CARD = "#252b3b"
CLR_ACCENT = "#4f8ef7"
CLR_SUCCESS = "#6ee7b7"
CLR_DANGER = "#f87171"
CLR_TEXT = "#e2e8f0"
CLR_MUTED = "#64748b"
CLR_BORDER = "#334155"
CLR_ENTRY = "#0f172a"

fnSendMessage = u32.SendMessageW
fnSendMessage.restype = ctypes.c_long
fnSendMessage.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]

# ========== Helpers ==========
def cursor_pos():
    pt = wt.POINT()
    u32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def get_pid(hwnd):
    pid = wt.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def get_window_thread_id(hwnd):
    """Get thread ID of the window"""
    tid = u32.GetWindowThreadProcessId(hwnd, None)
    return tid

def win_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def win_rect(hwnd):
    rc = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rc))
    return rc

def is_password_field(hwnd):
    """只检查窗口自身是否有密码样式，不检查子窗口"""
    style = u32.GetWindowLongW(hwnd, GWL_STYLE)
    if style & ES_PASSWORD:
        return True
    return fnSendMessage(hwnd, EM_GETPASSWORDCHAR, 0, 0) != 0

def find_window_at(x, y, exclude_pid):
    """Find the smallest visible Edit-like window at (x,y) with password style"""
    hits = []

    def check(hwnd):
        if not u32.IsWindowVisible(hwnd):
            return
        if exclude_pid and get_pid(hwnd) == exclude_pid:
            return
        r = wt.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w > 0 and h > 0 and r.left <= x <= r.right and r.top <= y <= r.bottom:
            hits.append((w * h, hwnd))

    def enum_top(hwnd, _):
        check(hwnd)
        def enum_c(ch, __):
            check(ch)
            return True
        ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        u32.EnumChildWindows(hwnd, ENUM(enum_c), 0)
        return True

    ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    u32.EnumWindows(ENUM(enum_top), 0)

    if not hits:
        return 0

    # Sort by area, find smallest Edit-like controls first
    hits.sort()
    edit_classes = ('edit', 'nsedit', 'combobox')
    for area, hwnd in hits:
        cls = win_class(hwnd).lower()
        for ec in edit_classes:
            if ec in cls:
                return hwnd

    return hits[0][1]

# ========== GDI Highlight ==========
def draw_rect(rc, color_hex, width=3):
    r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
    cref = b | (g << 8) | (r << 16)
    hdc = u32.GetDC(0)
    if not hdc:
        return
    pen = g32.CreatePen(0, width, cref)
    old_pen = g32.SelectObject(hdc, pen)
    old_brush = g32.SelectObject(hdc, g32.GetStockObject(5))
    g32.Rectangle(hdc, rc.left - width, rc.top - width, rc.right + width, rc.bottom + width)
    g32.SelectObject(hdc, old_pen)
    g32.SelectObject(hdc, old_brush)
    g32.DeleteObject(pen)
    u32.ReleaseDC(0, hdc)

def erase_rect(rc, width=3):
    m = width + 4
    erc = wt.RECT(rc.left - m, rc.top - m, rc.right + m, rc.bottom + m)
    u32.InvalidateRect(0, ctypes.byref(erc), True)

# ========== Password Reading ==========
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("union", _INPUT_UNION)]

def key_down(vk):
    ki = KEYBDINPUT(vk, 0, 0, 0, None)
    inp = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki))
    u32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def key_up(vk):
    ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None)
    inp = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki))
    u32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def read_password_via_hook(hwnd):
    """
    Read password using DLL injection via helper EXE.
    Automatically selects 32-bit or 64-bit helper based on target architecture.
    """
    import os
    import subprocess

    target_pid = get_pid(hwnd)

    # Check if target is 32-bit (WOW64)
    hproc = k32.OpenProcess(0x0410, False, target_pid)  # QUERY_INFORMATION
    is_32bit = False
    if hproc:
        is_wow64 = wt.BOOL(False)
        if k32.IsWow64Process(hproc, ctypes.byref(is_wow64)):
            is_32bit = bool(is_wow64.value)
        k32.CloseHandle(hproc)

    # Select helper based on target architecture
    if is_32bit:
        helper = "load_hook32.exe"
    else:
        helper = "load_hook64.exe"

    helper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), helper)
    if not os.path.exists(helper_path):
        return None

    hwnd_hex = format(hwnd, 'x')
    try:
        r = subprocess.Popen(
            [helper_path, hwnd_hex],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out, _ = r.communicate(timeout=10)
        output = out.decode('gbk', errors='replace')

        if 'SUCCESS!' in output:
            idx = output.find('Password: ')
            if idx >= 0:
                pwd_line = output[idx + len('Password: '):].strip()
                pwd_line = pwd_line.strip('\r\n\\/ ')
                return pwd_line
        return ""
    except subprocess.TimeoutExpired:
        r.kill()
        return None
    except Exception:
        return None

def read_password(hwnd):
    """
    Main entry: try hook method first, fallback to DLL inject.
    """
    # Method 1: Same process - direct read
    my_pid = k32.GetCurrentProcessId()
    target_pid = get_pid(hwnd)
    if target_pid == my_pid:
        length = fnSendMessage(hwnd, WM_GETTEXTLENGTH, 0, 0)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            fnSendMessage(hwnd, WM_GETTEXT, length + 1, ctypes.addressof(buf))
            return buf.value
        return ""

    # Method 2: SetWindowsHookEx (preferred, works for both 32/64-bit)
    pwd = read_password_via_hook(hwnd)
    if pwd is not None:  # None means hook failed, try fallback
        return pwd

    # Method 3: Fallback to DLL injection via CreateRemoteThread (32-bit only)
    return read_password_via_dll_inject(hwnd)

def read_password_via_dll_inject(hwnd):
    """
    Legacy method: DLL injection via CreateRemoteThread.
    Only works for 32-bit target processes.
    """
    import os

    my_pid = k32.GetCurrentProcessId()
    target_pid = get_pid(hwnd)

    # For 32-bit processes: use DLL injection
    dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "password_reader_32.dll")
    if not os.path.exists(dll_path):
        return ""

    # Open target process
    hproc = k32.OpenProcess(PROCESS_ALL_ACCESS, False, target_pid)
    if not hproc:
        return ""

    # Check if 32-bit
    is_wow64 = wt.BOOL(False)
    k32.IsWow64Process(hproc, ctypes.byref(is_wow64))
    is_32 = bool(is_wow64.value)

    if not is_32:
        # 64-bit process: can't use CreateRemoteThread easily
        k32.CloseHandle(hproc)
        return ""

    # Create shared memory (file mapping)
    SHM_NAME = "Local\\PwdReaderSHM"
    SHM_SIZE = 8 + 1024 + 4 + 4  # hwnd(8) + password(1024) + done(4) + ready(4) = 1040

    hMap = k32.CreateFileMappingW(
        ctypes.c_void_p(-1),  # INVALID_HANDLE_VALUE
        None,
        PAGE_READWRITE,
        0,
        SHM_SIZE,
        SHM_NAME
    )
    if not hMap:
        k32.CloseHandle(hproc)
        return ""

    # Map it in our process
    local_sd = ctypes.windll.kernel32.MapViewOfFile(
        hMap, 0x0002 | 0x0004, 0, 0, SHM_SIZE  # FILE_MAP_READ | FILE_MAP_WRITE
    )
    if not local_sd:
        k32.CloseHandle(hMap)
        k32.CloseHandle(hproc)
        return ""

    # Write target HWND to shared memory
    class SharedData(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("password", ctypes.c_wchar * 512),
            ("done", ctypes.c_long),
            ("ready", ctypes.c_long),
        ]

    sd = ctypes.cast(local_sd, ctypes.POINTER(SharedData)).contents
    sd.hwnd = hwnd
    sd.password = ""
    sd.done = 0
    sd.ready = 0

    # Write DLL path to target process
    dll_path_w = dll_path.encode('utf-16-le') + b'\x00\x00'
    remote_path = k32.VirtualAllocEx(hproc, None, len(dll_path_w) + 256,
                                      MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    if not remote_path:
        ctypes.windll.kernel32.UnmapViewOfFile(local_sd)
        k32.CloseHandle(hMap)
        k32.CloseHandle(hproc)
        return ""

    written = ctypes.c_size_t(0)
    k32.WriteProcessMemory(hproc, ctypes.c_void_p(remote_path), dll_path_w, len(dll_path_w), ctypes.byref(written))

    # Get LoadLibraryW address (same across processes for kernel32.dll)
    h_kernel32 = k32.GetModuleHandleW("kernel32.dll")
    load_lib = k32.GetProcAddress(h_kernel32, b"LoadLibraryW")

    if not load_lib:
        k32.VirtualFreeEx(hproc, ctypes.c_void_p(remote_path), 0, MEM_RELEASE)
        ctypes.windll.kernel32.UnmapViewOfFile(local_sd)
        k32.CloseHandle(hMap)
        k32.CloseHandle(hproc)
        return ""

    # Set ready flag BEFORE loading DLL
    sd.ready = 1

    # Create remote thread to load our DLL
    hthread = k32.CreateRemoteThread(hproc, None, 0, ctypes.c_void_p(load_lib),
                                      ctypes.c_void_p(remote_path), 0, None)
    if not hthread:
        k32.VirtualFreeEx(hproc, ctypes.c_void_p(remote_path), 0, MEM_RELEASE)
        ctypes.windll.kernel32.UnmapViewOfFile(local_sd)
        k32.CloseHandle(hMap)
        k32.CloseHandle(hproc)
        return ""

    # Wait for DLL to finish reading (max 5 seconds)
    for _ in range(50):  # 50 * 100ms = 5s
        import time
        time.sleep(0.1)
        if sd.done:
            break

    result = sd.password if sd.password else ""

    # Cleanup
    k32.WaitForSingleObject(hthread, 1000)
    k32.VirtualFreeEx(hproc, ctypes.c_void_p(remote_path), 0, MEM_RELEASE)
    k32.CloseHandle(hthread)
    k32.CloseHandle(hproc)
    ctypes.windll.kernel32.UnmapViewOfFile(local_sd)
    k32.CloseHandle(hMap)

    return result

# ========== UI Components ==========
class EyeWidget(tk.Canvas):
    """Draggable eye icon"""
    def __init__(self, parent, on_drop):
        super().__init__(parent, width=72, height=72, bg=CLR_BG, highlightthickness=0, cursor="fleur")
        self._on_drop = on_drop
        self._drag = False
        self._float = None
        self._last_hwnd = 0
        self._last_rc = None
        self._last_color = None
        self._pid = k32.GetCurrentProcessId()
        self._paint(CLR_ACCENT)
        self.bind("<ButtonPress-1>", self._start)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._end)
        self._timer_id = None

    def _paint(self, color):
        self.delete("all")
        self.create_oval(4, 4, 68, 68, fill=color, outline="")
        self.create_oval(14, 24, 58, 48, fill="white", outline="")
        self.create_oval(28, 28, 44, 44, fill=color, outline="")
        self.create_oval(32, 32, 40, 40, fill="white", outline="")

    def _repaint_highlight(self):
        """定时器回调：重新绘制高亮"""
        if not self._drag or not self._last_rc or not self._last_color:
            return
        draw_rect(self._last_rc, self._last_color, 3)
        self._timer_id = self.after(50, self._repaint_highlight)

    def _start(self, e):
        self._drag = True
        self._paint("#7c3aed")
        # 浮动窗口放在左上角远处，不遮挡鼠标位置的窗口检测
        self._float = tk.Toplevel()
        self._float.overrideredirect(True)
        self._float.attributes("-topmost", True)
        self._float.attributes("-alpha", 0.7)
        self._float.config(bg="#7c3aed")
        self._float.geometry("28x28+-50+-50")
        fc = tk.Canvas(self._float, width=28, height=28, bg="#7c3aed", highlightthickness=0)
        fc.pack()
        fc.create_oval(4, 4, 24, 24, fill="white", outline="")
        fc.create_oval(10, 10, 18, 18, fill="#7c3aed", outline="")

    def _move(self, e):
        if not self._drag:
            return
        x, y = cursor_pos()
        # 不再移动浮动窗口，让它待在远处不干扰检测
        h = find_window_at(x, y, self._pid)
        if h != self._last_hwnd:
            # 擦除旧高亮
            if self._last_rc:
                erase_rect(self._last_rc)
                self._last_rc = None
            self._last_color = None
            self._last_hwnd = h
            if h:
                rc = win_rect(h)
                pwd = is_password_field(h)
                self._last_rc = rc
                self._last_color = CLR_SUCCESS if pwd else CLR_DANGER
                draw_rect(self._last_rc, self._last_color, 3)
                self._paint("#6ee7b7" if pwd else "#7c3aed")
                # 启动定时器持续重绘
                if self._timer_id:
                    self.after_cancel(self._timer_id)
                self._timer_id = self.after(50, self._repaint_highlight)
            else:
                self._paint("#7c3aed")

    def _end(self, e):
        if not self._drag:
            return
        self._drag = False
        # 停止定时器
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        if self._float and self._float.winfo_exists():
            self._float.destroy()
        self._float = None
        if self._last_rc:
            erase_rect(self._last_rc)
            self._last_rc = None
        self._last_color = None
        self._last_hwnd = 0
        self._paint(CLR_ACCENT)
        x, y = cursor_pos()
        self.after(50, lambda: self._on_drop(x, y))

# ========== Main App ==========
def main():
    root = tk.Tk()
    root.title("星号密码查看器--by Owl")
    root.geometry("520x440")
    root.resizable(False, False)
    root.configure(bg=CLR_BG)

    # Set window icon
    import os
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "星号.png")
    if os.path.exists(icon_path):
        icon_img = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_img)

    # Title bar
    title_frame = tk.Frame(root, bg=CLR_CARD, height=56)
    title_frame.pack(fill=tk.X)
    tk.Label(root, text=" 星号密码查看器-Owl", bg=CLR_CARD, fg=CLR_TEXT,
             font=("微软雅黑", 14, "bold")).place(x=0, y=0, width=520, height=56)

    # Topmost checkbox (top-right of title bar)
    topmost_var = tk.BooleanVar(value=True)
    def toggle_topmost():
        root.attributes("-topmost", topmost_var.get())
    cb_topmost = tk.Checkbutton(root, text="置顶", bg=CLR_CARD, fg=CLR_MUTED,
                                 activebackground=CLR_CARD, activeforeground=CLR_TEXT,
                                 selectcolor=CLR_CARD, font=("微软雅黑", 9),
                                 variable=topmost_var, command=toggle_topmost,
                                 highlightthickness=0)
    cb_topmost.place(x=430, y=16)

    body = tk.Frame(root, bg=CLR_BG, padx=24, pady=16)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(body, text="拖动眼睛图标到密码框上，松开查看明文",
             bg=CLR_BG, fg=CLR_MUTED, font=("微软雅黑", 10)).pack(anchor=tk.W)
    tk.Frame(body, bg=CLR_BORDER, height=1).pack(fill=tk.X, pady=(8, 14))

    plain = [""]

    def on_drop(x, y):
        h = find_window_at(x, y, k32.GetCurrentProcessId())
        if not h:
            show("", "未找到窗口", True)
            return
        if not is_password_field(h):
            show("", f"不是密码框 [{win_class(h)}]", True)
            return
        pwd = read_password(h)
        if pwd:
            show(pwd, "读取成功")
        else:
            show("", "获取失败 (目标有保护)", True)

    def show(text, msg, err=False):
        plain[0] = text
        var.set(text)
        status.config(text=msg, fg=CLR_DANGER if err else CLR_SUCCESS)
        if text:
            ph.place_forget()
        else:
            ph.place(relx=0, rely=0.5, anchor=tk.W, x=8)

    def copy_clipboard():
        if plain[0]:
            root.clipboard_clear()
            root.clipboard_append(plain[0])
            status.config(text="已复制", fg=CLR_SUCCESS)

    def clear():
        plain[0] = ""
        var.set("")
        status.config(text="")
        ph.place(relx=0, rely=0.5, anchor=tk.W, x=8)

    # Eye + instructions
    row = tk.Frame(body, bg=CLR_BG)
    row.pack(fill=tk.X)
    eye = EyeWidget(row, on_drop)
    eye.pack(side=tk.LEFT)

    info = tk.Frame(row, bg=CLR_BG, padx=16)
    info.pack(side=tk.LEFT, fill=tk.Y)
    tk.Label(info, text="操作说明", bg=CLR_BG, fg=CLR_TEXT, font=("微软雅黑", 10, "bold")).pack(anchor=tk.W)
    for i, t in enumerate(["按住眼睛图标", "拖到密码输入框", "看到绿色边框", "松开读取密码"], 1):
        tk.Label(info, text=f"{i}. {t}", bg=CLR_BG, fg=CLR_MUTED, font=("微软雅黑", 9)).pack(anchor=tk.W, pady=1)

    tk.Frame(body, bg=CLR_BORDER, height=1).pack(fill=tk.X, pady=14)

    # Result
    rh = tk.Frame(body, bg=CLR_BG)
    rh.pack(fill=tk.X)
    tk.Label(rh, text="检测结果", bg=CLR_BG, fg=CLR_TEXT, font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
    status = tk.Label(rh, text="", bg=CLR_BG, fg=CLR_MUTED, font=("微软雅黑", 8))
    status.pack(side=tk.RIGHT)

    ef = tk.Frame(body, bg=CLR_ENTRY, highlightbackground=CLR_BORDER, highlightthickness=1)
    ef.pack(fill=tk.X, pady=(6, 0))
    var = tk.StringVar()
    tk.Entry(ef, textvariable=var, font=("Consolas", 14), bg=CLR_ENTRY, fg=CLR_SUCCESS,
             insertbackground=CLR_TEXT, relief=tk.FLAT, bd=10, state="readonly",
             readonlybackground=CLR_ENTRY).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ph = tk.Label(ef, text="等待检测...", bg=CLR_ENTRY, fg=CLR_MUTED, font=("微软雅黑", 10), padx=10)
    ph.place(relx=0, rely=0.5, anchor=tk.W, x=8)

    # Buttons
    bf = tk.Frame(body, bg=CLR_BG, pady=10)
    bf.pack(fill=tk.X)

    def make_btn(parent, text, cmd):
        f = tk.Frame(parent, bg=CLR_ACCENT, cursor="hand2")
        f.pack(side=tk.LEFT)
        l = tk.Label(f, text=text, bg=CLR_ACCENT, fg=CLR_TEXT, font=("微软雅黑", 10, "bold"), padx=20, pady=8)
        l.pack()
        l.bind("<ButtonPress-1>", lambda e: (f.config(bg="#2d6fd4"), l.config(bg="#2d6fd4")))
        l.bind("<ButtonRelease-1>", lambda e: (f.config(bg=CLR_ACCENT), l.config(bg=CLR_ACCENT), cmd()))
        l.bind("<Enter>", lambda e: (f.config(bg="#3d7fe4"), l.config(bg="#3d7fe4")))
        l.bind("<Leave>", lambda e: (f.config(bg=CLR_ACCENT), l.config(bg=CLR_ACCENT)))

    make_btn(bf, "复制密码", copy_clipboard)
    make_btn(bf, "清空结果", clear)

    root.mainloop()

if __name__ == "__main__":
    main()
