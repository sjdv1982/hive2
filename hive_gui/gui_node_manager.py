class IGUINodeManager:

    def create_connection(self, output, input):
        raise NotImplementedError

    def delete_connection(self, output, input):
        raise NotImplementedError

    def create_node(self, node):
        raise NotImplementedError

    def delete_node(self, node):
        raise NotImplementedError

    def rename_node(self, node, name):
        raise NotImplementedError

    def on_pasted_pre_connect(self, nodes):
        pass

    def set_position(self, node, position):
        raise NotImplementedError