#include <winsock2.h>
#include <ws2tcpip.h>
#include <iostream>
#include <fstream>
#include <vector>

#pragma comment(lib, "ws2_32.lib")

#define PORT 3558
#define BUFFER_SIZE 1024

int main() {
    WSADATA wsaData;
    SOCKET listening, clientSocket;
    sockaddr_in server, client;
    char buffer[BUFFER_SIZE];

    // Initialize Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsaData)) {
        std::cerr << "WSAStartup failed\n";
        return 1;
    }

    // Create socket
    listening = socket(AF_INET, SOCK_STREAM, 0);
    if (listening == INVALID_SOCKET) {
        std::cerr << "Failed to create socket\n";
        WSACleanup();
        return 1;
    }

    // Bind socket
    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(PORT);

    if (bind(listening, (sockaddr*)&server, sizeof(server)) == SOCKET_ERROR) {
        std::cerr << "Bind failed\n";
        closesocket(listening);
        WSACleanup();
        return 1;
    }

    // Listen
    listen(listening, SOMAXCONN);
    std::cout << "Server listening on port " << PORT << "...\n";

    while (true) {
        int clientSize = sizeof(client);
        clientSocket = accept(listening, (sockaddr*)&client, &clientSize);

        if (clientSocket == INVALID_SOCKET) {
            std::cerr << "Client accept failed\n";
            continue;
        }

        std::vector<char> fullMessage;
        int bytesReceived;

        while ((bytesReceived = recv(clientSocket, buffer, BUFFER_SIZE, 0)) > 0) {
            fullMessage.insert(fullMessage.end(), buffer, buffer + bytesReceived);
        }

        // Save (overwrite) received message
        if (!fullMessage.empty()) {
            std::ofstream outFile("received_messages.txt", std::ios::trunc | std::ios::binary);
            outFile.write(fullMessage.data(), fullMessage.size());
            outFile.close();

            std::cout << "Message received and saved (overwritten).\n";
        }

        closesocket(clientSocket); // Ready for next
    }

    // Never reached (but good practice)
    closesocket(listening);
    WSACleanup();
    return 0;
}
