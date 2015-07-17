#!/usr/bin/python
# Writes out a binary file from a provided base64 string
import os
import shutil
import tempfile
import base64
try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

from ansible.module_utils.basic import *

DOCUMENTATION = """
---
module: binary
short_description: Writes out binary files to the filesystem
description:
  - Accepts a base64 string and writes out the file to the filesystem
version_added: "1.7"
author: Derek Anderson
notes:
  - Other things consumers of your module should know
requirements:
  - list of required things
  - like the factor package
  - or a specic platform
options:
  base_64:
    description:
      - A base64 encoded string representing the file
    required: true
    default: null
    choices: []
    aliases: []
    version_added: 1.7
  dest:
    description:
      - Absolute path on remote server where the binary should written
    required: true
    default: null
"""

EXAMPLES = """
- action: binary base64=SGVsbG8gV29ybGQK dest=/tmp/hi.txt
"""

class Binary(object):
    
    def write_base64_file(self, encoded_string, dest):
        """Accepts an encoded string and writes out a file based on the
        contents. Must first write out encoded string to a temporary file.
        
        Returns whether the file was changed or not."""
        # Create temporary file to store the encoded string
        tmp_file_name = tempfile.mkstemp()[1]
        tmp_file = open(tmp_file_name, 'w')
        tmp_file.write(encoded_string)
        tmp_file.close()
        tmp_file = open(tmp_file_name, 'r')

        # Decode temporary file into a temporary authkey file
        d_tmp_file_name = tempfile.mkstemp()[1]
        d_tmp_file = open(d_tmp_file_name, 'w')
        base64.decode(tmp_file, d_tmp_file)
        d_tmp_file.close()

        # Now we need to compare the generated file with the existing file
        try:
            existing_hash = sha1(open(dest).read()).hexdigest()
            new_hash = sha1(open(d_tmp_file_name).read()).hexdigest()
            
            if new_hash == existing_hash:
                # The hashes match. No changes are necessary.
                # Remove temp files
                os.remove(d_tmp_file_name)
                os.remove(tmp_file_name)
                return False

            # The hash is different than the existing one
            os.remove(dest)

        # At this point the file is new. We need to write it.
        except IOError:
            # No file exists, we can write
            pass

        # Copy the new generated file to the destination
        shutil.copyfile(d_tmp_file_name, dest)

        # Remove temporary files
        os.remove(d_tmp_file_name)
        os.remove(tmp_file_name)

        return True

def main():

    module = AnsibleModule(
        argument_spec = dict(
            base64 = dict(required=True),
            dest = dict(required=True)
        )
    )

    base64 = module.params['base64']
    dest = module.params['dest']

    bin = Binary()
    module.exit_json(changed=bin.write_base64_file(base64, dest))

main()
