#pragma once

#include <QObject>
#include <QTcpServer>
#include <QTcpSocket>
#include <QHostAddress>
#include <QThread>
#include <QJsonObject>
#include <QHash>
#include <QDebug>
#include "DatabaseManager.h"

using ClientData = QPair<QTcpSocket*, QThread*>;                                                    // 客户端数据
using ClientInfo = QHash<QString, ClientData>;                                                      // 客户端
using ClinetInfotype = QHash<QTcpSocket*, QString>;                                                 // 反哈希
using onlineInfo = QHash<QString, QList<QJsonObject>>;                                              // 离线消息
using type_function_Info = QHash<QString, std::function<void (QTcpSocket*&, QJsonObject&)>>;        // 通过消息类型调用不同的回调函数

class Server : public QTcpServer {
    Q_OBJECT
public:
    Server(QObject* parent = nullptr);
protected:
    void incomingConnection(qintptr socketDescriptor) override;
private:
    void onNewConnection(void);
    void disConnection(void);
    void ReadyRead_Thread(void);
    void init_type_hash(void);
private:
    void load_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void msg_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void registration_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void loading_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void friend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void loadend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void loadfriend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void appendFriend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj);
    void deleteFriend_type_hanlder(QTcpSocket*& client, QJsonObject& jsonObj);
    void file_type_handler(QTcpSocket*& client, QJsonObject& json);
private:
    void sendJson(QTcpSocket* client, const QJsonObject& json);
private:
    DatabaseManager db;
    ClientInfo m_clients;
    ClinetInfotype online_Client;
    onlineInfo info;
    QHash<QTcpSocket*, QByteArray> m_receiveBuffers;
    type_function_Info type_thread_handler;
};