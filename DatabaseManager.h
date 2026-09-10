#pragma once

#include <QSqlDatabase>
#include <QSqlQuery>
#include <QObject>
#include <QJsonArray>

class DatabaseManager : public QObject {
    Q_OBJECT
public:
    explicit DatabaseManager(QObject* parent = nullptr);
    ~DatabaseManager(void);
public:
    QString is_id_to_userName(int id);    
    int is_userName_to_id(QString userName);
    QJsonArray getFriendList(QString userName);
    bool load_userName(QString userName, QString password);
    bool registrationUser(QString userName, QString password);
    bool get_users_is_none(QString userName);
    bool is_userName_Status(QString userName);
    void setusersStatus(QString userName, bool status);
    QJsonArray loadFriend(QString data);
    bool appnedFriend(QString userName, QString friendName);
    bool deleteFriend(QString userName, QString friendName);
    QString Base64_decode(QString& data);
private:
    QSqlDatabase db = QSqlDatabase::addDatabase("QMYSQL");
};