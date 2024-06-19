import os

from config.common import ConfigurationBuilder as BaseConfigurationBuilder
from config.common import ConfigurationSource


class ConfigurationBuilder(BaseConfigurationBuilder):
    def __init__(self, *sources: ConfigurationSource) -> None:
        super().__init__(*sources)

    def add_examples(self, examples):
        from config.yaml import YAMLFile

        from harp.config import examples as examples_package

        _examples_dirname = os.path.dirname(examples_package.__file__)
        for example in examples or ():
            _example_file = os.path.join(_examples_dirname, f"{example}.yml")
            self.add_source(YAMLFile(_example_file))

    def add_files(self, files):
        for file in files or ():
            _, ext = os.path.splitext(file)
            if ext in (".yaml", ".yml"):
                from config.yaml import YAMLFile

                self.add_source(YAMLFile(file))
            elif ext in (".json",):
                from config.json import JSONFile

                self.add_source(JSONFile(file))
            elif ext in (".ini", ".conf"):
                from config.ini import INIFile

                self.add_source(INIFile(file))
            elif ext in (".toml",):
                from config.toml import TOMLFile

                self.add_source(TOMLFile(file))
            else:
                raise ValueError(f"Unknown file extension: {ext}")

    def add_values(self, values: dict):
        for k, v in values.items():
            self.add_value(k, v)
