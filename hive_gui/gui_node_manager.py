class IGUINodeManager:

    def create_connection(self, connection):
        raise NotImplementedError

    def delete_connection(self, connection):
        raise NotImplementedError

    def reorder_connection(self, connection, index):
        raise NotImplementedError

    def create_node(self, node):
        raise NotImplementedError

    def delete_node(self, node):
        raise NotImplementedError

    def set_node_name(self, node, name):
        raise NotImplementedError

    def on_pasted_pre_connect(self, nodes):
        pass

    def set_node_position(self, node, position):
        raise NotImplementedError

    def fold_pin(self, pin):
        raise NotImplementedError

    def unfold_pin(self, pin):
        raise NotImplementedError