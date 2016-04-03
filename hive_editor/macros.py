from .node import NodeTypes


def add_print_complex(node_manager, format_string):
    format_node = node_manager.create_node(NodeTypes.HIVE, "dragonfly.string.Format", params={'meta_args':
                                                                                                  {
                                                                                                  'format_string': format_string}}
    )
    transistor_node = node_manager.create_node(NodeTypes.HIVE, "dragonfly.std.Transistor",
                                               params={'meta_args': {'data_type': 'str'}})
    print_node = node_manager.create_node(NodeTypes.HIVE, "dragonfly.io.Print")

    node_manager.create_connection(format_node.outputs['result'], transistor_node.inputs['value'])
    node_manager.create_connection(transistor_node.outputs['result'], print_node.inputs['value_in'])

    return format_node, transistor_node, print_node