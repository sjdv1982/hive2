from ..event import bind_info as event_bind_info
from ..entity import bind_info as entity_bind_info
from ..instance import Instantiator as _Instantiator


bind_infos = (event_bind_info, entity_bind_info)



def build_entity_instantiate(i, ex, args, meta_args):
    bind_bases = tuple((b_i.environment_hive for b_i in bind_infos if b_i.is_enabled(meta_args)))

    # Update bind environment to use new bases
    environment_class = i.bind_meta_class.start_value
    i.bind_meta_class.start_value = environment_class.extend("EntityBindEnvironment", bases=tuple(bind_bases))


Instantiator = _Instantiator.extend("EntityInstantiator", bases=tuple(b_i.bind_hive for b_i in bind_infos))