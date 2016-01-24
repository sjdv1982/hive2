from traceback import format_exc

from .code_generator import dict_to_parameter_array, parameter_array_to_dict
from .models import model
from .node import NodeTypes


class HiveMapIO:

    def __init__(self, hivemap=None):
        self.hivemap = hivemap

    def save(self, node_manager, nodes=None, docstring=""):
        if nodes is None:
            nodes = node_manager.nodes.values()

        hivemap = self.hivemap = model.Hivemap()
        hivemap.docstring = docstring

        for node in nodes:
            # Get node params
            params = node.params

            # Write to Bee
            meta_arg_array = dict_to_parameter_array(params.get('meta_args', {}))
            arg_array = dict_to_parameter_array(params.get('args', {}))

            folded_pins = [pin_name for pin_name, pin in node.inputs.items() if pin.is_folded]

            # Serialise HiveNode instance
            if node.node_type == NodeTypes.HIVE:
                cls_arg_array = dict_to_parameter_array(params.get('cls_args', {}))

                spyder_hive = model.HiveNode(identifier=node.name, import_path=node.import_path, position=node.position,
                                             meta_args=meta_arg_array, args=arg_array, cls_args=cls_arg_array,
                                             folded_pins=folded_pins)

                hivemap.hives.append(spyder_hive)

            # Serialise Bee instance
            elif node.node_type == NodeTypes.BEE:
                spyder_bee = model.BeeNode(identifier=node.name, import_path=node.import_path, position=node.position,
                                           meta_args=meta_arg_array, args=arg_array, folded_pins=folded_pins)
                hivemap.bees.append(spyder_bee)

        for node in nodes:
            node_name = node.name

            for pin_name, pin in node.outputs.items():
                for connection in pin.connections:
                    target_pin = connection.input_pin
                    target_node = target_pin.node

                    # Omit connections that aren't in the copied nodes
                    if target_node not in nodes:
                        continue

                    is_trigger = connection.is_trigger
                    spyder_connection = model.Connection(node_name, pin_name, target_node.name, target_pin.name,
                                                         is_trigger)
                    hivemap.connections.append(spyder_connection)

    def load(self, node_manager):
        hivemap = self.hivemap

        if hivemap is None:
            return []

        # Create nodes
        # Mapping from original ID to new ID
        id_to_node_name = {}
        node_to_spyder_hive_node = {}
        node_to_spyder_node = {}

        created_nodes = {}

        # Load IO bees
        for spyder_bee in hivemap.bees:
            import_path = spyder_bee.import_path

            meta_args = parameter_array_to_dict(spyder_bee.meta_args)
            args = parameter_array_to_dict(spyder_bee.args)

            params = {"meta_args": meta_args, "args": args}

            try:
                node = node_manager.create_bee(import_path, params)

            except Exception as err:
                print("Unable to create node {}".format(spyder_bee.identifier))
                print(format_exc())
                continue

            node_to_spyder_node[node] = spyder_bee

        # Load hives
        for spyder_hive in hivemap.hives:
            import_path = spyder_hive.import_path

            meta_args = parameter_array_to_dict(spyder_hive.meta_args)
            args = parameter_array_to_dict(spyder_hive.args)
            cls_args = parameter_array_to_dict(spyder_hive.cls_args)

            params = {"meta_args": meta_args, "args": args, "cls_args": cls_args}

            try:
                node = node_manager.create_hive(import_path, params)

            except Exception as err:
                print("Unable to create node {}".format(spyder_hive.identifier))
                print(format_exc())
                continue

            node_to_spyder_node[node] = spyder_hive

            # Specific mapping for Spyder HiveNodes only.
            node_to_spyder_hive_node[node] = spyder_hive

        # Attempt to set common data between IO bees and Hives
        for node, spyder_node in node_to_spyder_node.items():
            # Try to use original name, otherwise make unique
            node_manager.rename_node(node, spyder_node.identifier, attempt_till_success=True)

            # Set original position
            node_manager.reposition_node(node, (spyder_node.position.x, spyder_node.position.y))

            # Map original copied ID to new allocated ID
            node_name = node.name
            id_to_node_name[spyder_node.identifier] = node_name
            created_nodes[node_name] = node

        # Recreate connections
        for connection in hivemap.connections:
            try:
                from_id = id_to_node_name[connection.from_node]
                to_id = id_to_node_name[connection.to_node]

            except KeyError:
                print("Unable to find all nodes in connection: {}, {}".format(connection.from_node, connection.to_node))
                continue

            from_node = created_nodes[from_id]
            to_node = created_nodes[to_id]

            try:
                from_pin = from_node.outputs[connection.output_name]
                to_pin = to_node.inputs[connection.input_name]

            except KeyError:
                print("Unable to find all node pins in connection: {}.{}, {}.{}"
                      .format(connection.from_node, connection.output_name, connection.to_node, connection.input_name))
                continue

            try:
                node_manager.create_connection(from_pin, to_pin)
            except Exception:
                print("Unable to create connection between {}.{}, {}.{}"
                      .format(connection.from_node, connection.output_name, connection.to_node, connection.input_name))
                print(format_exc())

        # Fold folded pins
        for node, spyder_node in node_to_spyder_node.items():

            for pin_name in spyder_node.folded_pins:
                try:
                    pin = node.inputs[pin_name]

                except KeyError:
                    print("Couldn't find pin {}.{} to fold".format(node.name, pin_name))
                    continue

                node_manager.fold_pin(pin)

        return dict(nodes=created_nodes, docstring=hivemap.docstring)
