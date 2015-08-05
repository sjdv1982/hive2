class IGUINodeManager:

    def create_connection(self, output, input):
        pass

    def delete_connection(self, output, input):
        pass

    def create_node(self, node):
        raise NotImplementedError

    def delete_node(self, node):
        raise NotImplementedError