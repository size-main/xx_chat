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
    if (!client)
    {
        return;
    }

    QByteArray& buffer = this->m_receiveBuffers[client];
    buffer.append(client->readAll());

    while (buffer.size() >= 8)
    {
        uint16_t header = (static_cast<uint8_t>(buffer[0]) << 8) | static_cast<uint8_t>(buffer[1]);

        if (header != 0xA1A2)
        {
            buffer.remove(0, 1);
            continue;
        }

        uint32_t bodyLength = (static_cast<uint8_t>(buffer[2]) << 24) | (static_cast<uint8_t>(buffer[3]) << 16) | 
                              (static_cast<uint8_t>(buffer[4]) << 8) | static_cast<uint8_t>(buffer[5]);

        const int packetSize = 2 + 4 + bodyLength + 2;

        if (buffer.size() < packetSize)
        {
            return;
        }

        uint16_t tail = (static_cast<uint8_t>(buffer[packetSize - 2]) << 8) | static_cast<uint8_t>(buffer[packetSize - 1]);

        if (tail != 0xB1B2)
        {
            buffer.remove(0, 1);
            continue;
        }

        QByteArray body = buffer.mid(6, bodyLength);
        buffer.remove(0, packetSize);

        QJsonParseError error;
        QJsonDocument dataJson =
            QJsonDocument::fromJson(body, &error);

        if (error.error != QJsonParseError::NoError || !dataJson.isObject())
        {
            qDebug() << "JSON parse error:" << error.errorString();
            continue;
        }

        QJsonObject jsonObj = dataJson.object();
        QString type = jsonObj["type"].toString();

        if (type_thread_handler.contains(type))
        {
            type_thread_handler[type](client, jsonObj);
        } else {
            qDebug() << "type" << type << "error";
        }
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
    this->type_thread_handler["delete friend"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->deleteFriend_type_hanlder(client, json); };
    this->type_thread_handler["file"] = [this] (QTcpSocket*& client, QJsonObject& json) { this->file_type_handler(client, json); };
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

void Server::deleteFriend_type_hanlder(QTcpSocket*& client, QJsonObject& jsonObj)
{
    QString userName = jsonObj["userName"].toString();
    QString friendName = jsonObj["friendName"].toString();

    if (this->db.deleteFriend(userName, friendName))
    {
        if (this->m_clients.contains(friendName))
        {
            QJsonObject data;

            data["type"] = "delete friend";
            data["friendName"] = userName;
            this->sendJson(this->m_clients[friendName].first, data);
        }
    }
}

void Server::file_type_handler(QTcpSocket*& client, QJsonObject& json)
{
    QJsonObject data;
    QString userName = json["friendName"].toString();

    data["type"] = "file";
    data["friendName"] = json["userName"].toString();
    data["fileName"] = json["fileName"].toString();
    data["fileData"] = json["fileData"];
    if (this->m_clients.contains(userName))
    {
        /* 好友在线就直接发送 */
        QTcpSocket* socket = this->m_clients.value(userName).first;
        this->sendJson(socket, data);
        socket->flush();
    } else {
        /* 证明不在线, 保留数据缓存等下上线再发送 */
        QString name = json["friendName"].toString();

        if (!this->info.contains(name))
        {
            /* 没存在过离线消息, 新建链表串连消息 */
            QList<QJsonObject> list;
            list.append(data);
            this->info.insert(name, list);
        } else {
            /* 存在离线消息, 直接在链表上添加元素 */
            this->info.value(name).toList().append(data);
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
