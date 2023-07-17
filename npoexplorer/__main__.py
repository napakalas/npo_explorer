
import stardog
import requests

class NPExplorer():
    def __init__(self) -> None:
        connection_details = {
            'endpoint': 'https://stardog.scicrunch.io:5821',
            'username': 'SPARC',
            'password': 'RCvp9tKzTdxg42py',
        }
        database_name = 'NPO'
        self.__conn = stardog.Connection(database_name, **connection_details)
        self.__conn.begin()



    def close(self):
        self.__conn.close()