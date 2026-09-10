#include <QCoreApplication>
#include "Server.h"
#include "ase_lib.h"

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    Server server;
    
    return app.exec();
}