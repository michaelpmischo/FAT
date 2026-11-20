#!/bin/env python3
import data


class Sector(data.Data):
    __SIZES = [
        int(0.5 * data.Data._KiB), # 512
        int(1.0 * data.Data._KiB), # 1024
        int(2.0 * data.Data._KiB), # 2048
        int(4.0 * data.Data._KiB), # 4096
    ]

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 number_in: int, size_in: int):
        self._verify_size(size_in)
        super().__init__(data_in, endianness_in, number_in * size_in, size_in)
        self.__sector_number = number_in
        self.__sector_size = size_in

    @property
    def sector_number(self) -> int:
        return self.__sector_number

    @property
    def sector_size(self) -> int:
        return self.__sector_size

    @sector_size.setter
    def sector_size(self, size_in: int):
        self._verify_size(size_in)
        self.__sector_size = size_in

    def _verify_size(self, size_in: int):
        if size_in not in self.__SIZES:
            raise ValueError(
                f"Error: Invalid Sector Size: {size_in}\n"
                f"Valid Sizes: {self.__SIZES}")

