from typing import Generic, TypeVar
from ruamel.yaml import YAML

_TYAMLOBJ = TypeVar("_TYAMLOBJ", bound="YamlSerializationMixin")

yaml = YAML()


class YamlSerializationMixin(Generic[_TYAMLOBJ]):
    def __init_subclass__(cls, **kwargs):
        """
        Automatically registers the class with the YAML serializer.
        """
        super().__init_subclass__(**kwargs)

        # Register the class with the yaml loader
        yaml.register_class(cls)
