# 密码星号探测器-Owl

将眼睛图标拖到密码输入框上，自动识别并读取星号密码明文。

## 功能

- 拖动眼睛图标到任意密码框，松开即读取明文
- 自动识别密码字段（绿色边框 = 密码框，紫色边框 = 非密码框）
- 支持 32位 和 64位 程序
- 一键复制密码到剪贴板
- 窗口置顶功能（默认开启）

## 使用方法

1. 双击 `星号探测器-Owl.exe` 启动程序
2. 按住界面上的**眼睛图标**
3. **拖动**到目标密码输入框上
4. 看到**绿色边框**后松开鼠标
5. 密码明文显示在结果框中
6. 点击**复制密码**按钮即可复制

## 技术原理

使用 `SetWindowsHookEx` 将 DLL 注入到目标进程，在目标进程内部调用 `GetWindowTextW` / `SendMessage WM_GETTEXT` 读取密码控件内容，通过 PE 共享节（`#pragma data_seg`）将数据传回主程序。

### 架构适配

| 目标程序 | 注入方式 | DLL |
|---------|---------|-----|
| 32位程序 | load_hook32.exe → hook_reader32.dll | 32位 |
| 64位程序 | load_hook64.exe → hook_reader.dll | 64位 |

程序自动通过 `IsWow64Process` 检测目标进程架构并选择对应的加载器。

## 打包

```bat
build.bat
```

依赖：Python 3.10+、PyInstaller

打包产物：`dist\星号探测器-Owl.exe`（单文件，约9.5MB）

## 项目文件

| 文件 | 说明 |
|------|------|
| `password_viewer.py` | 主程序（GUI + 逻辑） |
| `hook_reader.c` / `hook_reader.dll` | 64位密码读取DLL |
| `hook_reader32.c` / `hook_reader32.dll` | 32位密码读取DLL |
| `load_hook32.c` / `load_hook32.exe` | 32位加载器 |
| `load_hook64.c` / `load_hook64.exe` | 64位加载器 |
| `icon.ico` / `星号.png` | 图标 |
| `build.bat` | 一键打包脚本 |

## 注意

- 仅用于学习和安全测试，请勿用于非法用途
- 部分程序可能有额外保护（如银行客户端、密码管理器），可能无法读取
- 建议以管理员权限运行以提高兼容性
