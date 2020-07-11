import variables as var


def tr(option, *argv, **kwargs):
    try:
        string = var.config.get("strings", option)
    except KeyError:
        raise KeyError("Missed strings in configuration file: '{string}'. ".format(string=option)
                       + "Please restore you configuration file back to default if necessary.")
    if argv or kwargs:
        try:
            formatted = string.format(*argv, **kwargs)
            return formatted
        except KeyError as e:
            raise KeyError(
                "Missed/Unexpected placeholder {{{placeholder}}} in string '{string}'. ".format(placeholder=str(e).strip("'"), string=option)
                + "Please restore you configuration file back to default if necessary.")
        except TypeError:
            raise KeyError(
                "Missed placeholder in string '{string}'. ".format(string=option)
                + "Please restore you configuration file back to default if necessary.")
    else:
        return string


def commands(command):
    try:
        string = var.config.get("commands", command)
        return string
    except KeyError:
        raise KeyError("Missed command in configuration file: '{string}'. ".format(string=command)
                       + "Please restore you configuration file back to default if necessary.")
