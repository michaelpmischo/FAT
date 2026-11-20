#!/bin/env python3
import data, sector, cluster


class Partition(data.Data):
    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 sectors_per_cluster_in: int = None, sector_size_in: int = None,
                 initialize_in: bool = False):
        super().__init__(data_in, endianness_in)
        self.__clusters = {}
        if (sectors_per_cluster_in is not None and
                sector_size_in is not None and
                initialize_in):
            self.initialize(sectors_per_cluster_in, sector_size_in)

    def initialize(self, sectors_per_cluster_in: int, sector_size_in: int):
        print("Initializing Partition...")
        number_of_clusters = int(self.disk_size / sectors_per_cluster_in * sector_size_in)
        self.__clusters = {
            cluster: cluster.Cluster(
                self.data,
                self.endianness,
                cluster,
                cluster * sectors_per_cluster_in,
                sectors_per_cluster_in,
                sector_size_in) for cluster in
            range(number_of_clusters)}
        print("Completed Initializing Partition.")

    def __getitem__(self, cluster_in: int) -> cluster.Cluster | None:
        try:
            return self.__clusters[cluster_in]
        except KeyError as _:
            return None

    def __setitem__(self, number_in: int, cluster_in: cluster.Cluster):
        if number_in in self.__clusters.keys():
            if isinstance(cluster_in, cluster.Cluster):
                self.__clusters[number_in] = cluster_in
            else:
                raise ValueError(
                    f"Invalid Sector Type: {type(cluster_in).__name__}")
        else:
            raise ValueError(
                f"Invalid Sector Number: {number_in}")

    def __len__(self) -> int:
        return len(self.__clusters)

    def __contains__(self, cluster_in: int) -> bool:
        return cluster_in in self.__clusters.keys()

    @property
    def number_of_sectors(self) -> int:
        return sum([len(cluster) for cluster in self.__clusters.values()])

    def get_sector_cluster(self, sector_in: int) -> int | None:
        for c, cluster in self.__clusters.items():
            if sector_in in cluster:
                return c
        else:
            return None

    def get_sector(self, number_in: int) -> sector.Sector | None:
        try:
            return [c for c in self.__clusters.values() if (
                    number_in in c)][0][number_in]
        except (IndexError, AttributeError) as _:
            return None

    def set_sector(self, number_in: int, sector_in: sector.Sector):
        c = self.get_sector_cluster(number_in)
        if c is not None:
            self[c][number_in] = sector_in
        else:
            raise ValueError(
                f"Error: Sector: {number_in} does not "
                f"exist on this partition.")