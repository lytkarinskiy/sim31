import uuid
import pickle
import os


class UUIDict:
    def __init__(self, db_name="dict.uuid"):
        self.__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        self.db_name = db_name
        self.storage = self.read_dict()

    def write_dict(self, obj):
        with open(self.db_name, 'wb') as f:
            pickle.dump(obj, f)

    def erase_dict(self):
        self.storage = dict()
        self.write_dict(self.storage)

    def read_dict(self):
        try:
            f = open(os.path.join(self.__location__, self.db_name), "rb")
        except OSError:
            self.write_dict(dict())
            f = open(os.path.join(self.__location__, self.db_name), "rb")
            print("Created empty dict")
        return pickle.load(f)

    def get_uuid(self, key_string):
        try:
            uuid_string = self.storage[key_string]
            print("Found record", key_string, uuid_string)
        except KeyError:
            print("Didn't find record", key_string)
            uuid_string = str(uuid.uuid3(uuid.NAMESPACE_DNS, key_string))
            self.storage[key_string] = uuid_string
            print("Created new record", key_string, uuid_string)
            self.write_dict(self.storage)
        return uuid_string

