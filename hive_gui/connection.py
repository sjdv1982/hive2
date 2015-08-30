class Connection:

    def __init__(self, output_pin, input_pin):
        self.output_pin.add_connection(self)
        self.input_pin.add_connection(self)

        self.output_pin = output_pin
        self.input_pin = input_pin

    @property
    def index(self):
        return self.input_pin.index_connection(self)

    @property
    def number_siblings(self):
        return self.input_pin.number_connections

    def delete(self):
        self.output_pin.remove_connection(self)
        self.input_pin.remove_connection(self)