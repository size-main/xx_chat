cmake_minimum_required(VERSION 3.30) 

project(demo LANGUAGES CXX)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/build/Debug)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_SOURCE_DIR}/build/Debug)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/build/Release)

set(CMAKE_INCLUDE_CURRENT_DIR ON)
set(CMAKE_PREFIX_PATH "D:/QT/6.7.3/msvc2022_64")

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(MSVC)
    add_compile_options("/Zc:__cplusplus")
    add_compile_options("/std:c++17")
else()
    add_compile_options(-Wall -Wextra -Wno-deprecated)
endif()

include_directories(SYSTEM ${Qt6_DIR}/include)

find_package(Qt6 REQUIRED
    Core
    Widgets
    Network
    Qml
    Quick
    QuickControls2
    Core5Compat
    Sql
    QuickWidgets
    Multimedia
    Bluetooth
    Charts
    HttpServer 
)

aux_source_directory(./src SOURCES)

add_executable(${PROJECT_NAME}
    WIN32
    ${SOURCES}
    ${RESOURCES}
)

target_compile_definitions(${PROJECT_NAME} PRIVATE QT_QML_DEBUG)

target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    Qt6::Core5Compat
    Qt6::Widgets
    Qt6::Network
    Qt6::Sql
    Qt6::QuickWidgets
    Qt6::Multimedia
    Qt6::Bluetooth
    Qt6::Charts
    Qt6::Qml
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::HttpServer
)
