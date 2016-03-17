from .bind import bind_info as entity_bind_info

from ..app import bind_info as app_bind_info
from ..bind import create_instantiator
from ..event import bind_info as event_bind_info


bind_infos = (app_bind_info, event_bind_info, entity_bind_info)
Instantiator = create_instantiator(*bind_infos)
