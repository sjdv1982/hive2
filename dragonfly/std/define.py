import hive
import ast


def create_func(expression):
    declaration = """
def func():
    {}
    """

    body = expression.replace("\n", "\n    ")
    declaration_string = declaration.format(body)
    exec(declaration_string, locals(), globals())

    return func

def declare_define(meta_args):
    meta_args.definition = hive.parameter(("str", "code"))

# GEN / FUNC modifiers operate on args - different to build
# Call node - output generator OR result

def build_define(i, ex, args, meta_args):
    """Define callable object from expression"""
    # Check body is valid
    ast_node = ast.parse(meta_args.definition, mode='exec')

    func = create_func(meta_args.definition)
    i.result = hive.attribute(("object", "callable"), func)
    i.pull_result = hive.pull_out(i.result)
    ex.result = hive.output(i.pull_result)


Define = hive.dyna_hive("Define", build_define, declarator=declare_define)