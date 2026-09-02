#include "Server.h"
#include <QSqlError>

Server::Server(QObject* parent)
    : QObject(parent)
{
    server = new QTcpServer(this);
}

void Server::lisen_ipconfig(const QHostAddress& address, quint16 port)
{
    server->listen(address, 8888);
    connect(server, &QTcpServer::newConnection, this, &Server::onNewConnection);
}

bool Server::initMysqlConnect(void)
{
    this->db.setHostName("127.0.0.1");
    this->db.setPort(3306);
    this->db.setDatabaseName("chat_server");
    this->db.setUserName("root");
    this->db.setPassword("root");

    return db.open();
}

void Server::onNewConnection(void)
{
    QTcpSocket* client = server->nextPendingConnection();
    
    if (client)
    {
        ClientInfo info;
        QString clientIp = client->peerAddress().toString();
        connect(client, &QTcpSocket::disconnected, [this, client]() {
            for (auto it = this->m_clients.constBegin(); it != this->m_clients.constEnd(); ++it) 
            {
                ClientData itm = it.value();
                if (itm.first == client)
                {
                    delete itm.second;
                    this->m_clients.erase(it);
                    break;
                }
            }
            client->deleteLater();
        });
        connect(client, &QTcpSocket::readyRead, [this, client] () {
            this->ReadyReadData_Slots_Handler(client);
        });
    }
}

QByteArray Server::msgErrorSned(QString error)
{
    QJsonObject retJson;

    retJson["type"] = "error";
    retJson["msg"] = "json error";
    QJsonDocument tempJson(retJson);

    return tempJson.toJson();
}

bool Server::loadEnable_as_Disable(QString userName, QString password)
{
    if (userName.isEmpty() || password.isEmpty())
    {
        return false;
    }
    QSqlQuery query(this->db);
    query.prepare(R"(
        SELECT id, account
        FROM users
        WHERE account = :account
        AND password = :password
    )");
    query.bindValue(":account", userName);
    query.bindValue(":password", password);
    if (!query.exec())
    {
        return false;
    }
    if (query.next())
    {
        int userId = query.value("id").toInt();
        qDebug() << "登录成功:" << userId;

        this->setloadStatus(userId, true);
        return true;
    }

    return false;
}

bool Server::is_friend(QString friendName, QString userName)
{
    if (friendName.isEmpty() || userName.isEmpty())
    {
        return false;
    }
    quint64 friendId = this->getId(friendName);
    quint64 userId = this->getId(userName);
    QSqlQuery query;
    query.prepare(
        "SELECT friendId"
    );
    query.bindValue(":userId", userId);
    query.bindValue(":friendId", friendId);
    
    if (!query.exec())
    {
        return false;
    }
    if (query.next())
    {
        return true;
    }

    return false;
}

qint64 Server::getId(QString name)
{
    QSqlQuery query(this->db);

    query.prepare("SELECT id FROM users WHERE account = :account;");
    query.bindValue(":account", name);
    if (!query.exec())
    {
        return -1;
    }
    if (query.next())
    {
        const qint64 userId = query.value("id").toLongLong();
        return userId;
    }

    return -1;
}

QString Server::getUserName(int id)
{
    if (id <= 0)
    {
        qDebug() << "id不合法" << Qt::endl;
        return "";
    }
    QSqlQuery query;

    query.prepare("SELECT account FROM users WHERE id = :user_id");
    query.bindValue(":user_id", id);

    if (!query.exec())
    {
        qDebug() << "查询失败";
        return "";
    }
    if (query.next())
    {
        return query.value("account").toString();
    }
    return "";
}

QJsonArray Server::getfriendList(int userId)
{
    QSqlQuery query;
    QJsonArray retList;

    query.prepare(
        "SELECT friend_id "
        "FROM friends "
        "WHERE user_id = :userId"
    );

    query.bindValue(":userId", userId);

    if (!query.exec())
    {
        qDebug() << "查询好友失败:" << query.lastError().text();
        return retList;
    }

    qDebug() << "查询到好友" << Qt::endl;

    while (query.next())
    {
        retList.append(query.value("friend_id").toInt());
    }

    return retList;
}

