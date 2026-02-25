import yaml
import yaql
from os import getenv, getcwd, putenv
from os.path import exists,isfile,isdir
from typing import Any

class FileReference:
    """
    !FileReference should simply refer to a file that exists.
    The file is not loaded as part of the configuration.
    """
    yaml_tag = '!FileReference'
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    filename: str = None
    def __init__(self, filename: str):
        self.filename = filename
    @property
    def scalar_value(self):
        return self.filename
    def __repr__(self):
        fn = self.filename
        exists = isfile(fn)
        return ("(reference to '{}')" if exists else "(invalid reference to '{}')").format(fn)

class FileData(yaml.YAMLObject):
    """
    !FileData should refer to a file that exists.
    The file's contents are then loaded as a string
    and available for reference.
    """
    yaml_tag = '!FileData'
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    filename: str = None
    data: Any = None
    def __init__(self, filename: str):
        self.filename = filename
    @property
    def scalar_value(self):
        return self.filename
    def read_data(self):
        if self.data is not None: return self.data
        with open(self.filename,'r') as file:
            self.data = file.read()
        return self.data
    def calculate_data_hash(self):
        # to-do: actually hash the data
        return self.data[:10] if isinstance(self.data,str) else 'DATA HASH'
    def __repr__(self):
        hashdata = self.calculate_data_hash()
        return '(filename:{filename:}, data hash: {hashdata:})'.format(filename=self.filename,hashdata=hashdata)

class EncryptedFileData(FileData):
    yaml_tag = '!EncryptedFileData'
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    def __init__(self, filename: str, key: str | FileData):
        self.filename = filename
        self.key = key
    def key_data(self):
        if isinstance(self.key, str): return self.key
        if isinstance(self.key, FileData):
            return self.key.read_data()
    def decrypt(self, data, key):
        return data
    def read_data(self):
        base_data = super().read_data()
        key_data = self.key_data()
        return self.decrypt(base_data, key_data)
    def __repr__(self):
        return '(encrypted file: {:})'.format(self.filename)

def generic_representer(dumper, data):
    return dumper.represent_scalar(type(data).yaml_tag, data.scalar_value)

def filedata_constructor(loader, node):
    filename = loader.construct_scalar(node)
    return FileData(filename)

def fileref_constructor(loader, node):
    filename = loader.construct_scalar(node)
    return FileReference(filename)

yaml.add_representer(FileData, generic_representer)
yaml.add_constructor(FileData.yaml_tag, filedata_constructor, yaml.SafeLoader)
yaml.add_representer(FileReference, generic_representer)
yaml.add_constructor(FileReference.yaml_tag, fileref_constructor, yaml.SafeLoader)

class Configuration:
    appname: str = ''
    document: Any = None
    engine: Any = None
    def __init__(self):
        self.engine = yaql.factory.YaqlFactory().create()
    @property
    def specified_configfile_variable_name(self):
        return self.appname+"_CONFIG_FILE"
    def find_config_file(self) -> str:
        specified_file = getenv(self.specified_configfile_variable_name)
        if specified_file is not None:
            return specified_file
        home = getenv('HOME')
        pwd = getcwd()
        populate_template = lambda base:base.format(appname=self.appname,pwd=pwd,home=home)
        paths = map(populate_template,[
            "{pwd:}/.config.yaml",
            "{home:}/.config/{appname:}/.config.yaml",
            "/etc/{appname:}/.config.yaml"
        ])
        for path in paths:
            if isfile(path):
                return path
    def specify_config_file(self, fn):
        putenv(self.specified_configfile_variable_name, fn)
    def load_data(self, config_source=None):
        if isinstance(config_source, str):
            self.document = yaml.safe_load(config_source)
            return
        filename_to_load = self.find_config_file()
        with open(filename_to_load,'r') as config_file:
            self.document = yaml.safe_load(filename_to_load)
    def save_config(self):
        filename_to_load = self.find_config_file()
        with open(filename_to_load,'w') as config_file:
            yaml.safe_dump(self.document, config_file, default_flow_style=False)
    def dump_config(self):
        return yaml.safe_dump(self.document)
    def query(self,query):
        expression = self.engine(query)
        return expression.evaluate(data=self.document)

def query_property(query, unpack_filedata=True, null_invalid_file_references=True):
    def run_query(config):
        results = config.query(query)
        if not (unpack_filedata or null_invalid_file_references):
            return results
    return property(run_query)