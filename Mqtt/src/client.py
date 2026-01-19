import json
import os

class Client:
    def __init__(self, filename:str = 'client.json'):
        self.filename = filename
        self.saved_client = self.__load_client()

    # Save the client ID to a file.
    def __save_client(self, client_id):
        with open(self.filename, 'w') as f:
            json.dump(client_id, f)

    # Load clients from a file if it exists, merge them with the input client list, and return the updated client list.
    def __load_client(self, client_list:list = [])->list:
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                json_clients = json.load(f)
                list1 = list(json_clients)
                _client_temp = list1 + [item for item in client_list if item not in list1]
                return _client_temp
        else:
            return []
    
    # Add a client to the list of saved clients if it is not already in the list.
    def add_client(self, client_id:str)->list:
        if client_id not in self.saved_client:
            self.saved_client.append(client_id)
        self.__save_client(self.saved_client)
        return self.saved_client
    
    # A method that returns the list of saved clients.
    def get_clients(self)->list:
        return self.saved_client

    # Removes a client ID from the saved client list.
    def remove_client(self, client_id:str)->list:
        if client_id in self.saved_client:
            self.saved_client.remove(client_id)
        self.__save_client(self.saved_client)
        return self.saved_client

    # A function to refresh the JSON data, updates the saved client list, saves the updated client list, and returns the updated client list.
    def refresh_json(self)->str:
        client_list = self.saved_client
        self.saved_client = self.__load_client(client_list)
        self.__save_client(self.saved_client)
        return self.saved_client
    
    # Check if the given client_id exists in the saved_client list.
    def is_exist(self, client_id:str)->bool:
        if client_id in self.saved_client:
            return True
        else:
            return False