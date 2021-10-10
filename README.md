# MessageU-Server
 
MessageU is encrypted end-to-end chat and file transfer protocol. Using RSA for key exchange and AES CBS for messaging and file transfer.

The client is written in C++:
https://github.com/ShlomiRex/MessageU-Client

And the server is written in python:
https://github.com/ShlomiRex/MessageU-Server

# Environment

Client development: Visual Studio 2019 Community - Windows

Server development: Pycharm Professional 2021 - Windows + macOS

Database editor and viewer: DBeaver Community - Windows + macOS

Client C++ Libraries:

* Crypto++ 8.5.0
* Boost 1.70.0

# Screenshots - Client
## Main Menu
![Main Menu](README/Client/main_menu.png)

## Receiving list of clients
![Receiving list of clients](README/Client/receiving_list_of_clients.png)

## Request public key from server
![Request public key from server](README/Client/request_public_key_from_server.png)

## Getting list of clients - again
![Getting list of clients - again](README/Client/getting_list_of_clients_again.png)

## Receiving empty list of messages
![Receiving empty list of messages](README/Client/receiving_empty_list_of_messages.png)

## Receiving diffirent kinds of messages
![Receiving diffirent kinds of messages](README/Client/receiving_diffirent_kinds_of_messages.png)

# Screenshots - Server
## Server Database - Users table
![Database - Users table](README/Server/Database/users.png)

## Server Database - Messages table
![Database - Messages table](README/Server/Database/messages.png)

## Some server logs
![Some server logs](README/Server/logs.png)
