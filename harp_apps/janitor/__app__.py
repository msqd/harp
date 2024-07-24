from harp.config import Application
from harp_apps.janitor.lifecycle import JanitorLifecycle


class JanitorApplication(Application):
    depends_on = {"storage"}

    Lifecycle = JanitorLifecycle
