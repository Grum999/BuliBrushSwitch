# -----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2023 - Grum999
# -----------------------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
#
# https://spdx.org/licenses/GPL-3.0-or-later.html
# -----------------------------------------------------------------------------
# A Krita plugin framework
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# The extendableenum module provides a basic extendable Enum class
#
# Main class from this module
#
# - ExtendableEnum:
#       Extendable E num class
#
#
# Made from example from:
#   https://zestedesavoir.com/tutoriels/954/notions-de-python-avancees/4-classes/2-metaclasses/
# -----------------------------------------------------------------------------

class ExtendableEnumMeta(type):
    """Metaclass for ExtendableEnum class"""
    def __new__(cls, name, bases, dict):
        # create a cache to avoid to recreate instances everytime
        dict['__cache__']={}

        # create a dictionnary of class members
        # - exclude magic names from member list
        members = {name: value for (name, value) in dict.items() if not (name.startswith('__') and name.endswith('__'))}

        # create class extendableEnum
        extendableEnum = super().__new__(cls, name, bases, dict)

        # Instanciate all possible values and add them as attribute of created class
        for name, value in members.items():
            value = extendableEnum(value)

            # define member name
            value.name = name

            # define member as class attribute
            setattr(extendableEnum, name, value)
        return extendableEnum


class ExtendableEnum(metaclass=ExtendableEnumMeta):
    def __new__(cls, value):
        # if value exists in cache (has already been instancied), return ir
        if value in cls.__cache__:
            return cls.__mapping__[value]

        instanciedValue = super().__new__(cls)
        instanciedValue.value = value
        instanciedValue.name = 'toto'

        cls.__cache__[value] = instanciedValue
        return instanciedValue

    def __repr__(self):
        return f'<{type(self).__name__}({self.name}, {self.value})>'

