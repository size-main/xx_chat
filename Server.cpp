#include "Server.h"
#include <QJsonDocument>

Server::Server(QObject* parent)
    : QObject(parent)
{
    server = new QTcpServer(this);
    server->listen(QHostAddress::Any, 8888);
    this->init_type_hash();
    connect(server, &QTcpServer::newConnection, this, &Server::onNewConnection);
}

void Server::onNewConnection(void)
{
    QTcpSocket* client = this->server->nextPendingConnection();

    if (client)
    {
        connect(client, &QTcpSocket::disconnected, this, &Server::disConnection);
        connect(client, &QTcpSocket::readyRead, this, &Server::ReadyRead_Thread);
    } else {
        qDebug() << "错误连接" << Qt::endl;
    }
}

void Server::disConnection(void)
{
    QTcpSocket* client = qobject_cast<QTcpSocket*>(sender());
    if(!client) return; 
    if (this->online_Client.contains(client))
    {
        QString userName = this->online_Client[client];
        auto obj = this->m_clients[userName];
        delete obj.second;
        this->db.setusersStatus(userName, false);
        this->m_clients.remove(userName);
        this->online_Client.remove(client);
    }
    client->deleteLater();
}

void Server::ReadyRead_Thread(void)
{
    QTcpSocket* client = qobject_cast<QTcpSocket*>(sender());
    if(!client) return;
    QByteArray data = client->readAll();

    if(data.size() < 8)
    return;

    int totalSize = data.size();
    uint16_t header = (static_cast<uint8_t>(data[0]) << 8) | static_cast<uint8_t>(data[1]);
    uint8_t tailHigh = static_cast<uint8_t>(data[totalSize - 2]);
    uint8_t tailLow  = static_cast<uint8_t>(data[totalSize - 1]);
    uint16_t tail = (tailHigh << 8) | tailLow;

    data.remove(0,2);
    data.chop(2);

    if(data.size() <4) return;
    QByteArray lenBuf = data.first(4);
    uint32_t bodyLength = (static_cast<uint8_t>(lenBuf[0]) << 24) | (static_cast<uint8_t>(lenBuf[1]) << 16) |
                          (static_cast<uint8_t>(lenBuf[2]) << 8) | (static_cast<uint8_t>(lenBuf[3]));
    data.remove(0,4); 

    if (header != 0XA1A2 && tail != 0XB1B2 && bodyLength != data.size())
    {
        qDebug() << "data is not";
        return;
    }

    QJsonDocument dataJson = QJsonDocument::fromJson(data);

    if (dataJson.isEmpty())
    {
        qDebug() << "data is empty";
        return;
    }
    QJsonObject jsonObj = dataJson.object();
    QString type = jsonObj["type"].toString();

    if (type_thread_handler.contains(type))
    {
        auto func_type_handler = type_thread_handler[type];
        func_type_handler(client, jsonObj);
    } else {
        qDebug() << "type" << type << "error" << Qt::endl;
    }
}

void Server::init_type_hash(void)
{
    this->type_thread_handler["load"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->load_type_handler(client, json); };
    this->type_thread_handler["loading"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->loading_type_handler(client, json); };
    this->type_thread_handler["msg"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->msg_type_handler(client, json); };
    this->type_thread_handler["friend"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->friend_type_handler(client, json); };
    this->type_thread_handler["loadend"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->loadend_type_handler(client, json); };
    this->type_thread_handler["loadfriend"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->loadfriend_type_handler(client, json); };
    this->type_thread_handler["append friend"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->appendFriend_type_handler(client, json); };
    this->type_thread_handler["registration"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->registration_type_handler(client, json); };
}

void Server::load_type_handler(QTcpSocket*& client, QJsonObject& json)
{
    QString userName = json["userName"].toString();
    QString password = json["password"].toString();
    
    if (db.load_userName(userName, password))
    {
        if (this->m_clients.contains(userName))
        {
            QJsonObject loadJson;

            loadJson["type"] = "load";
            loadJson["status"] = "id is online";

            this->sendJson(client, loadJson);               // 不允许重复登录
            return;
        }
        QJsonObject loadJson;

        loadJson["type"] = "load";
        loadJson["status"] = "enable";
        this->sendJson(client, loadJson);

        QThread* thread = new QThread();
        auto infoData = qMakePair(client, thread);

        client->moveToThread(thread);
        this->m_clients.insert(userName, infoData);
        this->db.setusersStatus(userName, true);
    }
}

