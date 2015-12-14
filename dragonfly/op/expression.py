import hive
import ast

from math import *

namespace = ("sqrt",)


class NodeVisitor(ast.NodeVisitor):

    def __init__(self):
        super().__init__()

        self.visited_nodes = []

    def visit(self, node):
        if isinstance(node, ast.Call):
            for arg in node.args:
                self.visit(arg)

        else:
            self.generic_visit(node)
            self.visited_nodes.append(node)


def create_func(expression, names):
    declaration = """
def func(self, {}):
    {}
    self._result = {}"""

    arguments = ", ".join(["{0}={0}".format(name) for name in namespace])
    declarations = "\n    ".join(["{0}=self._{0}".format(name) for name in names])
    declare_func = declaration.format(arguments, declarations, expression)

    exec(declare_func, locals(), globals())
    return func


def declare_expression(meta_args):
    meta_args.expression = hive.parameter("str", "")


def build_expression(i, ex, args, meta_args):
    """Execute bound expression for provided inputs and output result"""
    ast_node = ast.parse(meta_args.expression, mode='eval')

    visitor = NodeVisitor()
    visitor.visit(ast_node)

    visited_nodes = visitor.visited_nodes

    variable_names = [x.id for x in visited_nodes if isinstance(x, ast.Name)]

    i.result = hive.attribute("float")
    i.pull_result = hive.pull_out(i.result)
    ex.result = hive.output(i.pull_result)

    for name in variable_names:
        attribute = hive.attribute("float")
        setattr(i, name, attribute)

        pull_in = hive.pull_in(attribute)
        setattr(ex, name, hive.antenna(pull_in))

        hive.trigger(i.pull_result, pull_in, pretrigger=True)

    func = create_func(meta_args.expression, variable_names)
    i.modifier = hive.modifier(func)
    hive.trigger(i.pull_result, i.modifier, pretrigger=True)


Expression = hive.dyna_hive("Expression", build_expression, declarator=declare_expression)