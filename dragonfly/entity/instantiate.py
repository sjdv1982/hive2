from .bind import bind_info as entity_bind_info

from ..app import bind_info as app_bind_info
from ..bind import Instantiator as _Instantiator, get_active_bind_environments, get_bind_bases
from ..event import bind_info as event_bind_info


bind_infos = (app_bind_info, event_bind_info, entity_bind_info)


def build_entity_instantiate(i, ex, args, meta_args):
    bind_environments = get_active_bind_environments(bind_infos, meta_args)

    # Update bind environment to use new bases
    environment_class = i.bind_meta_class.start_value
    i.bind_meta_class.start_value = environment_class.extend("EntityBindEnvironment", bases=tuple(bind_environments))


Instantiator = _Instantiator.extend("EntityInstantiator", builder=build_entity_instantiate,
                                    bases=get_bind_bases(bind_infos))