import os

import rodi
from blacksheep import Application

from harp.apis.controllers.api import ApiController


class ManagementApplication(Application):
    static_build_path = "/usr/local/harp/dashboard"
    has_static_build = False

    def __init__(self, *, container: rodi.Container):
        super().__init__(services=container)

        self.use_cors(
            allow_methods="*",
            allow_origins="*",
            allow_headers="* Authorization",
            max_age=300,
        )
        self.register_controllers([ApiController])

        @self.after_start
        async def after_start_print_routes(application: Application) -> None:
            from pprint import pprint

            pprint(dict(application.router.routes))

        if os.path.exists(self.static_build_path) and os.path.isdir(self.static_build_path):
            self.serve_files(
                self.static_build_path,
                index_document="index.html",
                fallback_document="index.html",
            )
            self.has_static_build = True
