#!/bin/env python3


class Data(object):
    """
    Base 10 Measurements
    """
    _KB = 1000
    _MB = _KB * _KB
    _GB = _MB * _KB
    _TB = _GB * _KB

    """
    Base 2 Measurements
    """
    _KiB = 0x400
    _MiB = _KiB * _KiB
    _GiB = _MiB * _KiB
    _TiB = _GiB * _KiB

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 offset_in: int = 0, size_in: int = None):
        self.__data_size = 0
        self.__offset = 0
        self.__data = memoryview(bytearray())
        self.__size = len(self.__data)

        self.data = data_in
        self.offset = offset_in
        self.size = size_in
        self.endianness = endianness_in

    @property
    def data(self) -> memoryview:
        return self.__data[self.__offset:self.__offset + self.__size]

    @data.setter
    def data(self, data_in: bytearray | memoryview):
        if isinstance(data_in, bytearray):
            self.__data = memoryview(data_in)
        elif isinstance(data_in, memoryview):
            self.__data = data_in
        else:
            raise ValueError(
                f"Error: Invalid Data Type: "
                f"{type(data_in).__name__}")

    @property
    def endianness(self) -> str:
        return self.__endianness

    @endianness.setter
    def endianness(self, endianness_in: str):
        if endianness_in in ('<', '>', "="):
            self.__endianness = endianness_in
        else:
            raise ValueError(
                f"Error: Invalid Endianness: {endianness_in}")

    @property
    def size(self) -> int:
        return len(self.data)

    @size.setter
    def size(self, size_in: int):
        if isinstance(size_in, int) or isinstance(size_in, float):
            if self.disk_size == 0 or self.offset + size_in < self.disk_size:
                self.__size = int(size_in)
            else:
                raise ValueError(
                    f"Error: Invalid Size: {size_in}\n"
                    f"Size Must BE: <{len(self.__data) - self.offset}")
        elif size_in is None:
            self.__size = len(self.__data)

        else:
            raise ValueError(
                f"Error: Invalid Size: {type(size_in).__name__}")

    @property
    def offset(self) -> int:
        return self.__offset

    @offset.setter
    def offset(self, offset_in: int):
        if self.disk_size == 0 or offset_in < self.disk_size:
            self.__offset = offset_in
        else:
            raise ValueError(
                f"Error: Invalid Offset: {offset_in}\n"
                f"Offset Must Be <{len(self.__data)}")

    @property
    def disk(self) -> memoryview:
        return self.__data

    @property
    def disk_size(self) -> int:
        return len(self.__data)

    def power2(self, value_in: int) -> int:
        value_in -= 1
        for v in [value_in >> n for n in [1,2,4,8,16,32,64]]:
            value_in |= v
        value_in += 1
        return value_in

    def boundary(self, offset_in: int, boundary_in: int) -> int:
        boundary_in = self.power2(boundary_in)
        mask = boundary_in - 1
        return (offset_in + boundary_in) & ~mask

    def __sizeof__(self) -> int:
        return len(self.__data)

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, offset_in: int | slice) -> int | memoryview:
        try:
            if isinstance(offset_in, int):
                return self.__data[offset_in]
            elif isinstance(offset_in, slice):
                start, stop, step = offset_in.indicies(self.size)
                return self.__data[start:stop:step]
            else:
                raise ValueError(
                    f"Error: Invalid Offset: {offset_in}")
        except IndexError as _:
            raise ValueError(
                f"Error: Invalid Offset: {offset_in}")

    def __setitem__(self, offset_in: int | slice, value_in: int):
        try:
            if isinstance(offset_in, int):
                if 0 <= value_in < 256:
                    self.__data[offset_in] = value_in & 0xFF
                else:
                    raise ValueError(
                        f"Error: Invalid Value: {value_in}\n"
                        f"Must Be: 0-255")
            elif isinstance(offset_in, slice):
                start, stop, step = offset_in.indicies(self.size)
                self.__data[start:stop:step] = value_in
            else:
                raise  ValueError(
                    f"Error: Invalid Offset Type: "
                    f"{type(offset_in).__name__}")
        except IndexError as _:
            raise ValueError(
                f"Error: Invalid Offset: {offset_in}")