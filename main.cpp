#include <QApplication>
#include <QDebug>
#include "Server.h"

int main(int argc, char** argv)
{
    QApplication app(argc, argv);
    Server server;

    return app.exec();
}