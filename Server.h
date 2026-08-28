#pragma once

#include <QObject>
#include <QTcpServer>
#include <QTcpSocket>
#include <QHostAddress>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QThread>
#include <QList>
#include <QHash>
#include <QPair>
#include <QDebug>

using ClientData = QPair<QTcpSocket*, QThread*>;            // 客户端数据
using ClientInfo = QHash<QString, ClientData>;              // 客户端
using onlineInfo = QHash<QString, QList<QJsonObject>>;      // 离线消息

class Server : public QObject {
    Q_OBJECT
public:
    Server(QObject* parent = nullptr);
public:
    /* 初始化连接API */
    void lisen_ipconfig(const QHostAddress& address = QHostAddress::Any, quint16 port = 8888);
    bool initMysqlConnect(void);
private:
    void onNewConnection(void);
    QByteArray msgErrorSned(QString error);
    bool loadEnable_as_Disable(QString userName, QString password);
    bool is_friend(QString friendName, QString userName);
    qint64 getId(QString name);
    QString getUserName(int id);
    QJsonArray getfriendList(int userId);
private:
    void ReadyReadData_Slots_Handler(QTcpSocket* client);
    bool deleteUser_as_registrationUser(QString userName, QString password, bool flag);
    void sendJson(QTcpSocket* client, const QJsonObject& json);
    void setloadStatus(int id, bool status);
    bool is_userName_Status(QString userName);
private:
    QTcpServer* server = nullptr;
    ClientInfo m_clients;
    onlineInfo info;
    QSqlDatabase db = QSqlDatabase::addDatabase("QMYSQL");
    bool is_mysql_connect = false;
};