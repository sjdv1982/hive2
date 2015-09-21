import hive


def build_generator(generator_string):
    declaration = """
def generator():
    {}
    """

    body = generator_string.replace("\n", "\n    ")
    declaration_string = declaration.format(body)
    exec(declaration_string, locals(), globals())

    return func


def build_generator(i, ex, meta_args):
    pass


Generator = hive.hive("Generator", build_generator)