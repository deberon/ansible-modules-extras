#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import os.path
import re
from subprocess import Popen, PIPE, call

DOCUMENTATION = '''
---
module: locale_gen
short_description: Creates or removes locales.
description:
     - Manages locales by editing /etc/locale.gen and invoking locale-gen.
version_added: "1.6"
options:
    name:
        description:
             - Name and encoding of the locale, such as "en_GB.UTF-8".
        required: true
        default: null
        aliases: []
    state:
      description:
           - Whether the locale shall be present.
      required: false
      choices: ["present", "absent"]
      default: "present"
'''

EXAMPLES = '''
# Ensure a locale exists.
- locale_gen: name=de_CH.UTF-8 state=present
'''

# ===========================================
# location module specific support methods.
#

def is_present(name):
    """Checks if the given locale is currently installed."""
    output = Popen(["locale", "-a"], stdout=PIPE).communicate()[0]
    return any(fix_case(name) == fix_case(line) for line in output.splitlines())

def fix_case(name):
    """locale -a might return the encoding in either lower or upper case.
    Passing through this function makes them uniform for comparisons."""
    return name.replace(".utf8", ".UTF-8")

def set_locale(name, encoding, enabled=True):
    """ Sets the state of the locale. Defaults to enabled. """
    search_string = '(#+\s*){0,1}%s %s' % (name, encoding)
    if enabled:
        new_string = '%s %s' % (name, encoding)
    else:
        new_string = '# %s %s' % (name, encoding)
    with open("/etc/locale.gen", "r") as f:
        lines = [re.sub(search_string, new_string, line) for line in f]
    with open("/etc/locale.gen", "w") as f:
        f.write("".join(lines))

def apply_change(targetState, name, encoding):
    """Create or remove locale.
    
    Keyword arguments:
    targetState -- Desired state, either present or absent.
    name -- Name including encoding such as de_CH.UTF-8.
    encoding -- Encoding such as UTF-8.
    """

    if targetState=="present":
        # Create locale.
        set_locale(name, encoding, enabled=True)
    else:
        # Delete locale.
        set_locale(name, encoding, enabled=False)
    
    localeGenExitValue = call("locale-gen")
    if localeGenExitValue!=0:
        raise EnvironmentError(localeGenExitValue, "locale.gen failed to execute, it returned "+str(localeGenExitValue))

def apply_change_ubuntu(targetState, name, encoding):
    """Create or remove locale.
    
    Keyword arguments:
    targetState -- Desired state, either present or absent.
    name -- Name including encoding such as de_CH.UTF-8.
    encoding -- Encoding such as UTF-8.
    """
    if targetState=="present":
        # Create locale.
        # Ubuntu's patched locale-gen automatically adds the new locale to /var/lib/locales/supported.d/local
        localeGenExitValue = call(["locale-gen", name])
    else:
        # Delete locale involves discarding the locale from /var/lib/locales/supported.d/local and regenerating all locales.
        with open("/var/lib/locales/supported.d/local", "r") as f:
            content = f.readlines()
        with open("/var/lib/locales/supported.d/local", "w") as f:
            for line in content:
                if line!=(name+" "+encoding+"\n"):
                    f.write(line)
        # Purge locales and regenerate.
        # Please provide a patch if you know how to avoid regenerating the locales to keep!
        localeGenExitValue = call(["locale-gen", "--purge"])
    
    if localeGenExitValue!=0:
        raise EnvironmentError(localeGenExitValue, "locale.gen failed to execute, it returned "+str(localeGenExitValue))

# ==============================================================
# main

def main():

    module = AnsibleModule(
        argument_spec = dict(
            name = dict(required=True),
            state = dict(choices=['present','absent'], required=True),
        ),
        supports_check_mode=True
    )

    name = module.params['name']
    if not "." in name:
        module.fail_json(msg="Locale does not match pattern. Did you specify the encoding?")
    state = module.params['state']

    if not os.path.exists("/etc/locale.gen"):
        if os.path.exists("/var/lib/locales/supported.d/local"):
            # Ubuntu created its own system to manage locales.
            ubuntuMode = True
        else:
            module.fail_json(msg="/etc/locale.gen and /var/lib/locales/supported.d/local are missing. Is the package “locales” installed?")
    else:
        # We found the common way to manage locales.
        ubuntuMode = False
    
    prev_state = "present" if is_present(name) else "absent"
    changed = (prev_state!=state)
    
    if module.check_mode:
        module.exit_json(changed=changed)
    else:
        encoding = name.split(".")[1]
        if changed:
            try:
                if ubuntuMode==False:
                    apply_change(state, name, encoding)
                else:
                    apply_change_ubuntu(state, name, encoding)
            except EnvironmentError as e:
                module.fail_json(msg=e.strerror, exitValue=e.errno)
      
        module.exit_json(name=name, changed=changed, msg="OK")

# import module snippets
from ansible.module_utils.basic import *

main()
