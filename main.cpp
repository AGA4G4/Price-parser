#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <string>

#pragma comment(lib, "ws2_32.lib")


// Constants
#define WINDOW_WIDTH      500
#define WINDOW_HEIGHT     400
#define ID_INPUT_FIELD    101
#define ID_SEND_BUTTON    102

// Global socket
SOCKET clientSocket = INVALID_SOCKET;

// Function declarations
LRESULT CALLBACK WindowProc(HWND, UINT, WPARAM, LPARAM);
bool ConnectToServer();
void SendData(HWND);

// Entry point for GUI application
int APIENTRY wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR lpCmdLine, int nCmdShow) {
    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData)) {
        MessageBoxW(NULL, L"WSAStartup failed.", L"Error", MB_ICONERROR);
        return 1;
    }

    // Register window class
    const wchar_t CLASS_NAME[] = L"UnicodeClientClass";

    WNDCLASS wc = {};
    wc.lpfnWndProc   = WindowProc;
    wc.hInstance     = hInstance;
    wc.lpszClassName = CLASS_NAME;

    if (!RegisterClass(&wc)) {
        MessageBoxW(NULL, L"Window registration failed.", L"Error", MB_ICONERROR);
        WSACleanup();
        return 1;
    }

    // Create main window
    HWND hwnd = CreateWindowEx(
        0,
        CLASS_NAME,
        L"Unicode TCP Client",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        WINDOW_WIDTH, WINDOW_HEIGHT,
        NULL,
        NULL,
        hInstance,
        NULL
    );

    if (hwnd == NULL) {
        MessageBoxW(NULL, L"Window creation failed.", L"Error", MB_ICONERROR);
        WSACleanup();
        return 1;
    }

    ShowWindow(hwnd, nCmdShow);

    // Message loop
    MSG msg = {};
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    // Cleanup
    if (clientSocket != INVALID_SOCKET) {
        closesocket(clientSocket);
    }
    WSACleanup();
    return 0;
}

// Window Procedure
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    static HWND hEdit;

    switch (uMsg) {
        case WM_CREATE:
        {
            // Multiline input field with scrollbars
            hEdit = CreateWindowEx(
                WS_EX_CLIENTEDGE,
                L"EDIT",
                L"",
                WS_VISIBLE | WS_CHILD | WS_BORDER |
                ES_LEFT | ES_MULTILINE | ES_WANTRETURN | WS_VSCROLL,
                20, 20, 440, 300,
                hwnd,
                (HMENU)ID_INPUT_FIELD,
                NULL,
                NULL
            );

            // Send button
            CreateWindow(
                L"BUTTON",
                L"Send",
                WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                20, 330, 100, 30,
                hwnd,
                (HMENU)ID_SEND_BUTTON,
                NULL,
                NULL
            );

            // Try to connect on startup
            while (!ConnectToServer()) {
                int result = MessageBoxW(hwnd, L"Failed to connect to server. Retry?", L"Connection Error", MB_RETRYCANCEL | MB_ICONWARNING);
                if (result != IDRETRY) {
                    PostQuitMessage(0);
                    return 0;
                }
            }
        }
        break;

        case WM_COMMAND:
            if (LOWORD(wParam) == ID_SEND_BUTTON) {
                SendData(hEdit);
            }
            break;

        case WM_DESTROY:
            PostQuitMessage(0);
            break;

        default:
            return DefWindowProc(hwnd, uMsg, wParam, lParam);
    }
    return 0;
}

// Connect to the server
bool ConnectToServer() {
    if (clientSocket != INVALID_SOCKET) {
        closesocket(clientSocket); // Prevent leaks
    }

    clientSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (clientSocket == INVALID_SOCKET) {
        return false;
    }

    sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons(3558);
    server.sin_addr.s_addr = inet_addr("192.168.1.56"); // Your server IP

    if (connect(clientSocket, (sockaddr*)&server, sizeof(server)) == SOCKET_ERROR) {
        closesocket(clientSocket);
        clientSocket = INVALID_SOCKET;
        return false;
    }

    return true;
}

// Send data to server
void SendData(HWND hEdit) {
    // Auto-reconnect if disconnected
    if (clientSocket == INVALID_SOCKET) {
        if (!ConnectToServer()) {
            MessageBoxW(NULL, L"Not connected to server.", L"Error", MB_ICONWARNING);
            return;
        }
    }

    int length = GetWindowTextLengthW(hEdit);
    if (length <= 0) {
        MessageBoxW(NULL, L"Input is empty.", L"Error", MB_ICONWARNING);
        return;
    }

    // Get text from edit control
    std::wstring wbuffer(length + 1, L'\0');
    GetWindowTextW(hEdit, wbuffer.data(), length + 1);

    // Convert to UTF-8
    int size = WideCharToMultiByte(CP_UTF8, 0, wbuffer.c_str(), -1, NULL, 0, NULL, NULL);
    std::string utf8buffer(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, wbuffer.c_str(), -1, utf8buffer.data(), size, NULL, NULL);

    // Send and signal end of message
    if (send(clientSocket, utf8buffer.c_str(), utf8buffer.size(), 0) == SOCKET_ERROR) {
        MessageBoxW(NULL, L"Failed to send data.", L"Error", MB_ICONERROR);
        closesocket(clientSocket);
        clientSocket = INVALID_SOCKET;
    } else {
        SetWindowTextW(hEdit, L"");         // Clear input
        shutdown(clientSocket, SD_SEND);    // Signal "done sending"
        ConnectToServer();                  // Reconnect for next message
    }
}