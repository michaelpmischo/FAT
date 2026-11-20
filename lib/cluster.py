#!/bin/env python3
import data, sector


class Cluster(data.Data):
    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 cluster_in: int, number_of_sectors_in: int, sector_size_in: int):
        super().__init__(
            data_in,
            endianness_in,
            cluster_in * number_of_sectors_in * sector_size_in,
            number_of_sectors_in * sector_size_in)
        self.__cluster = cluster_in
        self.__sector_size = sector_size_in
        self.__sectors = [
            sector.Sector(data_in, endianness_in, s, sector_size_in) for s in
            range(number_of_sectors_in)]

    @property
    def number(self) -> int:
        return self.__cluster

    def __getitem__(self, sector_in: int) -> sector.Sector | None:
        try:
            return self.__sectors[self.__index(sector_in)]
        except IndexError as _:
            return None

    def __setitem__(self, number_in: int, sector_in: sector.Sector):
        try:
            if isinstance(sector_in, sector.Sector):
                self.__sectors[self.__index(sector_in)] = sector_in
            else:
                raise ValueError(
                    f"Invalid Sector Type: {type(sector_in).__name__}")

        except IndexError as _:
            raise ValueError(
                f"Invalid Sector Number: {number_in}")

    def __len__(self) -> int:
        return len(self.__sectors)

    def __contains__(self, sector_in: int) -> bool:
        return sector_in in self.__sectors.keys()

    def __index(self, sector_in: int) -> int:
        index = sector_in - self.offset // self.__sector_size
        return 0 if index < 0 else index