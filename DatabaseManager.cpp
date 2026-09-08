#include "DatabaseManager.h"
#include <QDebug>
#include <QSqlError>
#include <QString>

DatabaseManager::DatabaseManager(QObject* parent)
{
    this->db.setHostName("127.0.0.1");
    this->db.setPort(3306);
    this->db.setDatabaseName("chat_server");
    this->db.setUserName("root");
    this->db.setPassword("root");

    qDebug() << (db.open() ? "数据库连接成功" : "数据库连接失败");
}

DatabaseManager::~DatabaseManager(void)
{
}

QString DatabaseManager::is_id_to_userName(int id)
{
    QSqlQuery query(this->db);

    query.prepare("SELECT account FROM users WHERE id = :user_id;");
    query.bindValue(":user_id", id);
    if (!query.exec())
    {
        return "";
    }
    if (query.next()) 
    {
        return query.value("account").toString();
    }

    return "";
}

int DatabaseManager::is_userName_to_id(QString userName)
{
    QSqlQuery query(this->db);

    query.prepare("SELECT id FROM users WHERE account = :account;");
    query.bindValue(":account", userName);
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

QJsonArray DatabaseManager::getFriendList(QString userName)
{
    QJsonArray friendList;
    QSqlQuery query;

    query.prepare(R"(
        SELECT f.friend_id
        FROM friends f
        JOIN users u ON f.user_id = u.id
        WHERE u.account = :userName;
    )");
    query.bindValue(":userName", userName);

    if(!query.exec())
    {
        qDebug() << query.lastError();
        return friendList;
    }
    while (query.next())
    {
        friendList.append(query.value("friend_id").toInt());
    }

    return friendList;
}

bool DatabaseManager::load_userName(QString userName, QString password)
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
        qDebug() << "登录成功:" << userName;
        this->setusersStatus(userName, true);
        return true;
    }

    return false;
}

bool DatabaseManager::registrationUser(QString userName, QString password)
{
    QSqlQuery query;

    query.prepare("INSERT INTO users(account, password) VALUES (:userName, :password);");
    query.bindValue(":userName", userName);
    query.bindValue(":password", password);
    if (!query.exec())
    {
        qDebug() << "操作失败：" << query.lastError().text();
        return false;
    }
    qDebug() << "操作成功";
    return true;
}

bool DatabaseManager::get_users_is_none(QString userName)
{
    QSqlQuery query(this->db);
    query.prepare(R"(
        SELECT EXISTS(SELECT 1 FROM users WHERE account = :userName);
    )");
    query.bindValue(":userName", userName);
    if (!query.exec())
    {
        return false;
    }
    if (query.next())
    {
        return query.value(0).toBool();
    }

    return false; 
}

void DatabaseManager::setusersStatus(QString userName, bool status)
{
    QSqlQuery query;
    query.prepare(R"(
        UPDATE users
        SET is_online = :status
        WHERE accountaccount = :userName
    )");
    query.bindValue(":status", status);
    query.bindValue(":userName", userName);

    if (!query.exec())
    {
        qDebug() << "修改失败";
        return;
    }
}

QJsonArray DatabaseManager::loadFriend(QString data)
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

bool DatabaseManager::appnedFriend(QString userName, QString friendName)
{
    QSqlQuery query;

    query.prepare(R"(
        INSERT INTO friends (user_id, friend_id, created_at)
        SELECT u1.id, u2.id, t.ts
        FROM users u1
        JOIN users u2
        CROSS JOIN (SELECT NOW() AS ts) t
        WHERE u1.account = :userName AND u2.account = :friendName
        AND NOT EXISTS (
            SELECT 1 FROM friends f WHERE f.user_id = u1.id AND f.friend_id = u2.id
        )

        UNION ALL

        SELECT u2.id, u1.id, t.ts
        FROM users u1
        JOIN users u2
        CROSS JOIN (SELECT NOW() AS ts) t
        WHERE u1.account = :userName AND u2.account = :friendName
        AND NOT EXISTS (
            SELECT 1 FROM friends f WHERE f.user_id = u2.id AND f.friend_id = u1.id
        );
    )");
    query.bindValue(":userName", userName);
    query.bindValue(":friendName", friendName);
    
    if (!query.exec())
    {
        return false;
    }

    return true;
}

bool DatabaseManager::deleteFriend(QString userName, QString friendName)
{
    QSqlQuery query;

    query.prepare(R"(
        DELETE f
        FROM friends f
        JOIN users u1, users u2
        WHERE
            (
                (f.user_id = u1.id AND f.friend_id = u2.id)
                OR
                (f.user_id = u2.id AND f.friend_id = u1.id)
            )
        AND u1.account = :userName
        AND u2.account = :friendName;
    )");
    query.bindValue(":userName", userName);
    query.bindValue(":friendName", friendName);

    if (!query.exec())
    {
        return false;
    }
    return true;
}
