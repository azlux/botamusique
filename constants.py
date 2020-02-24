import variables as var

def strings(option, *argv, **kwargs):
    string = ""
    try:
        string = var.config.get("strings", option)
    except KeyError as e:
        raise KeyError("Missed strings in configuration file: '{string}'. ".format(string=option) +
                       "Please restore you configuration file back to default if necessary.")
    if argv or kwargs:
        try:
            formatted = string.format(*argv, **kwargs)
            return formatted
        except KeyError as e:
            raise KeyError(
                "Missed placeholder {{{placeholder}}} in string '{string}'. ".format(placeholder=str(e).strip("'"), string=option) +
                "Please restore you configuration file back to default if necessary.")
        except TypeError as e:
            raise KeyError(
                "Missed placeholder in string '{string}'. ".format(string=option) +
                "Please restore you configuration file back to default if necessary.")
    else:
        return string

def commands(command):
    string = ""
    try:
        string = var.config.get("commands", command)
        return string
    except KeyError as e:
        raise KeyError("Missed command in configuration file: '{string}'. ".format(string=command) +
                       "Please restore you configuration file back to default if necessary.")
