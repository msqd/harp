import os

from config.common import ConfigurationBuilder as BaseConfigurationBuilder
from config.common import ConfigurationSource

from harp.config.examples import get_example_filename


class ConfigurationBuilder(BaseConfigurationBuilder):
    def __init__(self, *sources: ConfigurationSource) -> None:
        super().__init__(*sources)

    def add_examples(self, examples):
        from config.yaml import YAMLFile

        for example in examples or ():
            self.add_source(YAMLFile(get_example_filename(example)))

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
