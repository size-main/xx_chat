#include <QCoreApplication>
#include <QDebug>
#include "Server.h"

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    Server server;

    server.lisen_ipconfig(QHostAddress::Any, 8088);
    qDebug() << "服务器开始监听" << Qt::endl;
    qDebug() << "数据库连接" << (server.initMysqlConnect() ? "成功" : "失败") << Qt::endl;

    return app.exec();
}