import hive
import dragonfly

var = dragonfly.std.Variable("str", "12")
conv_cast = dragonfly.convert.Convert(("str",), ("float",), "pull", "cast")
conv_duck = dragonfly.convert.Convert(("str",), ("float",), "pull", "duck")

hive.connect(var, conv_cast)
hive.connect(var, conv_duck)

print(repr(conv_cast.value_out.pull()))
print(repr(conv_duck.value_out.pull()))
