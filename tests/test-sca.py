from sca.controllers import AND, NAND
from sca.actuators import Debug
from sca.sensors import Keyboard, Always

import hive

sens = Keyboard()
sens.name = "Sensor1"

sens2 = Always()

cont = AND()
cont_not = NAND()

act = Debug()

act_not = Debug()
act_not.message = "Not Triggered!"

hive.connect(cont, act)
hive.connect(cont_not, act_not)

# Connect Triggered message
hive.connect(sens.positive, cont.a)
hive.connect(sens.trig_out, cont.trig_in)

hive.connect(sens2.positive, cont.b)
hive.connect(sens2.trig_out, cont.trig_in)

# Connect Not Triggered message
hive.connect(sens.positive, cont_not.a)
hive.connect(sens.trig_out, cont_not.trig_in)

hive.connect(sens2.positive, cont_not.b)
hive.connect(sens2.trig_out, cont_not.trig_in)

# Trigger sensors
sens.trig_in()
sens2.trig_in()