void Server::ReadyReadData_Slots_Handler(QTcpSocket* client)
{
    QByteArray data = client->readAll();
    QJsonDocument dataJson = QJsonDocument::fromJson(data);

    if (dataJson.isEmpty())
    {
        client->write(this->msgErrorSned("json error"));
        return;
    }

    QJsonObject jsonObj = dataJson.object();
    QString type = jsonObj["type"].toString();

    if (type == "load")
    {
        if (this->loadEnable_as_Disable(jsonObj["userName"].toString(), jsonObj["password"].toString()))
        {
            if (this->m_clients.contains(jsonObj["userName"].toString()))
            {
                QJsonObject loadJson;

                loadJson["type"] = "load";
                loadJson["status"] = "id is online";

                QJsonDocument sendJson(loadJson);

                client->write(sendJson.toJson());
                return;
            }
            QJsonObject loadJson;

            loadJson["type"] = "load";
            loadJson["status"] = "enable";

            this->sendJson(client, loadJson);
            QThread* thread = new QThread();
            auto infoData = qMakePair(client, thread);
            client->moveToThread(thread);
            this->m_clients.insert(jsonObj["userName"].toString(), infoData);
        }
    } else if (type == "msg") {
        QString friendName = jsonObj["friendName"].toString();
        QString userName = jsonObj["userName"].toString();
        QString msgData = jsonObj["data"].toString();
        QJsonObject sendJson;

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
    } else if (type == "registration") {
        QString userName = jsonObj["userName"].toString();
        QString password = jsonObj["password"].toString();

        if (!this->is_userName_Status(userName))
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
            sendJson["data"] = this->deleteUser_as_registrationUser(userName, password, true);
            this->sendJson(client, sendJson);
        }
    } else if (type == "loading") {
        QString userName = jsonObj["userName"].toString();
        quint64 userId = this->getId(userName);
        QJsonObject sendJson;

        sendJson["type"] = "friendIds";
        sendJson["data"] = this->getfriendList(userId);

        qDebug() << "friendsIdLists:" << sendJson["data"].toArray() << Qt::endl;
        this->sendJson(client, sendJson);
        client->flush();
    } else if (type == "friend") {
        int friendId = jsonObj["data"].toInt();
        QString friendName = this->getUserName(friendId);
        QJsonObject sendJson;

        sendJson["type"] = "friend";
        sendJson["data"] = friendName;
        this->sendJson(client, sendJson);
        client->flush();
    } else if (type == "loadend") {
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
    } else if (type == "loadfriend") {
        QJsonArray data = this->loadFriend(dataJson["data"].toString());
        QJsonObject sendJson;

        sendJson["type"] = "loadfriend";
        sendJson["data"] = data;

        qDebug() << sendJson;
        this->sendJson(client, sendJson);
        client->flush();
    } else if (type == "append friend") {
        QString userName = dataJson["userName"].toString();
         QString friendName = dataJson["friendName"].toString();
         QJsonObject sendJson;
        
         sendJson["type"] = "append friend";
         sendJson["status"] = this->appnedFriend(userName, friendName);
         sendJson["friendName"] = friendName;
         sendJson["data"] = sendJson["status"].toBool() ? "添加成功" : "添加失败";
         this->sendJson(client, sendJson);
         if (sendJson["status"].toBool())
         {
             if (this->m_clients.contains(userName))
             {
                 QTcpSocket* socket = this->m_clients[friendName].first;
                 sendJson["friendName"] = userName;
                 sendJson["type"] = "add friend";
                 this->sendJson(socket, sendJson);
                 socket->flush();
             }
         }
    }
}

void Server::sendJson(QTcpSocket* client, const QJsonObject& json)
{
    QByteArray body = QJsonDocument(json).toJson(QJsonDocument::Compact);

    quint32 length = body.size();

    QByteArray packet;
    QDataStream stream(&packet, QIODevice::WriteOnly);
    stream.setByteOrder(QDataStream::BigEndian);

    stream << length;
    packet.append(body);

    qDebug() << packet << Qt::endl;

    client->write(packet);
}

bool Server::deleteUser_as_registrationUser(QString userName, QString password, bool flag)
{
    QSqlQuery query;
    if (flag)
    {
        query.prepare("INSERT INTO users(account, password) VALUES (:userName, :password);");
        query.bindValue(":userName", userName);
        query.bindValue(":password", password);
    } else {
        query.prepare("DELETE FROM users WHERE account = :userName;");
        query.bindValue(":userName", userName);
    }

    if (!query.exec())
    {
        qDebug() << "操作失败：" << query.lastError().text();
        return false;
    }
    qDebug() << "操作成功";
    return true;
}

void Server::setloadStatus(int id, bool status)
{
    QSqlQuery query;
    QString sqlStr = QString("UPDATE users SET is_online = %1 WHERE id = :id").arg(status ? 1 : 0);
    
    qDebug() << sqlStr << Qt::endl;
    query.prepare(sqlStr);
    query.bindValue(":id", id);

    if (!query.exec()) 
    {
        qDebug() << "更新失败：" << query.lastError().text();
        qDebug() << query.lastQuery();
        qDebug() << query.boundValues();
    } else {
        qDebug() << "更新成功，影响行数：" << query.numRowsAffected();
    }
}

bool Server::is_userName_Status(QString userName)
{
    QSqlQuery query;
    
    query.prepare("SELECT * FROM users WHERE account=:userName;");
    query.bindValue(":userName", userName);

    if (!query.exec())
    {
        return false;
    }
    if (query.next())
    {
        return query.value(0).toBool();
    }

    return true;
}

QJsonArray Server::loadFriend(QString data)
{
    QSqlQuery query;
    QString friendName = data;

    friendName = "%" + friendName + "%";
    query.prepare("SELECT * FROM users WHERE account LIKE :friendName;");
    query.bindValue(":friendName", friendName);

    if (!query.exec())
    {
        return QJsonArray();
    }
    QJsonArray Arraydata;
    while (query.next())
    {
        Arraydata.append(query.value("account").toString());
    }

    return Arraydata;
}

bool Server::appnedFriend(QString userName, QString friendName)
{
    QSqlQuery query;

    query.prepare(R"(INSERT INTO friends (user_id, friend_id, created_at) 
                    VALUES(:user_id, :friend_id, NOW()), (:friend_id, :user_id, NOW());)");
    query.bindValue(":user_id", this->getId(userName));
    query.bindValue(":friend_id", this->getId(friendName));

    if (!query.exec())
    {
        return false;
    }

    return true;
}