void Server::msg_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    QString friendName = jsonObj["friendName"].toString();
    QString userName = jsonObj["userName"].toString();
    QString msgData = jsonObj["data"].toString();
    QJsonObject sendJson;

    (void)client;

    sendJson["type"] = "msg";
    sendJson["friendName"] = userName;
    sendJson["data"] = jsonObj["data"].toString();

    if (this->m_clients.contains(friendName))
    {
        /* 好友在线就直接发送 */
        QTcpSocket* socket = this->m_clients.value(friendName).first;
        this->sendJson(socket, sendJson);
        socket->flush();
    } else {
        /* 证明不在线, 保留数据缓存等下上线再发送 */
        QString name = jsonObj["friendName"].toString();

        if (!this->info.contains(name))
        {
            /* 没存在过离线消息, 新建链表串连消息 */
            QList<QJsonObject> list;
            list.append(sendJson);
            this->info.insert(name, list);
        } else {
            /* 存在离线消息, 直接在链表上添加元素 */
            this->info.value(name).toList().append(sendJson);
        }
    }
}

void Server::registration_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    QString userName = jsonObj["userName"].toString();
    QString password = jsonObj["password"].toString();

    if (this->db.get_users_is_none(userName))
    {
        QJsonObject sendJson;

        sendJson["type"] = "registration";
        sendJson["data"] = false;
        sendJson["error"] = "The account has already been registered";
        this->sendJson(client, sendJson);
    } else {
        QJsonObject sendJson;
        
        sendJson["type"] = "registration";
        sendJson["error"] = "server error";
        sendJson["data"] = this->db.registrationUser(userName, password);
        this->sendJson(client, sendJson);
    }
}

void Server::loading_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    QString userName = jsonObj["userName"].toString();
    QJsonObject loadingJson;

    loadingJson["type"] = "friendIds";
    loadingJson["data"] = this->db.getFriendList(userName);

    qDebug() << "friendsIdLists:" << loadingJson["data"].toArray() << Qt::endl;
    this->sendJson(client, loadingJson);
    client->flush();
}

void Server::friend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    int friendId = jsonObj["data"].toInt();
    QString friendName = this->db.is_id_to_userName(friendId);
    QJsonObject sendJson;

    sendJson["type"] = "friend";
    sendJson["data"] = friendName;
    this->sendJson(client, sendJson);
    client->flush();
}

void Server::loadend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    const QString userName = jsonObj["userName"].toString();

    if (this->info.contains(userName)) 
    {
        const auto list = this->info.value(userName).toList();

        for (const auto& item : list) 
        {
            this->sendJson(client, item);
        }
        this->info.remove(userName);
        client->flush();
    }
}

void Server::loadfriend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    QJsonArray data = this->db.loadFriend(jsonObj["data"].toString());
    QJsonObject sendJson;

    sendJson["type"] = "loadfriend";
    sendJson["data"] = data;

    qDebug() << sendJson;
    this->sendJson(client, sendJson);
    client->flush();
}

void Server::appendFriend_type_handler(QTcpSocket*& client, QJsonObject& jsonObj)
{
    QString userName = jsonObj["userName"].toString();
    QString friendName = jsonObj["friendName"].toString();
    QJsonObject sendJson;

    sendJson["type"] = "append friend";
    sendJson["status"] = this->db.appnedFriend(userName, friendName);
    sendJson["friendName"] = friendName;
    sendJson["data"] = sendJson["status"].toBool() ? "添加成功" : "添加失败";
    this->sendJson(client, sendJson);
    if (sendJson["status"].toBool())
    {
        if (this->m_clients.contains(friendName))
        {
            QTcpSocket* socket = this->m_clients[friendName].first;
            sendJson["friendName"] = userName;
            sendJson["type"] = "add friend";
            this->sendJson(socket, sendJson);
            socket->flush();
        }
    }
}

void Server::sendJson(QTcpSocket* client, const QJsonObject& json)
{
    QByteArray body = QJsonDocument(json).toJson(QJsonDocument::Compact);
    quint32 length = static_cast<quint32>(body.size());

    QByteArray packet;
    QDataStream stream(&packet, QIODevice::WriteOnly);
    stream.setByteOrder(QDataStream::BigEndian);

    stream << quint16(0xA1A2);
    stream << quint32(length);
    stream.writeRawData(body.constData(), body.size());
    stream << quint16(0xB1B2);

    qDebug() << packet;
    client->write(packet);
}
