class Info:
    def __init__(self, info_type, data):
        self.info_type = info_type
        self.data = data

    def get_info_type(self):
        return self.info_type

    def get_data(self):
        return self.data

    def set_info_type(self, info_type):
        self.info_type = info_type

    def set_data(self, data):
        self.data = data

    def to_string(self):
        return f"Make request [info_type={self.info_type}, data={self.data}]"
