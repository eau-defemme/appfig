from config import Configuration, query_property

class SampleConfiguration(Configuration):
    plain_file = query_property("$.plain")
    reference = query_property("$.working_reference")
    broken_reference = query_property("$.broken_reference")
    encrypted_file = query_property("$.encrypted_file")


sample_config="""
plain: !FileData plain_file.txt
working_reference: !FileReference plain_file.txt
broken_reference: !FileReference fake_file.txt
encrypted_file: !EncryptedFileData
    filename: encrypted_file.txt
    key: !FileReference key.txt
"""

config = SampleConfiguration()
config.load_data(config_source=sample_config)

from pprint import pprint

pprint([config.reference, config.broken_reference, config.plain_file.read_data(),config.encrypted_file.read_data()])